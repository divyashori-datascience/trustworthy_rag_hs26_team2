"""Three baseline retrievers: bilingual BM25, dense (e5), GraphRAG.

The classes mirror the previous team's implementations exactly so we can reuse
their pickled artifacts. The original loader scripts in
``Baseline/storage/full_corpus/`` had Colab-only paths baked in; the loaders
here accept paths so the same artifacts work locally.
"""
from __future__ import annotations

import functools
import json
import pathlib
import pickle
from typing import Dict, List, Optional, Tuple

import numpy as np
from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langdetect import detect
from sentence_transformers import SentenceTransformer
from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer

from . import config


# --------------------------------------------------------------------- BM25
class EnDeTranslator:
    """Greedy EN<->DE translation using m2m100_418M (1st call downloads weights)."""

    def __init__(self, model: str = "facebook/m2m100_418M", device: Optional[str] = None) -> None:
        self.device = device or config.DEVICE
        self.tok = M2M100Tokenizer.from_pretrained(model)
        self.model = M2M100ForConditionalGeneration.from_pretrained(model).to(self.device)

    @functools.lru_cache(maxsize=512)
    def translate(self, text: str, tgt: str) -> str:
        try:
            src = detect(text) if text.strip() else "en"
        except Exception:
            src = "en"
        src = src if src in ("en", "de") else "en"
        if src == tgt:
            return text
        self.tok.src_lang = src
        ids = self.tok(text, return_tensors="pt").to(self.device)
        out = self.model.generate(
            **ids,
            forced_bos_token_id=self.tok.get_lang_id(tgt),
            num_beams=1,
            max_new_tokens=128,
        )
        return self.tok.decode(out[0], skip_special_tokens=True)


class BilingualBM25:
    """Two BM25Retrievers (EN/DE) with optional translation + dedup by chunk_id."""

    def __init__(
        self,
        docs: List[Document],
        translator: Optional[EnDeTranslator] = None,
        k1: float = 1.2,
        b: float = 0.75,
    ) -> None:
        self.translator = translator
        buckets: Dict[str, List[Document]] = {"en": [], "de": []}
        for d in docs:
            lang = d.metadata.get("language", "en")
            if lang not in ("en", "de"):
                lang = "en"
            buckets[lang].append(d)
        self.retrievers: Dict[str, BM25Retriever] = {}
        for lang, ds in buckets.items():
            if ds:
                self.retrievers[lang] = BM25Retriever.from_documents(ds, k1=k1, b=b)

    def _detect_lang(self, query: str) -> str:
        try:
            l = detect(query)
            return l if l in ("en", "de") else "en"
        except Exception:
            return "en"

    def search(
        self,
        query: str,
        top_k: int = 100,
        metadata_filter: Optional[dict] = None,  # kept for API parity
    ) -> List[Document]:
        src = self._detect_lang(query)
        hits: List[Tuple[Document, float]] = []
        for lang, retriever in self.retrievers.items():
            if self.translator is not None and lang != src:
                q_lang = self.translator.translate(query, lang)
            else:
                q_lang = query
            docs = retriever.invoke(q_lang)[:top_k]
            for rank, d in enumerate(docs, start=1):
                score = float(top_k - rank)
                d.metadata["bm25_score"] = score
                hits.append((d, score))
        best: Dict[str, Document] = {}
        for d, _ in sorted(hits, key=lambda x: x[1], reverse=True):
            uid = d.metadata.get("chunk_id") or d.metadata.get("record_id")
            if uid not in best:
                best[uid] = d
            if len(best) >= top_k:
                break
        return list(best.values())


def _register_for_unpickle() -> None:
    """The previous team pickled BilingualBM25 from __main__, so reattach it there.

    Without this, ``pickle.load`` raises ``AttributeError: Can't get attribute
    'BilingualBM25' on <module '__main__'>``.
    """
    import __main__
    __main__.BilingualBM25 = BilingualBM25
    __main__.EnDeTranslator = EnDeTranslator


def load_bm25(
    path: Optional[pathlib.Path] = None,
    with_translator: bool = True,
) -> BilingualBM25:
    path = pathlib.Path(path or config.PATH_BM25_PICKLE)
    _register_for_unpickle()
    with open(path, "rb") as fh:
        bm25: BilingualBM25 = pickle.load(fh)
    bm25.translator = EnDeTranslator(device=config.DEVICE) if with_translator else None
    return bm25


