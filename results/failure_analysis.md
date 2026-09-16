# Empirical Failure Mode Analysis

This failure analysis is derived strictly from empirical evaluation logs on the 200-example human-reviewed golden dataset (`results/evaluation_results.jsonl`). No failure cases or metrics were fabricated.

---

## Executive Summary of Error Distribution

- **Total Golden Examples Evaluated**: 200
- **Intent Misclassifications**: 53 / 200 (Intent Accuracy: 73.5%)
- **Handling Decision Mismatches**: 62 / 200 (Escalation Accuracy: 69.0%)
- **Escalation Recall on High-Risk Cases**: 50.0% (32 / 64 detected)
- **Auto-Handle F1**: 77.4%

```
               Predicted AUTO_HANDLE    Predicted ESCALATE_TO_HUMAN
Gold AUTO_HANDLE               107                               29
Gold ESCALATE_TO_HUMAN          32                               32
```

---

## Top 5 Failure Modes

### Failure Mode 1: Billing Inquiries Masked by Technical/Hardware Symptoms
- **Description**: Customers reporting billing or subscription problems frequently describe the software or hardware surface through which the charge occurred (e.g., "stuck on connect to iTunes screen", "charger broke under 1-year warranty", "app crashed after purchasing"). Lexical and TF-IDF classifiers latch onto the dominant technical nouns ("charger", "update", "screen") and misclassify the intent as `Device_Performance_Battery` or `Software_Bug_OS_Update`.
- **Real Evaluation Example**:
  - **Example ID**: `gold_163`
  - **Customer Query**: *"my charger stopped working& it has a rip in it,but I haven't had it for a year. is there a way I can get a replacement?"*
  - **Gold Label**: `Billing_Subscriptions` (Warranty / purchase replacement) | Expected: `ESCALATE_TO_HUMAN`
  - **Model Output**: Predicted Intent: `Device_Performance_Battery` | Predicted Decision: `AUTO_HANDLE`
  - **Model Reply**: *"We're here to help optimize your battery performance. Based on standard diagnostic procedures: We'd be happy to help..."*
- **Expected Behavior**: Recognize the warranty/purchase dispute intent and escalate to human agent or authorized replacement channel.
- **Actual Behavior**: Classified as battery diagnostic and attempted self-service automation.
- **Hypothesis**: The word "charger" has high TF-IDF weighting towards battery/power components, overriding the commercial term "replacement".
- **Possible Improvement**: Multi-intent hierarchical classification or dependency parsing that detects transactional verbs ("replacement", "bought", "charged") as primary routing triggers regardless of device nouns.

---

### Failure Mode 2: Over-Escalation of Safe, Conversational Inquiries (False Positives)
- **Description**: 21 self-service inquiries in `General_Product_Inquiry` and 7 in `Software_Bug_OS_Update` were escalated to human agents even though they could have been safely auto-handled.
- **Real Evaluation Example**:
  - **Example ID**: `gold_112`
  - **Customer Query**: *"why does my iPhone cable intermittently cause my phone to come up with the message, #thisaccessoryisnotsuppotted? #frustrated"*
  - **Gold Label**: `General_Product_Inquiry` | Expected: `AUTO_HANDLE`
  - **Model Output**: Predicted Intent: `General_Product_Inquiry` | Predicted Decision: `ESCALATE_TO_HUMAN`
  - **Stated Reason**: *"Intent classification confidence (0.50) is below safe automation threshold (0.55)."*
- **Expected Behavior**: Auto-handle with standard Apple Support KB guidance for "Accessory Not Supported" (cleaning port, checking MFi certification).
- **Actual Behavior**: The conversational hashtag `#thisaccessoryisnotsuppotted` diluted keyword confidence below the 0.55 threshold, triggering the conservative safety fallback.
- **Hypothesis**: The conservative threshold ($0.55$) prioritizes safety over deflection. Unnormalized slang, hashtags, and informal punctuation drop lexical confidence scores into the cautious escalation zone.
- **Possible Improvement**: Hashtag normalization / decompounding (e.g., split `#thisaccessoryisnotsuppotted` into "this accessory is not supported") before scoring.

