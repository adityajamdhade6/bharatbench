# BharatBench analysis

Run `run-5`, scored 2026-10-07. Every number below is read from `results/run-5/scores.json`; scores are the mean item score (0 to 1) shown as a percentage, with 95% percentile-bootstrap intervals (10,000 resamples over tasks). Rankings use the unrounded scores; displayed decimals are added wherever rounding would make different scores look equal.

## Overall leaderboard

| Rank | Model | Score | 95% interval | Tasks scored |
|---:|---|---:|---:|---:|
| 1 | qwen3.8-27b | 94.4% | 88.9% to 98.9% | 90 |
| 2 | qwen3.8-flash | 94.1% | 88.8% to 98.4% | 94 |
| 3 | gemini-3.1-flash-lite | 89.4% | 83.0% to 94.7% | 94 |
| 3 | gemini-3.5-flash-lite | 89.4% | 83.0% to 95.7% | 94 |
| 5 | llama-4-maverick | 86.2% | 78.7% to 92.6% | 94 |
| 6 | llama-3.3-70b-instruct | 74.9% | 65.7% to 83.2% | 94 |
| 7 | mistral-small-2603 | 64.0% | 54.4% to 73.6% | 94 |

The top model, qwen3.8-27b, cannot be separated from: qwen3.8-flash, gemini-3.1-flash-lite, gemini-3.5-flash-lite, llama-4-maverick (their 95% intervals overlap with its interval). Treat the order among them as unsettled.

Excluded replies (no answer could be obtained, so not counted as wrong): qwen3.8-27b 4.

## Per category

| Model | GST & tax math | Hinglish & Hindi support | Indian documents | Indian law & policy | Payments & banking |
|---|---:|---:|---:|---:|---:|
| qwen3.8-27b | 100.0% | 100.0% | 100.0% | 90.0% | 80.0% |
| qwen3.8-flash | 100.0% | 100.0% | 97.5% | 90.0% | 84.2% |
| gemini-3.1-flash-lite | 70.0% | 100.0% | 100.0% | 90.0% | 89.5% |
| gemini-3.5-flash-lite | 70.0% | 100.0% | 100.0% | 90.0% | 89.5% |
| llama-4-maverick | 95.0% | 100.0% | 100.0% | 65.0% | 73.7% |
| llama-3.3-70b-instruct | 70.0% | 97.8% | 73.8% | 70.0% | 68.4% |
| mistral-small-2603 | 40.0% | 94.4% | 85.0% | 60.0% | 47.4% |
| **Average of models** | **77.9%** | **98.9%** | **93.7%** | **79.3%** | **76.1%** |
| *Tasks* | *20* | *15* | *20* | *20* | *19* |

**Hardest category:** Payments & banking, with the lowest average across the 7 models (76.1%). **Easiest:** Hinglish & Hindi support (98.9%). The single lowest model-category score is mistral-small-2603 on GST & tax math (40.0%).

## English, Hindi and Hinglish

| Model | English (n) | Hindi (n) | Hinglish (n) | English minus Hinglish |
|---|---:|---:|---:|---:|
| qwen3.8-27b | 93.7% (63) | 100.0% (7) | 95.0% (20) | −1.3 pp |
| qwen3.8-flash | 91.7% (66) | 100.0% (7) | 100.0% (21) | −8.3 pp |
| gemini-3.1-flash-lite | 89.4% (66) | 100.0% (7) | 85.7% (21) | +3.7 pp |
| gemini-3.5-flash-lite | 89.4% (66) | 100.0% (7) | 85.7% (21) | +3.7 pp |
| llama-4-maverick | 81.8% (66) | 85.7% (7) | 100.0% (21) | −18.2 pp |
| llama-3.3-70b-instruct | 75.4% (66) | 85.7% (7) | 69.8% (21) | +5.5 pp |
| mistral-small-2603 | 59.1% (66) | 100.0% (7) | 67.5% (21) | −8.4 pp |

Averaged over the 7 models, English accuracy is 82.9% and Hinglish accuracy is 86.2%, a difference of 3.3 percentage points (Hinglish higher). Hinglish is lower than English for 3 of 7 models.

Read this with care: the tasks are different questions in each language, not translations. Hinglish and Hindi tasks are mostly customer-support classification and extraction (21 Hinglish tasks scored per model), while English tasks include the harder calculations, so a language gap here is confounded with task type. The Hindi sample is small.

## Ten example failures

Selected by rule, not by hand: cycle through the categories, take the tasks that the most models failed, one model per task. Each shows the model's answer next to the reference answer. Some are format failures rather than wrong facts: the scorer is strict, so an extra word in an extracted field or a long explanation where a bare answer was requested scores zero.

### 1. gst-007 · GST & tax math · gemini-3.1-flash-lite

