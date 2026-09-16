"""Intent taxonomy grounded in empirical analysis of @AppleSupport customer interactions.
Defines definitions, keyword signatures, boundary cases, and risk tiers.
"""

from typing import Dict, List, Any


INTENTS: List[str] = [
    "Account_Access_Security",
    "Device_Performance_Battery",
    "Software_Bug_OS_Update",
    "Connectivity_Hardware",
    "Billing_Subscriptions",
    "General_Product_Inquiry"
]

INTENT_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "Account_Access_Security": {
        "definition": (
            "Issues regarding Apple ID credentials, locked iCloud accounts, two-factor authentication "
            "codes, password resets, unauthorized account access, or security lockouts."
        ),
        "examples": [
            "My icloud account has been locked for security reasons. Even my Apple ID is locked.",
            "Can't get verification code sent to my trusted number because my phone is dead.",
            "Forgot my Apple ID password and security questions aren't working."
        ],
        "keywords": [
            "apple id", "icloud", "locked", "password", "verification code", "2fa",
            "security reasons", "unlock", "two-factor", "trusted number", "passcode"
        ],
        "risk_level": "HIGH",
        "default_decision": "ESCALATE_TO_HUMAN",
        "escalation_reason": "Account access and identity verification require human agent review or secure verification link."
    },
    "Device_Performance_Battery": {
        "definition": (
            "Reports of abnormal battery drain, sudden device shutdowns, overheating, charging port/cable "
            "failures, or system sluggishness following battery degradation."
        ),
        "examples": [
            "This update is also killing my battery, losing 30% in 15 minutes.",
            "My iPhone 7 gets burning hot while charging and turns off at 20%.",
            "Battery health shows service but phone is only 8 months old."
        ],
        "keywords": [
            "battery", "battery drain", "overheating", "hot", "charging", "charger",
            "drain", "shut down", "dies", "battery health", "sluggish", "slow"
        ],
        "risk_level": "LOW",
        "default_decision": "AUTO_HANDLE",
        "escalation_reason": "Standard battery troubleshooting and diagnostics steps can be auto-guided unless physical swelling occurs."
    },
    "Software_Bug_OS_Update": {
        "definition": (
            "Bugs, crashes, glitches, or errors after installing an iOS/macOS update, app crashes, "
            "UI freezing, audio/camera software bugs, or installation failure."
        ),
        "examples": [
            "Anyone else getting the voice control bug on ios10? It's driving me insane!",
            "How do I delete apps if this is what shows when I press and hold an app?",
            "iOS 11 update bricked my phone, screen is stuck on apple logo."
        ],
        "keywords": [
            "ios", "update", "bug", "crash", "glitch", "freeze", "stuck", "apple logo",
            "screen frozen", "keyboard lag", "app crash", "software update", "version"
        ],
        "risk_level": "LOW",
        "default_decision": "AUTO_HANDLE",
        "escalation_reason": "Software troubleshooting, force restarts, and update guidance can be auto-handled unless device is unrecoverable."
    },
    "Connectivity_Hardware": {
        "definition": (
            "Hardware failures or wireless connectivity problems including SIM card recognition, "
            "Wi-Fi/Bluetooth disconnections, broken screen/camera lens, speaker/mic defects."
        ),
        "examples": [
            "Today I started getting a 'No Sim Card Installed' message on my iPhone 6.",
            "Unable to connect to home Wi-Fi after restarting the router.",
            "Dropped my phone, screen is cracked and touch is unresponsive."
        ],
        "keywords": [
            "no sim", "sim card", "wifi", "wi-fi", "bluetooth", "cellular", "no service",
            "cracked screen", "microphone", "speaker", "hardware", "broken screen"
        ],
        "risk_level": "MEDIUM",
        "default_decision": "AUTO_HANDLE",
        "escalation_reason": "Network reset steps can be auto-handled; physical damage requires repair booking escalation."
    },
    "Billing_Subscriptions": {
        "definition": (
            "Charges on bank statement/credit card from Apple, disputed App Store purchases, "
            "subscription cancellations, refund requests, or family sharing billing."
        ),
        "examples": [
            "I was charged $9.99 for an app I deleted within 5 minutes. Need a refund.",
            "How do I cancel my Apple Music trial before it renews?",
            "Unauthorized purchase on my credit card from iTunes."
        ],
        "keywords": [
            "charged", "charge", "refund", "subscription", "bill", "billing", "receipt",
            "apple music", "itunes", "in-app purchase", "payment", "cancel subscription"
        ],
        "risk_level": "HIGH",
        "default_decision": "ESCALATE_TO_HUMAN",
        "escalation_reason": "Financial disputes, unauthorized charges, and refund requests require verified account lookup."
    },
    "General_Product_Inquiry": {
        "definition": (
            "General questions regarding product compatibility, specifications, upcoming features, "
            "store availability, trade-in value, or accessory support."
        ),
        "examples": [
            "Is it possible to link my Hive lights/hub to Apple HomeKit?",
            "Will there be an Apple battery case for the iPhone X eventually?",
            "Does the Apple Watch Series 3 work without an iPhone nearby?"
        ],
        "keywords": [
            "compatible", "compatibility", "homekit", "release", "when will", "specs",
            "trade-in", "accessory", "case", "difference between", "how do i use"
        ],
        "risk_level": "LOW",
        "default_decision": "AUTO_HANDLE",
        "escalation_reason": "Product specs and feature compatibility are publicly documented knowledge suitable for auto-handling."
    }
}