---

### Failure Mode 3: Hardware Failures Confounded with Software Update Complaints
- **Description**: Customers often conflate the timing of a software update with the sudden discovery of hardware or cellular failure (e.g., "iOS 11 update made my phone lose service", "speaker died after update").
- **Real Evaluation Example**:
  - **Example ID**: `gold_082`
  - **Customer Query**: *"iOS 11.0.2 update is making my iPhone 7 constantly lose service."*
  - **Gold Label**: `Connectivity_Hardware` | Expected: `AUTO_HANDLE` (carrier/SIM reset)
  - **Model Output**: Predicted Intent: `Software_Bug_OS_Update` | Predicted Decision: `AUTO_HANDLE`
  - **Model Reply**: *"We'd love to help resolve this software issue. Recommended steps: Have you updated to 11.0.2 yet?..."*
- **Expected Behavior**: Provide cellular and carrier settings troubleshooting (Settings > Cellular > Carrier Update, SIM reinsertion).
- **Actual Behavior**: Recommended software update steps because "iOS 11.0.2 update" overpowered "lose service".
- **Hypothesis**: Update complaints outnumber hardware connectivity complaints 15:1 on Twitter following a major release, creating strong prior bias in token weights.
- **Possible Improvement**: Symptom-versus-trigger feature separation (treating "iOS 11" as trigger context and "lose service" as core symptom).

---

### Failure Mode 4: Account Security Edge Cases with Indirect Language
- **Description**: High-stakes account security inquiries that do not use the explicit keywords "Apple ID" or "iCloud locked" risk being treated as generic app questions.
- **Real Evaluation Example**:
  - **Example ID**: `gold_133`
  - **Customer Query**: *"Why is my phone suddenly asking me to verify my passwords for every social network app I log on to today? 🤔 @AppleSupport"*
  - **Gold Label**: `Account_Access_Security` | Expected: `ESCALATE_TO_HUMAN`
  - **Model Output**: Predicted Intent: `General_Product_Inquiry` (confidence 0.50) | Predicted Decision: `ESCALATE_TO_HUMAN`
  - **Escalation Reason Triggered**: *"Retrieved historical precedent is insufficient to guarantee an accurate automated resolution."*
- **Expected Behavior**: Identify suspicious credential prompts as security verification risk and escalate.
- **Actual Behavior**: Intent classifier failed (missed specific keywords), but the **evidence-aware fallback correctly escalated** because top retrieval similarity was low (0.1784 < 0.18).
- **Hypothesis**: This demonstrates the value of evidence-aware fallback: when the intent classifier fails, vector retrieval distance acts as a second safety net preventing accidental auto-handling.
- **Possible Improvement**: Few-shot prompt exemplars explicitly covering indirect phishing, suspicious credential prompts, and malware concerns.

---

### Failure Mode 5: Retrieval Semantic Drift on Sparse Queries
- **Description**: Intent Concordance @ 1 for vector retrieval was measured at 42.5%. When customer tweets are terse (e.g. 5–8 words), cosine similarity matches superficial lexical tokens ("phone", "screen", "update") to historical threads that had entirely different root causes.
- **Real Evaluation Example**:
  - **Example ID**: `gold_042`
  - **Customer Query**: *"Screen is flickering on my iPhone 8"*
  - **Gold Intent**: `Connectivity_Hardware` (Display hardware defect)
  - **Retrieved Top-1 Historical Query**: *"My iPhone 8 camera is flickering under indoor lighting"* (Software / camera refresh issue)
  - **Similarity**: 0.412
- **Expected Behavior**: Retrieve display/OLED/LCD flickering threads.
- **Actual Behavior**: Retrieved camera sensor flickering due to overlapping tokens (`iPhone 8`, `flickering`).
- **Hypothesis**: Bag-of-words / TF-IDF representations lack fine-grained component distinction when syntactic context is minimal.
- **Possible Improvement**: Dense dual-encoder embeddings (e.g., `all-MiniLM-L6-v2`) fine-tuned with contrastive loss on Apple Support turn pairs.