# -------------------------------------------------------------------- Dense
class DenseRetriever:
    """Light wrapper around a Chroma store with the e5 ``query: `` prefix."""

    def __init__(self, vectordb: Chroma, k: int = 100) -> None:
        self.store, self.k = vectordb, k

    @staticmethod
    def _prep(q: str) -> str:
        return "query: " + q.strip()

    def search(self, query: str, top_k: Optional[int] = None) -> List[Document]:
        k = top_k or self.k
        hits = self.store.similarity_search_with_score(self._prep(query), k=k)
        out: List[Document] = []
        for doc, dist in hits:
            doc.metadata["dense_score"] = 1.0 - float(dist)
            out.append(doc)
        return out


def load_dense(
    persist_dir: Optional[pathlib.Path] = None,
    k: int = 100,
    device: Optional[str] = None,
    model_name: str = "intfloat/multilingual-e5-large-instruct",
) -> DenseRetriever:
    persist_dir = pathlib.Path(persist_dir or config.PATH_CHROMA_DIR)
    embeds = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": device or config.DEVICE},
        encode_kwargs={"batch_size": 32, "normalize_embeddings": True},
    )
    db = Chroma(persist_directory=str(persist_dir), embedding_function=embeds)
    return DenseRetriever(db, k=k)


# ----------------------------------------------------------------- GraphRAG
class GraphRAGRetriever:
    """Mirrors the previous team's ``load_graphrag.retrieve`` but is parametrised."""

    def __init__(
        self,
        root: Optional[pathlib.Path] = None,
        chunk_pkl: Optional[pathlib.Path] = None,
        embed_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> None:
        self.root = pathlib.Path(root or config.PATH_GRAG_ROOT)
        self.emb_dir = self.root / "embeddings"
        self.comm2chunk_path = self.root / "comm2chunk_fixed.json"
        self.chunk_pkl = pathlib.Path(chunk_pkl or config.PATH_LANG_NORM_PKL)
        self._embedder = SentenceTransformer(embed_model)
        self._emb_cache: Dict[int, Tuple[np.ndarray, list]] = {}
        self._chunks: Optional[Dict[str, Document]] = None
        self._chunk_vec: Dict[str, np.ndarray] = {}
        self._comm2chunk: Optional[dict] = None

    def _load_emb(self, level: int) -> Tuple[np.ndarray, list]:
        if level not in self._emb_cache:
            mat = np.load(self.emb_dir / f"EMB_fixed_C{level}.npy")
            cid = json.loads((self.emb_dir / f"CID_fixed_C{level}.json").read_text())
            self._emb_cache[level] = (mat, cid)
        return self._emb_cache[level]

    def _load_chunks(self) -> Dict[str, Document]:
        if self._chunks is not None:
            return self._chunks
        with open(self.chunk_pkl, "rb") as f:
            docs_norm = pickle.load(f)
        out: Dict[str, Document] = {}
        for d in docs_norm:
            raw = d.metadata.get("original_text") or d.page_content
            out[d.metadata["chunk_id"]] = Document(page_content=raw, metadata=d.metadata)
        self._chunks = out
        return out

    def _vec(self, cid: str) -> np.ndarray:
        if cid not in self._chunk_vec:
            self._chunk_vec[cid] = self._embedder.encode(
                [self._load_chunks()[cid].page_content], normalize_embeddings=True
            )[0]
        return self._chunk_vec[cid]

    def retrieve(
        self,
        query: str,
        *,
        level: str = "C1",
        k_comms: int = 24,
        top_k: int = 100,
    ) -> List[Document]:
        L = int(level.lstrip("C"))
        emb_mat, cid_list = self._load_emb(L)
        chunks = self._load_chunks()
        if self._comm2chunk is None:
            self._comm2chunk = json.loads(self.comm2chunk_path.read_text())

        q_vec = self._embedder.encode([query], normalize_embeddings=True)[0]
        sims = emb_mat @ q_vec
        best_idx = sims.argsort()[::-1][:k_comms]
        cand: set = set()
        for idx in best_idx:
            cand.update(self._comm2chunk.get(cid_list[idx], []))
        if not cand:
            return []

        scored = [(cid, float(self._vec(cid) @ q_vec)) for cid in cand]
        scored.sort(key=lambda x: x[1], reverse=True)
        out: List[Document] = []
        for cid, sim in scored[:top_k]:
            d = chunks[cid]
            d.metadata["grag_score"] = (sim + 1) / 2
            out.append(d)
        return out


def load_graphrag(
    root: Optional[pathlib.Path] = None,
    chunk_pkl: Optional[pathlib.Path] = None,
) -> GraphRAGRetriever:
    return GraphRAGRetriever(root=root, chunk_pkl=chunk_pkl)
