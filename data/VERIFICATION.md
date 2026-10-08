# Verification record (2026-10-07)

The `"verified": true` flags were set by an AI assistant (Claude) at the dataset owner's request, **not by a human reviewer**.
Each task was confirmed in one of two ways; anything that could not be confirmed was left `false`.

| Tasks | How confirmed |
|---|---|
| gst-001 – gst-020 | Recomputed with separate exact-fraction code (not the generator). Income-tax slabs, the 87A rebate (nil tax up to 12,00,000) and the 75,000 standard deduction match PIB / Income Tax Department pages; tax at 16,00,000 reproduces the published 1,20,000. |
| doc-001 – doc-020 | Invoices and bank statements were re-parsed from the prompt text and recomputed line by line (line amounts, discounts, GST, grand totals, running balances). Rent-agreement values were checked against the clauses in the prompt. |
| hin-001 – hin-008 | Read and judged independently (intent / sentiment / language labels; 9 days > 7-day window). |
| hin-009 – hin-015 | Every extracted value was checked to occur verbatim in the customer message. |
| law-001 – law-003 | Consumer Protection Act 2019 s.69 (two years) and s.41 (45 days; 50% pre-deposit) match the statute text as quoted on legal-database mirrors; the India Code pages were unreachable. |
| law-004 – law-007 | Thresholds (District <= 50 lakh, State 50 lakh–2 crore, National > 2 crore, by consideration paid) read in the Rules, 2021 text (copy hosted on thc.nic.in). |
| law-008 – law-013 | RTI Act 2005 text read directly (s.6(3), 7(1), 19(1), 19(3), 20(1)). |
| law-014 | RTI Rules 2012 PDF on cic.gov.in (application fee ₹10; BPL exempt). |
| law-015 – law-020 | Code on Social Security 2020 text read directly (s.53, s.60). |
| pay-001 – pay-018 | RBI TAT table (Circular of 20 Sep 2019), RBI limited-liability circular (6 Jul 2017) and RBI KYC FAQs read directly; compensation arithmetic recomputed. "Plain days" for T+N follows the circular's "T = calendar date". |
| pay-019 | RBI Integrated Ombudsman FAQ (30-day no-reply ground). |

## Held back (`verified: false`)
hin-016 – hin-020 and pay-020: the six **rubric** tasks. Their criteria are judgement calls and the LLM judge has not been validated against human grades.

A human spot-check is still pending: a flag only means the assistant could confirm the answer, not that a person signed off.

## Corrections
doc-008: the reference names carried the "(synthetic)" label from the prompt; models that wrote the plain names were marked wrong in the first scored run. The reference now holds the plain names (corrected 2026-10-08).
