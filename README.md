# @AppleSupport AI Customer Support System

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-16%20passed-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An end-to-end, modular, and empirically evaluated AI customer support prototype for **`@AppleSupport`**, built on Kaggle's real-world *Customer Support on Twitter* dataset (`thoughtvector/customer-support-on-twitter`).

The system triages incoming customer messages, classifies them into 6 empirical intents, retrieves relevant historical resolution precedents using semantic vector search, synthesizes grounded replies with anti-hallucination guardrails, and conservatively decides between **`AUTO_HANDLE`** and **`ESCALATE_TO_HUMAN`**.

Evaluated against a 200-sample golden set with strict leakage prevention and benchmarked against two empirical baselines.

---

## ⚡ Quickstart: Reproduce Results in Under 15 Minutes

### 1. Clone & Set Up Environment
```bash
git clone https://github.com/KodakandlaSahtihi-29/hiver-sde-intern.git
cd hiver-sde-intern

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables (Optional)
The system works 100% out of the box with zero external API keys required (using deterministic grounded synthesis and a transparent evaluation rubric). If you wish to use Google Gemini for generative completions and LLM judging:
```bash
cp .env.example .env
# Configure your GEMINI_API_KEY inside .env
```

### 3. Golden Set Review & Leak-Free Validation
The evaluation corpus is isolated from training and retrieval. A review queue of 200 real held-out AppleSupport interactions is maintained in `data/golden/review_queue.csv` (with full annotation criteria in `data/golden/REVIEW_GUIDE.md`). Machine-proposed labels are kept separate from final human labels.

```bash
# 1. Parse raw sample and compute measured dataset statistics
python scripts/prepare_data.py

# 2. Import reviewed CSV into the canonical golden set (once human-verified):
python scripts/review_golden_set.py --import-csv data/golden/review_queue.csv

# 3. Programmatically validate 200 golden examples & verify 0% leakage:
python scripts/validate_golden_set.py
```

### 4. Run the Support Agent
```bash
# Test single query (Safe Auto-Handle example)
python scripts/run_agent.py --query "My iPhone battery dies within 30 minutes after updating to iOS 11"

# Test single query (Account Security Escalation example)
python scripts/run_agent.py --query "My Apple ID is locked and I cannot receive the verification code"

# Or launch interactive terminal session
python scripts/run_agent.py --interactive
```

### 5. Run Full Evaluation (Baselines vs. Agent)
```bash
python scripts/evaluate.py
```
This generates:
- `results/metrics.csv` (Headline comparison against both baselines)
- `results/per_intent_metrics.csv` (Per-intent breakdown)
- `results/evaluation_results.jsonl` (All 200 individual predictions, confidence, and judge scores)

### 6. Run Automated Test Suite
```bash
pytest tests/ -v
```
*(All 16 unit tests pass in under 3 seconds)*

---

## 📊 Measured Benchmark Results (Zero Fabrication)

All numbers are measured directly from execution against the 200-sample human-verified golden set:

| Model / System | Intent Accuracy | Intent Macro F1 | Intent Weighted F1 | Escalation Accuracy | Escalate Recall (Human) | Auto-Handle F1 | Retrieval Concordance | Judge Score (Deterministic Fallback) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline 1 (Majority Class)** | 0.2200 | 0.0601 | 0.0793 | 0.7950 | 0.0000 | 0.8858 | N/A | N/A |
| **Baseline 2 (TF-IDF + LogReg on Weak Labels)** | 0.5250 | 0.3886 | 0.5345 | 0.7950 | 0.0244 | 0.8852 | N/A | N/A |
| **Proposed AI Support Agent** | **0.6800** | **0.6246** | **0.7051** | **0.8450** | **0.7805** | **0.8984** | **43.5%** | **4.40 / 5.0** |

*Note on Baseline 2: Trained exclusively on the 3,499 training corpus using weak/heuristic pseudo-labels derived from keyword matching. The 200 golden evaluation examples were strictly held out and never seen during training.*

*Note on Quality Score: Evaluated using the deterministic rule-anchored rubric because no remote LLM API key was provided in the offline evaluation environment. The codebase includes the full LLM-as-a-Judge implementation (`src/evaluation/judge.py`), which calls Gemini 1.5 Flash when `GEMINI_API_KEY` is set.*

### Per-Intent Performance (Proposed AI Agent):
| Intent Category | Precision | Recall | F1 Score | Support |
| :--- | :---: | :---: | :---: | :---: |
| `Device_Performance_Battery` | 0.9574 | 0.7143 | **0.8182** | 63 |
| `Account_Access_Security` | 0.8750 | 0.7000 | **0.7778** | 30 |
| `Connectivity_Hardware` | 0.9259 | 0.5952 | 0.7246 | 42 |
| `Software_Bug_OS_Update` | 0.5469 | 0.7955 | 0.6481 | 44 |
| `Billing_Subscriptions` | 0.4000 | 0.6667 | 0.5000 | 6 |
| `General_Product_Inquiry` | 0.2143 | 0.4000 | 0.2791 | 15 |

---

## 🔍 "What is Misleading About My Headline Number?"

Our headline metric is: **Intent Macro F1 = 0.6246 (62.46%), Intent Accuracy = 68.00%, and Escalation Accuracy = 84.50%**.

Why this number is misleading without context:
1. **Macro F1 penalizes low-frequency minor classes**: The low score on `General_Product_Inquiry` (F1: 0.2791, support: 15) pulls down Macro F1, whereas high-volume Battery (F1: 0.8182) and Security (F1: 0.7778) perform strongly. Weighted F1 is 0.7051.
2. **Sample Size Margin of Error**: With $N=200$, the 95% confidence interval is $\pm 6.5\%$ on 68.0% accuracy (true population accuracy lies between 61.5% and 74.5%).
3. **Escalation Accuracy (84.5%) masks 9 false negatives**: The trivial baseline gets 79.5% escalation accuracy by *never escalating*. Our agent achieves 78.05% human escalation recall (detecting 32/41 high-risk cases), but 9 un-escalated cases slip through.
4. **Retrieval Concordance is 43.5%**: In 56.5% of queries, vector search retrieved an exemplar from a different intent bucket, showing that short tweets suffer from lexical overlap drift even when overall response tone scores 4.40/5.0.

*(See full breakdown in [reports/report.md](reports/report.md))*.

---

## 🏗️ Project Architecture

```
Customer Message
       │
       ▼
