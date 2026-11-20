# Step 2: Benchmark contribution, group G02

**Benchmark draft and coverage gaps:** Divya Shori · **Validation:** Hanieh Jebeli (draft cases 006–014), Divya Shori (draft cases 001–004)

> **Status: final, ready to submit.** Submission file: [`benchmark/G02_benchmark.xlsx`](../../benchmark/G02_benchmark.xlsx): **10 cases, all Self-validated**, in the course template. It goes to the course instructor **by email by Mon 23 Nov 2026, 09:00**. The 14-case working draft stays in [`benchmark/G02_benchmark_draft.xlsx`](../../benchmark/G02_benchmark_draft.xlsx).

## Final 10

| Final ID | Draft ID | Case | Category | Expected action → outcome | Evidence chunk |
|---|---|---|---|---|---|
| G02-001 | 001 | EPFL President successor: start date, who appoints | Standard factual | ANSWER | `06fcc05a…_fixed_0` |
| G02-002 | 002 | Who runs the Swiss Data Science Center, since when | Standard factual | ANSWER | `8adacd9a…_fixed_0`, `f41da84c…_fixed_1` |
| G02-003 | 003 | Gene variant E756del and malaria | Difficult retrieval | ANSWER | `084aa327…_fixed_0` |
| G02-004 | 004 | When tuition fees were last adjusted before 2017 (2004) | Temporal | ANSWER | `6df21a18…_fixed_0` |
| G02-005 | 006 | QS rank: 12th (2013) vs 7th (2018, QS 2024) | Conflicting evidence | ANSWER (resolve by date) | `add82cd3…_fixed_7`, `2685b452…_fixed_0`, `a39f97e3…_fixed_1` |
| G02-006 | 007 | Acceptance rate, MSc Data Science 2023 | Insufficient evidence | ABSTAIN | none (search log) |
| G02-007 | 010 | "2019 ETH study on 5G killing bees" (no such study) | Adversarial / false premise | ABSTAIN | none (search log) |
| G02-008 | 011 | District heating sale: price and transfer date (DE-only evidence) | Multilingual / code-switch | ANSWER | `909f5028…_fixed_0` |
| G02-009 | 013 | "What did the ETH President talk about in his ETH Day speech?" | Ambiguous / underspecified | CLARIFY | `2f3e0e22…_fixed_0`, `20aed329…_fixed_1` |
| G02-010 | 014 | "Who won the Rossler Prize in 2013?" (umlaut missing) | Recovery-triggering | RECOVER → ANSWER | `dd06ade4…_fixed_0` |

All 9 categories are covered (minimum 4), with 2 standard factual cases (minimum 2). Expected actions: 6 ANSWER, 2 ABSTAIN, 1 CLARIFY, 1 RECOVER.

**Not submitted (kept in the draft):**
- **005** (ETH President in 2013 vs 2016): the same question pattern as original Q1 ("who was president of ETH in 2003?").
- **008** (international tuition fees from 2025): the same topic as 004; one insufficient-evidence case is enough.
- **009** and **012** (Fixposition): both use the same source chunk; 010 covers the false-premise category with an ABSTAIN case.

## Validation (20 Nov)

- **Automated check of every case** against `docs_fixed_norm.pkl`: each chunk ID exists, its file name matches the cited document, and every quoted passage appears in the chunk text. The only differences were formatting (a markdown link inside one 2013 passage, a missing comma); both were fixed or checked by reading the chunk.
- **Hanieh's review (draft 006–014):** the full name "Zhenzhong" is in no chunk, so it was removed from the expected answer. The 2016 and 2021 ETH Day chunks described the Rector's speech, so they were replaced with the President's speeches (2019, 2021).
- **Correction to her review:** for the Rössler case the cited chunk stores "rössler" with the umlaut. "roessler" only appears in other chunks, so the rationale was changed back. The trap still holds: "Rossler" matches 0 chunks.
- **Category of the QS case:** kept as *Conflicting evidence* (team decision). Without a year, the retrieved passages disagree and have to be resolved by date.
- **Duplicate check** against the 25 original questions and between our own cases: draft 005 was dropped, as described above.

## Course guidelines (17 Nov) and how we meet them

| Guideline | Our cases |
|---|---|
| Answerable questions: evidence must exist in the shared indexed chunks | Every answerable case cites chunk IDs that contain the answer (checked with `fill_chunk_ids.py --verify`) |
| Difficult retrieval: evidence in the index but hard to retrieve | G02-003: the answer is a side detail in an indexed chunk |
| Insufficient evidence: abstention justified by the indexed corpus, not a failed retrieval | G02-006 and G02-007: searched all 7,531 chunks (and the raw HTML); search logs in the workbook |
| Facts only in the original HTML: document separately, not in the 10 | Listed in [`coverage_gaps.md`](coverage_gaps.md) (7 gaps) |

## Design choices

- **Grounded in the shared index, not only the raw pages.** The system can only answer from `docs_fixed_norm.pkl`, which misses 37% of pages and the lead paragraph of 92% of indexed pages ([audit finding](../audit/index_coverage.md)). Every answerable case cites a chunk ID that contains the answer, checked automatically and by eye. Our first draft used facts from article leads that turned out not to be indexed, so those cases were replaced.
- **Abstention cases document a search of all chunks and all raw pages**, not a failed top-k retrieval (template requirement). The search terms and hit counts are in the evidence column.
- **False premise:** an *unsupported* premise (correct behaviour: abstain without inventing a study). A *contradicted* premise (Fixposition, draft 009) stays in the draft.
- **The temporal case needs reasoning across dates** (a relative span anchored to the publication year), not a plain lookup.
- **Multilingual case:** an English question whose only evidence is a German chunk.
- **No overlap with the reference benchmark** (Q1–25, R1–R15): no "current president", "president in 2003", "student numbers" or "Hong Kong" questions.
- **One family per underlying fact.** Each of the 10 cases tests a different fact, so each has its own family ID (G02-F01 to G02-F10).

Authoring method is recorded honestly as *LLM-assisted* in the workbook. Ground truth, evidence and chunk IDs were verified by group members, as the template requires.
