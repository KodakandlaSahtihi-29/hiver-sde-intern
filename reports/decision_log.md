# Architectural & Engineering Decision Log

This log documents 12 non-obvious architectural, algorithmic, and evaluation decisions made during the design and implementation of the `@AppleSupport` AI Support System.

---

### Decision 1: Focus Brand Selection — `@AppleSupport` over `@AmazonHelp`
- **Decision**: Select `@AppleSupport` from the *Customer Support on Twitter* dataset as our sole operational domain.
- **Why**: Inspection revealed `@AmazonHelp` is heavily multilingual (mixing Spanish, German, Japanese, Portuguese, and English within single author streams), introducing cross-lingual confounding. `@AppleSupport` is overwhelmingly English, has high conversational density (76,639 threads in the full dataset), and features distinct boundaries between self-service technical guidance and high-stakes identity/security lockouts.
- **Alternative Considered**: `@AmazonHelp` or `@Delta`.
- **Why Alternative Was Not Selected**: Multi-language processing in `@AmazonHelp` would divert engineering effort from intent taxonomy depth, retrieval precision, and safety escalation into multilingual translation pipelines.

---

### Decision 2: Empirical Intent Taxonomy of 6 Categories
- **Decision**: Define a 6-intent taxonomy grounded directly in `@AppleSupport` threads (`Account_Access_Security`, `Device_Performance_Battery`, `Software_Bug_OS_Update`, `Connectivity_Hardware`, `Billing_Subscriptions`, `General_Product_Inquiry`).
- **Why**: Generic e-commerce categories (e.g., "Shipping", "Delivery", "Return") do not match consumer tech support. Six categories offer optimal granularity: sufficiently granular to isolate high-risk actions (passwords, billing) while avoiding micro-classes with insufficient training sample density.
- **Alternative Considered**: A 3-class system ("Technical", "Account", "Other") or a 15-class fine-grained system (e.g., separating "Wi-Fi" from "Bluetooth", "Battery Drain" from "Overheating").
- **Why Alternative Was Not Selected**: 3 classes is too coarse to route actionable solutions; 15 classes causes severe semantic overlap and drops classification macro-F1 due to subjective class boundaries.

---

### Decision 3: Stratified Golden Candidate Sampling from Held-Out Offset
- **Decision**: Strictly partition the dataset by index offset, allocating the first 3,500 conversations exclusively to the retrieval knowledge base and sampling candidates for the golden set only from the held-out tail (rows 3,501 to 4,953).
- **Why**: Completely isolates the candidate pool from the knowledge base, ensuring test conversations cannot be indexed.
- **Alternative Considered**: Uniform random split across the entire dataset.
- **Why Alternative Was Not Selected**: In Twitter customer care, customers frequently tweet multiple times about the same incident. A naive random split risks splitting multi-tweet threads between train and test sets, causing semantic data leakage.

---

### Decision 4: Automated Pre-Index Leakage Audit
- **Decision**: Implement an automated validation step in `scripts/validate_golden_set.py` that verifies 0% overlap between golden set conversation IDs/query text hashes and the vector index before any evaluation runs.
- **Why**: Data leakage is the most prevalent flaw in RAG evaluations, leading to artificially inflated retrieval metrics.
- **Alternative Considered**: Manual inspection of random sample IDs.
- **Why Alternative Was Not Selected**: Manual audits are prone to human oversight; programmatic hash-intersection guarantees mathematical proof of isolation.

---

### Decision 5: Lightweight TF-IDF + Sublinear TF Retrieval over Dense Neural Embeddings
- **Decision**: Build the retrieval engine using TF-IDF with sublinear term-frequency scaling and character/word n-grams $(1, 2)$ rather than loading an un-fine-tuned heavy transformer (e.g., BERT/Sentence-Transformers).
- **Why**: In device support, exact technical terminology matters immensely (e.g., "iOS 11.0.2", "Apple ID", "2FA", "No SIM", "HomeKit"). General-purpose sentence embeddings frequently compress these critical tokens into generic "technology" embeddings. TF-IDF provides deterministic indexing, runs in $< 500$ ms with zero GPU requirements, and operates with zero dependency bloat.
- **Alternative Considered**: `sentence-transformers/all-MiniLM-L6-v2` or FAISS with dense embeddings.
- **Why Alternative Was Not Selected**: Required downloading 100MB+ models, increased container/runtime complexity, and proved less sensitive to exact Apple error codes in sparse customer tweets without task-specific fine-tuning.

---

### Decision 6: Retrieval Top-$K$ Set to 3
- **Decision**: Retrieve exactly $K=3$ historical conversation exemplars for evidence assessment and generation context.
- **Why**: Twitter customer care replies are short (mean: 25–35 words). Three relevant exemplars provide sufficient stylistic diversity (e.g., direct troubleshooting step vs. link to Apple KB article) without flooding the prompt context with noise.
- **Alternative Considered**: $K=1$ or $K=10$.
- **Why Alternative Was Not Selected**: $K=1$ is brittle to irrelevant outliers; $K=10$ exceeds the optimal signal-to-noise ratio for short Twitter dialogues and increases retrieval latency.

