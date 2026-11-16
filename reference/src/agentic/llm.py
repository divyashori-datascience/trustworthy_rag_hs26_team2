"""Thin Claude (Anthropic SDK) wrapper for the agentic system.

Every LLM-backed agent in Step 3 — the profiler, generator, verifier, and query
rewriter — goes through :class:`LLMClient`. Centralising the calls here lets us:

* keep one configured ``anthropic.Anthropic`` client (the SDK handles retries),
* request structured JSON via ``output_config.format`` and parse it safely,
* prompt-cache the stable system prompt across the whole benchmark run, and
* accumulate token usage / approximate cost (the Step 1 rubric asks for a cost
  indicator, and we report the agentic system's cost the same way).

Design choice: the verifier and generator default to a strong model
(``claude-opus-4-7``) because grounding judgements drive the reliability story;
profiling and query rewriting are light tasks routed to a faster model. All
models are configurable via ``.env`` (see ``baseline.config``).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from baseline import config

# Approximate USD per 1M tokens (input, output), for the cost indicator only.
# Source: model card pricing at time of writing; treated as an estimate.
_PRICING: Dict[str, tuple] = {
    "claude-opus-4-7": (5.0, 25.0),
    "claude-opus-4-6": (5.0, 25.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
}


@dataclass
class UsageTally:
    """Running token + cost accumulator across all calls of one client."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    calls: int = 0
    est_cost_usd: float = 0.0
    per_model: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def add(self, model: str, usage) -> None:
        i = getattr(usage, "input_tokens", 0) or 0
        o = getattr(usage, "output_tokens", 0) or 0
        cr = getattr(usage, "cache_read_input_tokens", 0) or 0
        cw = getattr(usage, "cache_creation_input_tokens", 0) or 0
        self.input_tokens += i
        self.output_tokens += o
        self.cache_read_tokens += cr
        self.cache_write_tokens += cw
        self.calls += 1

        in_price, out_price = _PRICING.get(model, (5.0, 25.0))
        # Cache reads ~0.1x input, writes ~1.25x input.
        cost = (
            (i / 1e6) * in_price
            + (o / 1e6) * out_price
            + (cr / 1e6) * in_price * 0.1
            + (cw / 1e6) * in_price * 1.25
        )
        self.est_cost_usd += cost
        m = self.per_model.setdefault(
            model, {"calls": 0, "input_tokens": 0, "output_tokens": 0, "est_cost_usd": 0.0}
        )
        m["calls"] += 1
        m["input_tokens"] += i
        m["output_tokens"] += o
        m["est_cost_usd"] += cost

    def as_dict(self) -> dict:
        return {
            "calls": self.calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_write_tokens": self.cache_write_tokens,
            "est_cost_usd": round(self.est_cost_usd, 4),
            "per_model": {
                k: {**v, "est_cost_usd": round(v["est_cost_usd"], 4)}
                for k, v in self.per_model.items()
            },
        }


class LLMUnavailableError(RuntimeError):
    """Raised when an LLM call is attempted without a configured key."""


class LLMClient:
    """Configured Claude client with JSON + text helpers and a usage tally."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key or config.ANTHROPIC_API_KEY
        self._client = None  # lazily constructed so import works without a key
        self.usage = UsageTally()

    @property
    def available(self) -> bool:
        return config.have_anthropic_key() or bool(self._api_key and "replace" not in self._api_key)

    def _ensure(self):
        if self._client is None:
            if not self.available:
                raise LLMUnavailableError(
                    "No usable ANTHROPIC_API_KEY. Add it to .env (see .env.example)."
                )
            import anthropic  # imported here so the package loads without the SDK key

            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    # ----------------------------------------------------------------- text
    def complete_text(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int = 1024,
        thinking: bool = False,
    ) -> str:
        """Return Claude's text response (thinking blocks are skipped)."""
        client = self._ensure()
        kwargs: Dict[str, Any] = dict(
            model=model,
            max_tokens=max_tokens,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
        )
        if thinking:
            kwargs["thinking"] = {"type": "adaptive"}
        resp = client.messages.create(**kwargs)
        self.usage.add(model, resp.usage)
        return "".join(b.text for b in resp.content if b.type == "text").strip()

    # ----------------------------------------------------------------- json
    def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict,
        model: str,
        max_tokens: int = 1024,
    ) -> dict:
        """Return a dict validated against ``schema`` via structured outputs.

        Falls back to best-effort JSON extraction if the structured-output
        response is somehow not clean JSON.
        """
        client = self._ensure()
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )
        self.usage.add(model, resp.usage)
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        return _loads_lenient(text)


def _loads_lenient(text: str) -> dict:
    """Parse JSON, tolerating ```json fences or surrounding prose."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


# A module-level singleton is convenient for the pipeline; tests can pass their
# own LLMClient instead.
_default_client: Optional[LLMClient] = None


def default_client() -> LLMClient:
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client
