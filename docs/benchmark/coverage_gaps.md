# Corpus coverage gaps (documented separately, NOT among our 10 benchmark cases)

Following the course instructor's guidance (17 Nov), facts that exist in the original HTML (`HKNews.zip`) but **not** in the shared indexed chunks (`docs_fixed_norm.pkl`) are listed here instead of in the benchmark. The retrieval artifacts stay unchanged for all groups, so the system cannot answer these questions. A failure on them is a **data preparation** issue, not a retrieval or generation failure.

All entries were checked against the chunks with `python -m src.ours.benchmark.fill_chunk_ids --pkl <path>/docs_fixed_norm.pkl --find "<phrase>"` (0 matching chunks) and against the raw page.

| # | Example question | Answer in the original HTML | Source page (HKNews.zip) | Why it is missing from the index |
|---|---|---|---|---|
| 1 | How much were ETH's annual tuition fees before the 2017 decision to raise them? | CHF 1,160 per year; raised by CHF 500 in two steps of CHF 250 (autumn 2019/20 and 2020/21) | `en_news_events/2017/09/tuition-fees-at-eth-to-be-increased.html` | Page indexed, opening paragraph lost |
| 2 | How many students took part in the 55th International Chemistry Olympiad at ETH? | Around 350 young chemists from some 90 countries, on the Hönggerberg campus (July 2023) | `en_news_events/2023/07/first-time-in-switzerland-the-55th-chemistry-olympiad.html` | Page indexed, opening paragraph lost |
| 3 | How many private and municipal buildings does ETH's city-centre district heating supply? | 142 private and municipal buildings, plus 29 properties used by ETH | `de_internal/2024/04/eth-zuerich-verkauft-fernwaermeversorgung-an-die-stadt-zuerich.html` | Page indexed, paragraph lost (sale price and transfer date *are* indexed, see case G02-011) |
| 4 | When was the ETH spin-off Fixposition founded? | August 2017 | `en_news_events/2018/11/high-precision-navigation-for-driverless-cars-and-drones.html` | Page indexed, opening paragraph lost |
| 5 | How do tendons become stiffer, according to ETH researchers? | A force sensor (ion channel) in tendon cells detects shear between collagen fibres, lets calcium in, and triggers enzymes that cross-link the fibres | `en_news_events/2021/05/how-tendons-become-stiffer-and-stronger.html` | Page indexed, opening paragraphs lost (the E756del / malaria part *is* indexed, see case G02-003) |
| 6 | What did ETH President Joël Mesot say in April 2024 about raising tuition fees to cover the budget gap? | He and the Executive Board considered raising fees the wrong way (ETH's free reserves would be used up by the end of 2025) | `de_internal/2024/04/unsere-frei-verfuegbaren-reserven-werden-spaetestens-ende-2025-aufgebraucht-sein.html` | Page not indexed at all |
| 7 | What place did ETH reach in the QS ranking published in June 2023? | Seventh place, up two positions | `en_news_events/2023/06/qs-ranking-eth-zurich-takes-a-top-spot-thanks-to-long-term-investments-in-research-and-teaching.html` | English page indexed, opening paragraph lost; the same fact survives in a German chunk from September 2023 (used in case G02-006) |

## Not coverage gaps (for reference)

- **Reference benchmark Q18 (Hong Kong):** the gold answer (CUHK / HKUST agreements) appears neither in the raw HTML nor in the index, so it lies outside the corpus altogether.
- **Reference benchmark Q6 (e-Sling) and Q17 (bird song learning):** no supporting text in the raw HTML or the index, so abstaining is correct.

## How to use this list

- In the final report, it helps separate **data preparation** failures from retrieval and generation failures.
- In our evaluation, a wrong answer or abstention on these facts should not be counted against the agent.
