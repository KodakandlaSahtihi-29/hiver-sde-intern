# Golden Set Human Review Guide (200 Examples)

This guide walks you through reviewing and verifying the **200 candidate examples** in `data/golden/review_queue.csv` to create the final hand-labelled golden evaluation set for the Hiver SDE Intern take-home assignment.

> [!NOTE]
> **Engineering Disclaimer**: The intent categories, definitions, and escalation criteria in this guide represent this project's engineering annotation standards and evaluation rubric, **NOT official corporate policies of Apple Inc.**

---

## 1. File Location & Column Structure

Open **`data/golden/review_queue.csv`** in Microsoft Excel, Google Sheets, or VS Code.

The file contains 200 rows of real Twitter customer interactions with `@AppleSupport`:

| Column | Description | Reviewer Action |
| :--- | :--- | :--- |
| `example_id` | Unique identifier (`gold_001` - `gold_200`) | **Do not change** |
| `conversation_id` | Raw Twitter dialogue ID | **Do not change** |
| `customer_message` | Real user tweet sent to Apple Support | **Do not change** (read for intent) |
| `historical_reply` | Historical response from `@AppleSupport` | **Do not change** (use as context) |
| `proposed_intent` | Heuristic machine suggestion | **Do not change** (reference only) |
| `proposed_decision` | Heuristic machine suggestion | **Do not change** (reference only) |
| **`final_intent`** | **Your human-verified intent** | **Fill with 1 of the 6 valid intents** |
| **`final_decision`** | **Your human-verified decision** | **Fill with `AUTO_HANDLE` or `ESCALATE_TO_HUMAN`** |
| **`human_verified`** | **Verification flag** | **Change from `False` to `True`** |
| `reviewer_notes` | Optional notes | Optional (rationale for overrides or edge cases) |

---

## 2. The 6 Valid Intent Categories

Every row's `final_intent` must be exactly one of these 6 categories:

1. **`Software_Bug_OS_Update`**
   - **Covers**: iOS update bugs, app crashes, screen freeze after update, reboot loops, iOS beta program glitches, Touch ID/Face ID software lag.
   - *Example*: `"ios11 was forced onto my iphone 6... It's broken my apps & phone call abilities!"`

2. **`Device_Performance_Battery`**
   - **Covers**: Rapid battery drain, phone overheating/running hot, device slowing down, slow charging, battery percentage jumping.
   - *Example*: `"@AppleSupport we have to talk about ios 11, I want my batery back again!"`

3. **`Connectivity_Hardware`**
   - **Covers**: Wi-Fi dropouts, Bluetooth pairing failure, cellular data / 'No SIM' errors, physical screen damage, broken speaker/microphone, damaged charging port, accessory compatibility alerts.
   - *Example*: `"Ever since i updated my iPhone 7 Plus to iOS 11 my speaker for phone calls won't work"`

4. **`General_Product_Inquiry`**
   - **Covers**: Device specifications, compatibility (e.g. HomeKit, Apple Watch with carriers), release dates, feature how-tos, iOS settings questions.
   - *Example*: `"Does the Apple Watch Series 3 support cellular in Canada?"`

5. **`Account_Access_Security`**
   - **Covers**: Locked Apple ID, two-factor authentication (2FA) SMS codes, password resets, compromised/hacked iCloud, suspicious credential prompts, phishing tweets.
   - *Example*: `"My icloud account has been locked for security reasons. Even my Apple ID is locked."`

6. **`Billing_Subscriptions`**
   - **Covers**: Unrecognized App Store charges, iTunes subscription cancellations, duplicate purchase refunds, warranty replacement claims for purchased accessories.
   - *Example*: `"I was charged $9.99 for an app I deleted within 5 minutes. Need a refund."`

---

## 3. How to Resolve Ambiguous & Boundary Cases

When customer tweets mention multiple symptoms, use the following disambiguation rules:

| Ambiguity / Overlap | Disambiguation Guideline | Selected Intent |
| :--- | :--- | :--- |
| **Battery drain after an iOS update**<br>*(e.g., "Updated to iOS 11 and battery drops 30% in 10 mins")* | If the customer's *primary complaint* is battery drain or device heat, choose Battery. If they list multiple general bugs (apps crashing + lag + reboot) and battery is just one bullet, choose OS Update. | `Device_Performance_Battery` (if battery is core issue)<br>`Software_Bug_OS_Update` (if general update bug complaint) |
| **Hardware failure triggered by an update**<br>*(e.g., "Updated to iOS 11 and my speaker/mic stopped working")* | Customers often attribute hardware discovery to an update. If a physical component (speaker, camera, mic, screen, Wi-Fi antenna) has failed, prioritize Hardware. | `Connectivity_Hardware` |
| **Damaged accessory under warranty**<br>*(e.g., "My lightning cable ripped, can I get a replacement under 1-year warranty?")* | Even though "cable" is hardware, the customer's intent is warranty adjudication / financial replacement. Route to Billing/Subscriptions. | `Billing_Subscriptions` |
| **Accessory connection error**<br>*(e.g., "iPhone says 'accessory not supported' when plugged into charger")* | If the customer is trying to make an accessory work through troubleshooting, prioritize Hardware/Connectivity. | `Connectivity_Hardware` |
| **Suspicious password prompt**<br>*(e.g., "Phone keeps asking me to verify password for every app")* | Credential prompts pose security/phishing risks. Prioritize Security over general inquiry. | `Account_Access_Security` |
| **Feature questions vs How-to troubleshooting**<br>*(e.g., "Can I link my smart bulbs to HomeKit?")* | Pre-purchase or capability questions belong in General Product Inquiry. | `General_Product_Inquiry` |