- **Prompt:** Ek dealer ne ₹15,000 ki list price wali machine par 12% trade discount diya, aur invoice me discount GST se pehle minus kiya gaya hai. Uske baad 18% GST lagta hai. Customer ko total kitna dena hoga? Reply with only the number (rupees, no c…
- **Model answer:** 15660
- **Correct answer:** 15576
- **Scorer:** parsed 15660, expected 15576; 4 of 7 models failed this task.

### 2. hin-010 · Hinglish & Hindi support · llama-3.3-70b-instruct

- **Prompt:** Extract the details from the customer message. Reply with only a JSON object with these keys: order_id (string), amount (number in rupees), return_date (string exactly as written). Message: "Order ID OD2025-7731 ka refund ₹1,499 abhi tak n…
- **Model answer:** ```json { "order_id": "OD2025-7731", "amount": 1499, "return_date": "12 March ko" } ```
- **Correct answer:** {"order_id": "OD2025-7731", "amount": 1499, "return_date": "12 March"}
- **Scorer:** 2/3 fields correct; wrong: return_date; 1 of 7 models failed this task.

### 3. doc-014 · Indian documents · mistral-small-2603

- **Prompt:** What is the total of all debits in this synthetic bank statement? *** SYNTHETIC DOCUMENT - NOT A REAL BANK STATEMENT *** Account holder: Meena Test (synthetic) Account: XXXX0001 2345 Statement period: 01-09-2025 to 30-09-2025 Opening balan…
- **Model answer:** 10290
- **Correct answer:** 9730
- **Scorer:** parsed 10290, expected 9730; 2 of 7 models failed this task.

### 4. law-003 · Indian law & policy · qwen3.8-27b

- **Prompt:** Under section 41 of the Consumer Protection Act, 2019, within how many days from the date of the order must an appeal against a District Commission's order be filed with the State Commission? Reply with only the number.
- **Model answer:** 30
- **Correct answer:** 45
- **Scorer:** parsed 30, expected 45; 4 of 7 models failed this task.

### 5. pay-009 · Payments & banking · gemini-3.5-flash-lite

- **Prompt:** Per the RBI framework on turnaround time (TAT) for failed transactions, by which day must the reversal be completed when a UPI payment to a merchant debits the customer but the transaction confirmation is not received? Reply in the form T+…
- **Model answer:** T+1
- **Correct answer:** T+5
- **Scorer:** normalised reply 't1' vs reference 't5'; 7 of 7 models failed this task.

### 6. gst-009 · GST & tax math · gemini-3.1-flash-lite

- **Prompt:** In a month a trader made taxable sales of ₹8,00,000 at 18% GST. Eligible purchases were ₹5,50,000 at 18% GST and ₹1,20,000 at 5% GST, and the full GST on both purchases is claimable as input tax credit. How much GST must the trader pay in …
- **Model answer:** 38400
- **Correct answer:** 39000
- **Scorer:** parsed 38400, expected 39000; 4 of 7 models failed this task.

### 7. hin-012 · Hinglish & Hindi support · mistral-small-2603

- **Prompt:** Extract the details from the customer message. Reply with only a JSON object with these keys: txn_id (string), amount (number in rupees), date (string exactly as written). Message: "Mera UPI txn ID 412398765012 hai, ₹800 kate hain par merc…
- **Model answer:** ```json { "txn_id": "412398765012", "amount": 800, "date": "5 Aug thi" } ```
- **Correct answer:** {"txn_id": "412398765012", "amount": 800, "date": "5 Aug"}
- **Scorer:** 2/3 fields correct; wrong: date; 1 of 7 models failed this task.

### 8. doc-015 · Indian documents · llama-3.3-70b-instruct

- **Prompt:** Is synthetic bank statement mein saare credits ka total kitna hai? *** SYNTHETIC DOCUMENT - NOT A REAL BANK STATEMENT *** Account holder: Vikram Sample (synthetic) Account: XXXX0002 7788 Statement period: 01-10-2025 to 31-10-2025 Opening b…
- **Model answer:** 30000
- **Correct answer:** 29750
- **Scorer:** parsed 30000, expected 29750; 2 of 7 models failed this task.

### 9. law-007 · Indian law & policy · llama-4-maverick

- **Prompt:** A consumer paid exactly ₹50,00,000 (₹50 lakh) as consideration for a service and wants to file a complaint. Under the Consumer Protection (Jurisdiction of the District Commission, the State Commission and the National Commission) Rules, 20…
- **Model answer:** ## Step 1: Understand the pecuniary jurisdiction limits for Consumer Commissions under the Consumer Protection Act, 2019, and the rules framed thereunder. The Consumer Protection (Jurisdiction of the District Commission, the State Commission and the National Commission) Rules, 2021, specify the pec…
- **Correct answer:** District
- **Scorer:** normalised reply 'step1understandthepecuniaryjurisdictionlimitsforconsumercomm' vs reference 'district'; 4 of 7 models failed this task.

### 10. pay-008 · Payments & banking · qwen3.8-flash

- **Prompt:** Per the RBI framework on turnaround time (TAT) for failed transactions, by which day (counted from the transaction day T) must a bank complete the auto-reversal when a UPI fund transfer debits the sender but does not credit the beneficiary…
- **Model answer:** T+2
- **Correct answer:** T+1
- **Scorer:** normalised reply 't2' vs reference 't1'; 4 of 7 models failed this task.
