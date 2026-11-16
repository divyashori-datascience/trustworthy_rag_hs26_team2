"""Local baseline reproduction (Step 1) for the Adv. GenAI capstone.

Loads the previous semester's prebuilt retrievers (BM25, Dense, GraphRAG) from
``Baseline/storage/full_corpus/``, runs the three orchestration strategies
(Waterfall, Voting, Confidence) on the bilingual benchmark, and reports
retrieval metrics (P@k, Recall@k, MRR, NDCG) plus latency.

Key modules
-----------
config          : all path constants and model/parameter settings
retrievers      : loader wrappers for BM25, Dense (ChromaDB), and GraphRAG
orchestration   : Waterfall / Voting / Confidence strategies + BaselineSystem
evaluation      : pytrec_eval metric computation
failure_analysis: failure taxonomy classifier (retrieval / ranking / partial …)
"""