---

## 4. Valid Escalation Decisions & Decision Rules

Every row's `final_decision` must be either **`AUTO_HANDLE`** or **`ESCALATE_TO_HUMAN`**.

### When to choose `AUTO_HANDLE`:
- The issue is a standard software bug, general performance optimization, Wi-Fi network reset, or product spec question.
- The agent can safely resolve the inquiry publicly using known troubleshooting steps or official Apple Support knowledge base articles (e.g. `support.apple.com`).
- No private personal data, passwords, financial transactions, or physical inspections are required.

### When to choose `ESCALATE_TO_HUMAN`:
- **Mandatory Escalation 1 (Account Security)**: Any inquiry involving Apple ID lockouts, password resets, 2FA recovery, or compromised accounts (`Account_Access_Security`). Automated systems must never handle credential modifications.
- **Mandatory Escalation 2 (Billing & Transactions)**: Any payment dispute, subscription cancellation, refund request, or warranty purchase claim (`Billing_Subscriptions`). Requires transactional authorization.
- **Mandatory Escalation 3 (Physical Damage)**: Cracked glass, liquid damage, swollen batteries, or destroyed ports (`Connectivity_Hardware`). Cannot be fixed with settings; requires Genius Bar / repair appointment.
- **Mandatory Escalation 4 (High Distress / Ambiguity)**: Customer expressing security alarm, identity theft, or complex multi-device failure requiring human specialist review.

---

## 5. Easiest Review Workflow in Excel / Google Sheets

1. **Open** `data/golden/review_queue.csv` in **Microsoft Excel**, **Google Sheets**, or **VS Code**.
2. **Reviewing rows**:
   - Read `customer_message` (Col C) and `historical_reply` (Col D).
   - Check `proposed_intent` (Col E) and `proposed_decision` (Col F).
   - **If you agree with the machine proposal**:
     - Copy Col E into `final_intent` (Col G).
     - Copy Col F into `final_decision` (Col H).
     - Set `human_verified` (Col I) to **`True`**.
     *(Tip in Excel: Select columns E & F for matching rows, copy into G & H, and drag `True` down column I)*.
   - **If you disagree with the machine proposal**:
     - Type the correct intent into `final_intent` (Col G) from the 6 valid options.
     - Type the correct decision into `final_decision` (Col H) (`AUTO_HANDLE` or `ESCALATE_TO_HUMAN`).
     - Set `human_verified` (Col I) to **`True`**.
     - *(Optional)* Add a brief reason in `reviewer_notes` (Col J), e.g., `"Update broke speaker - hardware issue"`.
3. **Save**:
   - Save the file as standard **CSV (Comma Delimited) (*.csv)** with UTF-8 encoding back to:
     `data/golden/review_queue.csv`

---

## 6. Terminal Alternative (Interactive CLI)

If you prefer reviewing directly in the terminal without opening a spreadsheet:

```powershell
python scripts/review_golden_set.py --interactive
```

- **`[Enter]`**: Accepts the proposed intent and decision and marks verified.
- **`i <1-6>`**: Changes intent (1:Account, 2:Billing, 3:Battery, 4:Hardware, 5:Bug, 6:General).
- **`d <1-2>`**: Changes decision (1:AUTO_HANDLE, 2:ESCALATE_TO_HUMAN).
- **`s`**: Skips the row without verifying.
- **`q`**: Saves progress and exits.

---

## 7. Exact Commands to Run After You Finish Reviewing

Once you have reviewed the 200 rows and saved `review_queue.csv`:

```powershell
# 1. Import your verified CSV into golden_set.jsonl
python scripts/review_golden_set.py --import-csv data/golden/review_queue.csv

# 2. Programmatically validate golden set integrity & 0% data leakage
python scripts/validate_golden_set.py

# 3. Run evaluation across Baselines and Agent
python scripts/evaluate.py

# 4. Extract top empirical failure modes
python scripts/extract_failures.py

# 5. Run all unit tests
pytest tests/ -v
```