[Text Cleaning & Mention Normalization]
       │
       ▼
[Intent Classification (6 Empirical Classes)]
       │
       ▼
[Historical Retrieval (TF-IDF Cosine Vector Store, K=3)]
       │
       ▼
[Evidence Sufficiency & Confidence Scorer (sim >= 0.18)]
       │
       ▼
[Conservative Escalation Engine (AUTO_HANDLE vs ESCALATE_TO_HUMAN)]
       │
       ▼
[Grounded Reply Generation (Anti-Hallucination Guardrails)]
       │
       ▼
Structured Output JSON (Intent, Reply, Decision, Stated Reason, Evidence)
```

Structured Output Example:
```json
{
  "intent": "Account_Access_Security",
  "intent_confidence": 0.912,
  "reply": "We understand this Apple ID / account security issue is urgent. Because account and identity verification involves sensitive personal data, our automated system cannot modify account credentials. Please follow the secure recovery steps at https://iforgot.apple.com or contact an Apple Support specialist directly.",
  "decision": "ESCALATE_TO_HUMAN",
  "reason": "Account access and identity verification require human agent review or authenticated recovery channel.",
  "evidence_sufficiency": "adequate",
  "evidence": [
    {
      "conversation_id": "379fbc9474cdeee48caf9e28aa058d42",
      "historical_query": "My icloud account has been locked for security reasons. Even my Apple ID is locked. I can't receive my confirmation code.",
      "historical_reply": "We're happy to assist. This article can help you to unlock your account: https://t.co/HH37urdbz9 DM us with any questions. https://t.co/GDrqU22YpT",
      "similarity_score": 0.5051
    }
  ]
}
```

---

## 📂 Repository Structure

```
hiver-sde-intern/
├── README.md                          # Quickstart & reproduction (< 15 mins)
├── ARCHITECTURE.md                    # Technical specs, latency, and schemas
├── QUICK_EXPLANATION.md               # Interview defense & live coding Q&A
├── requirements.txt                   # Pinned dependencies
├── .env.example                       # API key template
├── .gitignore                         # Prevents committing secrets & large cache
│
├── data/
│   ├── raw/apple_sample.parquet       # Raw brand sample (5,000 Apple records)
│   ├── processed/                     # Parsed & normalized dialogue pairs (4,953 items)
│   └── golden/
│       ├── candidates_for_review.jsonl# Candidate pool (220 items)
│       ├── review_queue.csv           # Review queue with proposed machine labels
│       └── golden_set.jsonl           # 200 verified golden evaluation examples
│
├── src/
│   ├── data/                          # Loader, schema, leakage-prevention split
│   ├── preprocessing/                 # Text normalization, turn extraction
│   ├── intent/                        # Taxonomy, rule & semantic classifier
│   ├── retrieval/                     # TF-IDF sublinear vector store
│   ├── generation/                    # Grounded reply generator & anti-hallucination
│   ├── escalation/                    # Evidence-aware conservative escalation policy
│   └── evaluation/                    # Metrics, Baselines, LLM Judge rubric
│
├── scripts/
│   ├── prepare_data.py                # Measures dynamic counts & parses threads
│   ├── sample_data.py                 # Reproducible data sampling utility
│   ├── create_golden_candidates.py    # Extracts candidate pool from held-out split
│   ├── review_golden_set.py           # Review queue & confirmation workflow
│   ├── validate_golden_set.py         # Validates schema, size, & 0% leakage
│   ├── run_agent.py                   # Single-query & interactive CLI agent
│   └── evaluate.py                    # Complete evaluation harness
│
├── tests/                             # 16 unit tests across all modules
├── reports/
│   ├── report.md                      # Comprehensive technical report (<= 6 pages)
│   └── decision_log.md                # 12 non-obvious engineering decisions
│
└── results/
    ├── metrics.csv                    # Empirical baseline vs agent comparison
    ├── per_intent_metrics.csv         # Granular per-intent breakdown
    ├── evaluation_results.jsonl       # Full evaluation records with judge scores
    └── failure_analysis.md            # Top 5 empirical failure modes
```

---

## 📄 Key Documentation Links

- [Technical Report (reports/report.md)](reports/report.md)
- [Architectural Decision Log (reports/decision_log.md)](reports/decision_log.md)
- [Failure Mode Analysis (results/failure_analysis.md)](results/failure_analysis.md)
- [Interview Explanation & Defense (QUICK_EXPLANATION.md)](QUICK_EXPLANATION.md)
- [Architecture & Latency Profile (ARCHITECTURE.md)](ARCHITECTURE.md)
