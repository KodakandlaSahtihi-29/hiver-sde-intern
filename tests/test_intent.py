"""Unit tests for intent classification and taxonomy consistency.
"""

import pytest
from src.intent.classifier import IntentClassifier
from src.intent.taxonomy import INTENTS


def test_intent_classifier_labels():
    clf = IntentClassifier()
    test_queries = [
        "My Apple ID is locked and I cannot reset my password.",
        "The battery on my iPhone 8 is draining in 2 hours.",
        "After updating to iOS 11 my phone keeps crashing.",
        "My SIM card is not detected on my device.",
        "I was charged twice on my credit card for iTunes subscription.",
        "Will the Apple HomeKit work with Philips Hue lamps?"
    ]
    for q in test_queries:
        intent, conf = clf.classify(q)
        assert intent in INTENTS
        assert 0.0 <= conf <= 1.0


def test_intent_specific_classifications():
    clf = IntentClassifier()

    intent1, conf1 = clf.classify("My Apple ID is locked and 2FA code is not working")
    assert intent1 == "Account_Access_Security"
    assert conf1 >= 0.70

    intent2, conf2 = clf.classify("My iPhone battery dies so fast after the update")
    assert intent2 == "Device_Performance_Battery"

    intent3, conf3 = clf.classify("I was charged 15 dollars for an app subscription, I want a refund")
    assert intent3 == "Billing_Subscriptions"
    assert conf3 >= 0.70
