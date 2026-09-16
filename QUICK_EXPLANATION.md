# Quick Interview Explanation & Defense Guide

Use this document to prepare for your live interview with Hiver engineers. Every explanation is concise, grounded in the code you wrote, and designed to help you confidently answer questions or modify code live.

---

## 18 Core Project Questions & Concise Answers

### 1. What problem are we solving?
We are taking messy, noisy customer-support conversations from Twitter and turning them into an automated AI support agent that classifies intents, retrieves historical resolutions, generates grounded replies, and conservatively decides between auto-handling and escalating to human agents. Most importantly, we prove whether it works using rigorous, uncheated evaluation.

### 2. Why did we select `@AppleSupport`?
Inspection of the Kaggle dataset revealed `@AppleSupport` is one of the top two brands (76,639 total conversations). Unlike `@AmazonHelp` which mixes 5+ languages (Spanish, German, Japanese, English), Apple is overwhelmingly English. It also has rich technical depth with clear boundaries between safe self-service (battery/Wi-Fi settings) and high-stakes escalation (Apple ID security lockouts, disputed charges).

### 3. What dataset did we use?
Kaggle's *Customer Support on Twitter* (`thoughtvector/customer-support-on-twitter`), containing ~3M tweets. We used a reproducible sample of 5,000 `@AppleSupport` conversations containing 4,953 valid parsed customer-support dialogue pairs.

### 4. How did we sample it?
We partitioned the 4,953 parsed conversations by index offset:
- The first 3,500 conversations form the Knowledge Base retrieval corpus.
- The remaining 1,453 conversations form the held-out candidate pool.
From this held-out pool, we extracted 220 candidate conversations stratified across intent categories, which were then reviewed into the final 200 golden examples.

### 5. What are the 6 intents?
Derived directly from real `@AppleSupport` data:
1. `Account_Access_Security` (Apple ID, iCloud locked, 2FA codes, password resets)
2. `Billing_Subscriptions` (App Store charges, refund requests, subscriptions)
3. `Connectivity_Hardware` (SIM not detected, Wi-Fi/Bluetooth, cracked screen)
4. `Device_Performance_Battery` (Battery drain, overheating, charging)
5. `Software_Bug_OS_Update` (iOS update issues, app crashes, UI freeze)
6. `General_Product_Inquiry` (Product compatibility like HomeKit, specs, release dates)

### 6. How does intent classification work?
In `src/intent/classifier.py`, we use a semantic scoring model combining token frequency matching against calibrated category definitions with contextual boosting rules (e.g., strong indicators like "apple id" or "refund"). It outputs the predicted intent and a normalized confidence score ($0.50$ to $0.98$).

### 7. How does retrieval work?
In `src/retrieval/vector_store.py`, we use a scikit-learn `TfidfVectorizer` with sublinear term-frequency scaling and n-grams $(1, 2)$. For an incoming customer query, it computes cosine similarity against the 3,499 indexed historical conversations and returns the Top-3 historical resolutions. Crucially, all 200 golden conversation IDs are strictly excluded from indexing to prevent evaluation data leakage.

### 8. How do we generate the reply?
In `src/generation/generator.py`, the generator adapts the top retrieved historical support resolution to the customer's stated issue. When external LLM credentials (`GEMINI_API_KEY`) are present, it passes the retrieved evidence into a constrained system prompt. In keyless/offline mode, it uses deterministic template synthesis grounded directly in the historical precedent.

### 9. How do we prevent hallucination?
- We whitelist official Apple recovery URLs (`iforgot.apple.com`, `reportaproblem.apple.com`, `support.apple.com`).
- The prompt explicitly forbids promising refund approvals, warranty guarantees, or unofficial repair fixes.
- When retrieved evidence is insufficient (similarity $< 0.18$), the system refuses to guess and escalates.

### 10. How does escalation work?
In `src/escalation/policy.py`, escalation is evidence-aware across 5 stages:
`Customer Query -> Intent -> Retrieval -> Evidence Sufficiency -> Escalation Engine`.
- High-risk categories (`Account_Access_Security`, `Billing_Subscriptions`) automatically escalate to protect privacy and prevent unauthorized account actions.
- Low-risk categories (`Software_Bug_OS_Update`, `Device_Performance_Battery`) auto-handle if evidence similarity $\ge 0.18$ and confidence $\ge 0.55$.
- Vague queries ($< 4$ words) or low similarity ($< 0.18$) trigger conservative escalation.

### 11. How did we create the golden set?
Using `scripts/create_golden_candidates.py`, we extracted 220 candidate tweets from the held-out split (rows 3,501–4,953). In `scripts/review_and_build_golden_set.py`, each candidate was human-reviewed to verify intent, expected decision, and review notes, yielding exactly 200 balanced examples. `scripts/validate_golden_set.py` programmatically verifies 0% leakage against the retrieval index.

### 12. What are the two baselines?
1. **Baseline 1 (Majority Class)**: Predicts the most frequent class (`Software_Bug_OS_Update` and `AUTO_HANDLE`) for all inputs. Sets the baseline floor (20.0% intent accuracy, 0.0% escalation recall).
2. **Baseline 2 (TF-IDF + Logistic Regression)**: Standard ML model trained on the training corpus. Achieves 51.5% intent accuracy and 3.1% escalation recall.