---

### Decision 7: Evidence-Aware Multi-Stage Escalation Architecture
- **Decision**: Decouple the escalation decision from the intent classifier into an explicit 5-stage pipeline: `Message -> Intent -> Retrieval -> Evidence Sufficiency Scorer -> Reply Generation -> Escalation Policy`.
- **Why**: Intent alone does not determine whether an inquiry can be auto-handled. A `Connectivity_Hardware` inquiry can be auto-handled if it is a Wi-Fi setting reset, but MUST be escalated if the screen is physically shattered or if retrieved evidence is insufficient.
- **Alternative Considered**: Direct end-to-end classification where a single classifier outputs `{intent, decision}` simultaneously.
- **Why Alternative Was Not Selected**: Single-stage classifiers cannot incorporate runtime evidence retrieval quality into the escalation decision.

---

### Decision 8: Conservative Escalation Bias (Prioritizing Safety over Deflection)
- **Decision**: Configure the escalation policy to prioritize safety over automated deflection (e.g., escalating whenever intent confidence $< 0.55$, evidence similarity $< 0.18$, or query is vague).
- **Why**: In consumer tech support, the cost of a false auto-handle on an account security lockout or billing dispute is catastrophic (user frustration, potential privacy breach). Conversely, the cost of an unnecessary escalation on an ambiguous inquiry is minor (routed to a human specialist).
- **Alternative Considered**: Maximizing deflection rate by forcing auto-handling on all non-security queries.
- **Why Alternative Was Not Selected**: Aggressive deflection leads to hallucinated answers and poor customer experience when evidence is weak.

---

### Decision 9: Two-Stage Golden Set Workflow (`create_candidates` + `validate_golden_set`)
- **Decision**: Separate golden set generation into candidate extraction from real threads, followed by human verification and programmatic validation.
- **Why**: Pure synthetic generation creates unrealistic customer tweets. Extracting candidates directly from real `@AppleSupport` threads preserves natural user phrasing, typos, frustration markers, and emojis.
- **Alternative Considered**: Generating 200 synthetic evaluation questions using an LLM prompt.
- **Why Alternative Was Not Selected**: Synthetic prompts fail to represent the messiness, terse language, and contextual ambiguity of real Twitter support interactions.

---

### Decision 10: Defensible Retrieval Evaluation Metrics
- **Decision**: Measure retrieval quality using **Intent Concordance @ 1** (43.5%) and **Cosine Similarity Distributions** (mean: 0.3578, coverage: 99.5%) rather than fabricating synthetic "Precision@3" relevance labels.
- **Why**: Precision@3 requires binary relevance judgments for every retrieved document across all 200 queries ($200 \times 3 = 600$ manual judgments). Generating synthetic relevance tags would be dishonest. Intent Concordance provides an objective, defensible measure of whether retrieval stays within the customer's problem domain.
- **Alternative Considered**: LLM-generated binary relevance labels for every retrieved document.
- **Why Alternative Was Not Selected**: Subject to LLM judge hallucination and circular evaluation bias.

---

### Decision 11: Two Distinct Empirical Baselines
- **Decision**: Benchmark against both a **Trivial Baseline** (Majority-Class Predictor) and a **Simple ML Baseline** (TF-IDF + Logistic Regression).
- **Why**: A majority-class baseline sets the absolute floor (22.0% accuracy), exposing class imbalance. A TF-IDF Logistic Regression baseline represents standard pre-LLM production classification (52.5% accuracy, 0.3886 Macro F1), demonstrating the clear value added by our structured agent (68.0% accuracy, 0.6246 Macro F1).
- **Alternative Considered**: Random guessing baseline.
- **Why Alternative Was Not Selected**: Random guessing is weaker and less informative than majority class; Hiver explicitly requested a trivial baseline and a simple ML baseline.

---

### Decision 12: Dual-Mode LLM-as-a-Judge Implementation
- **Decision**: Implement the reply quality judge with a deterministic rule-anchored rubric that seamlessly executes via Google Gemini API if `GEMINI_API_KEY` is present, while remaining 100% runnable offline.
- **Why**: Take-home evaluators often test repositories in air-gapped or keyless environments. The project must never crash due to missing API keys while still delivering rigorous evaluation across Relevance, Groundedness, Tone, and Escalation.
- **Alternative Considered**: Requiring a live paid API key to run `evaluate.py`.
- **Why Alternative Was Not Selected**: Would fail the requirement for immediate $<15$-minute reproducibility for any evaluator without pre-configured API credentials.
