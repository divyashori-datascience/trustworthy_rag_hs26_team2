# Open questions for the course instructor (DRAFT, Q&A 1)

1. **Q1 label.** The corpus implies Olaf Kübler (he stepped down at the end of 2004), so Q1 is answerable, not out-of-corpus. Should the shared benchmark be corrected?
2. **Q6 and Q17 gold answers.** No indexed chunk (and no raw page) mentions e-Sling or bird song learning, so the system was right to abstain. Should these labels be changed to ABSTAIN?
3. **Q18 gold answer.** The gold lists CUHK and HKUST agreements that aren't in the corpus. Is the expected behaviour a partial answer from the corpus, or ABSTAIN?
4. **Typos in five questions** ("conneczons", "consumpzon", …). Should evaluation use the original or corrected questions?
5. **Common evaluation config.** Which models must everyone use (the most expensive part is the generation and verification model), and which judge model for correctness?
6. **German questions.** Should the shared evaluation also run the `question_de` versions?
7. **Qrels.** The gold-chunk labels are gpt-4o-mini relevance scores cut off at 0.5. Are they the official ground truth for retrieval metrics, given cases like Q1 where they missed the evidence?
8. **Index coverage.** 37% of pages are not in the shared index, and the opening paragraph is missing on 92% of indexed pages (`index_coverage.md`). Should benchmark answers be judged against the indexed chunks? And is re-chunking in scope for improvements?