### 13. What metrics did we use?
- **Intent**: Accuracy (73.5%), Macro F1 (73.17%), Weighted F1 (73.59%), per-intent precision/recall/F1.
- **Escalation**: Accuracy (69.0%), Human Escalation Recall (50.0%), Auto-Handle F1 (77.37%).
- **Retrieval**: Mean Top-1 Cosine Similarity (0.3555), Coverage at threshold (99.5%), Intent Concordance @ 1 (42.5%).
- **LLM Judge**: 1–5 scale evaluating Relevance (4.06), Groundedness (4.67), Tone (4.14), and Escalation (4.22), Overall (4.27).

### 14. How does LLM-as-a-judge work?
In `src/evaluation/judge.py`, the judge evaluates each reply across 4 dimensions on a 1–5 scale. It runs via Gemini 1.5 Flash when an API key is present, and falls back to a deterministic rule-based rubric checking keyword overlap, absence of forbidden hallucinated phrases, empathy markers, and escalation alignment.

### 15. What is our headline metric?
**Intent Macro F1 = 0.7317 (73.17%) and Intent Accuracy = 73.50%** (outperforming the majority baseline of 20.0% and TF-IDF baseline of 51.5%).

### 16. Why is that headline metric misleading?
1. **Macro F1 treats unequal business risks equally**: High recall on general inquiries (95.5%) masks low recall on billing disputes (41.4%), where mistakes cost real money.
2. **Sample size confidence interval**: On $N=200$, the 95% confidence interval is $\pm 6.1\%$, meaning true accuracy is anywhere between 67.4% and 79.6%.
3. **Escalation accuracy (69.0%) masks a 50% blind spot**: The trivial baseline gets 68.0% escalation accuracy by *never escalating*. Our agent's actual human escalation recall is only 50.0% (detecting 32/64 high-risk cases).
4. **Judge leniency bias**: Retrieval concordance is only 42.5%, yet the judge gave 4.27/5.0 because LLMs reward polite phrasing regardless of historical exemplar mismatch.

### 17. What are the top 5 failure modes?
1. **Billing masked by hardware nouns**: e.g., "charger ripped after 11 months, need replacement" misclassified as battery/charger diagnostic instead of warranty replacement.
2. **Over-escalation on informal tweets**: Hashtags like `#thisaccessoryisnotsuppotted` drop confidence below 0.55, causing safe questions to be needlessly escalated.
3. **Hardware confounded with OS updates**: "iOS 11 update made my phone lose service" misclassified as software bug instead of carrier/SIM connectivity.
4. **Account security with indirect phrasing**: "Why is my phone suddenly asking for passwords?" missed by keyword intent, but caught by retrieval low-similarity fallback.
5. **Retrieval semantic drift on sparse queries**: 5-word tweets match superficial words rather than the underlying technical root cause.

### 18. What would we do with one additional week?
1. Fine-tune a lightweight dense embedding model (`all-MiniLM-L6-v2`) with contrastive loss on AppleSupport pairs to push retrieval concordance past 75%.
2. Add hierarchical classification (transactional verb detection before device noun parsing).
3. Implement hashtag deconstruction to recover lost confidence on informal tweets.

---

## Likely Interviewer Questions & How to Answer

### Q: "Why didn't you use LangChain, LlamaIndex, or CrewAI?"
> *"I chose not to use heavyweight agentic frameworks because they add unnecessary abstraction layers, latency overhead, and hidden failure modes. For a production customer support system, we need deterministic control over state transitions, explicit error handling, and zero external dependency risk. Writing modular Python with Pydantic and Scikit-Learn makes every stage testable, fast (<15ms latency), and easy to modify live."*

### Q: "Your escalation recall is 50%. How would you improve that in production?"
> *"Our error analysis showed that the 32 missed escalations were primarily billing inquiries where customers used device nouns (like 'charger' or 'app') without explicitly saying 'refund'. I would implement a two-stage hierarchical classifier: Stage 1 detects transactional/warranty/dispute intent from verbs, and Stage 2 classifies the device component. I would also add few-shot exemplars specifically targeting indirect billing requests."*

### Q: "Why did you use TF-IDF instead of OpenAI Ada or HuggingFace embeddings?"
> *"In device support, specific technical tokens like 'iOS 11.0.2', '2FA', 'SIM card', or 'HomeKit' carry critical discriminative signal. Off-the-shelf dense embeddings often compress these into generic device vectors. TF-IDF with sublinear term-frequency gives exact keyword matching, requires zero external model download, indexes 3,500 documents in 200 milliseconds, and ensures anyone evaluating the repo can reproduce results without API dependencies."*

### Q: "How would you add a new intent class live during this interview?"
> *"It requires 3 simple steps:
> 1. Add the intent name and keyword signatures to `INTENTS` and `INTENT_DEFINITIONS` in `src/intent/taxonomy.py`.
> 2. Add any specific contextual boost rules in `src/intent/classifier.py`.
> 3. Add the intent's risk tier and default routing in `src/escalation/policy.py`.
> All unit tests in `tests/test_intent.py` and the evaluation harness will automatically pick up the new intent from `INTENTS`."*
