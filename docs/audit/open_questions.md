# Open questions for Guang (DRAFT, Q&A 1)

1. **Q1 label.** The corpus implies Olaf Kübler (he stepped down at the end of 2004), so Q1 is answerable, not out-of-corpus. Should the shared benchmark be corrected?
2. **Q6 and Q17 gold answers.** We find no supporting text in the raw HTML for e-Sling or for bird song learning. Were these gold answers written from sources outside the corpus?
3. **Q18 gold answer.** The gold lists CUHK and HKUST agreements that aren't in the corpus. Is the expected behaviour a partial answer from the corpus, or ABSTAIN?
4. **Typos in five questions** ("conneczons", "consumpzon", …). Should evaluation use the original or corrected questions?
5. **Common evaluation config.** Which models must everyone use (the most expensive part is the generation and verification model), and which judge model for correctness?
6. **German questions.** Should the shared evaluation also run the `question_de` versions?
7. **Qrels.** The gold-chunk labels are gpt-4o-mini relevance scores cut off at 0.5. Are they the official ground truth for retrieval metrics, given cases like Q1 where they missed the evidence?
