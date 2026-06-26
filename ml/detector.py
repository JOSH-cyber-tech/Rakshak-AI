"""
MODULE 1 — Real-Time Scam Detection Engine.

Hybrid: TF-IDF + Logistic Regression baseline, combined with a deterministic
rule-based override layer for high-risk patterns. Supports Hinglish/Hindi/English
via char + word n-grams (robust to transliteration and obfuscation).
"""
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

from data.synth import generate_messages

# ---------------------------------------------------------------------------
# RULE LAYER — high-precision override signals
# ---------------------------------------------------------------------------
HIGH_RISK_PATTERNS = {
    "authority_impersonation": [
        r"\bcbi\b", r"\bed\b", r"enforcement directorate", r"\bcustoms\b",
        r"narcotics", r"police\s*(case|arrest)", r"arrest\s*warrant", r"digital\s*arrest",
        r"money\s*laundering",
    ],
    "credential_request": [
        r"\botp\b", r"\bcvv\b", r"\bpin\b", r"\bupi\s*pin\b", r"share.*(otp|pin|cvv)",
        r"kyc.*(update|pending|expire)",
    ],
    "urgency_coercion": [
        r"immediately", r"turant", r"abhi", r"urgent", r"do not (disconnect|tell|cut)",
        r"within \d+ (hour|minute|hr|min)", r"warna", r"otherwise.*block",
    ],
    "money_demand": [
        r"send money", r"paise\s*(bhej|transfer)", r"transfer.*now", r"pay.*fee",
        r"processing fee", r"settlement", r"safe (rbi|bank) account",
    ],
    "reward_bait": [
        r"lottery", r"kbc", r"won \d+", r"cashback", r"double.*(scheme|profit|24)",
        r"guaranteed.*(profit|return)",
    ],
}

ACTION_BY_LEVEL = {
    "FRAUD": "Block sender, do NOT share any code/money, report at cybercrime.gov.in / 1930.",
    "SUSPICIOUS": "Do not act on this message. Verify via the official app or helpline before responding.",
    "SAFE": "No action needed. Stay alert for follow-up messages.",
}


# Phrases that indicate a LEGITIMATE informational message rather than a request.
# e.g. a real bank tells you your OTP and warns you NOT to share it.
BENIGN_CONTEXT = [
    r"do not share (it|this|your otp)", r"never share", r"will never ask",
    r"otp (is|for).*\d{4,}", r"debited from a/c", r"credited to your",
    r"- ?(hdfc|icici|sbi|axis|kotak|bank)", r"not you\??\s*call",
]

def _rule_signals(text):
    t = text.lower()
    hits = {}
    for cat, pats in HIGH_RISK_PATTERNS.items():
        matched = [p for p in pats if re.search(p, t)]
        if matched:
            hits[cat] = len(matched)
    # Benign guard: if the message looks like a legit informational bank SMS,
    # a lone credential mention is NOT a request -> drop that single signal.
    benign = any(re.search(p, t) for p in BENIGN_CONTEXT)
    if benign and set(hits.keys()) <= {"credential_request"}:
        hits.pop("credential_request", None)
    return hits


class ScamDetector:
    def __init__(self):
        self.pipe = None
        self._train()

    def _train(self):
        rows = generate_messages()
        X = [r[0] for r in rows]
        y = [r[1] for r in rows]
        features = FeatureUnion([
            ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2)),
        ])
        self.pipe = Pipeline([
            ("feat", features),
            ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
        ])
        self.pipe.fit(X, y)
        self.classes_ = list(self.pipe.named_steps["clf"].classes_)

    def predict(self, text):
        text = (text or "").strip()
        if not text:
            return self._format("SAFE", 0.0, "Empty message.", [], {})

        proba = self.pipe.predict_proba([text])[0]
        pmap = dict(zip(self.classes_, proba))
        ml_fraud = float(pmap.get("FRAUD", 0.0))

        rules = _rule_signals(text)
        rule_categories = len(rules)
        rule_weight = sum(rules.values())

        # Fusion: ML score boosted by rule evidence.
        score = ml_fraud
        if rule_categories >= 2:
            score = max(score, 0.85)        # multiple independent risk signals -> override
        elif rule_categories == 1:
            score = max(score, 0.55)
        score = min(1.0, score + 0.05 * rule_weight)

        # Critical combo: authority impersonation + (money OR credential) = digital arrest
        if "authority_impersonation" in rules and (
            "money_demand" in rules or "credential_request" in rules
        ):
            score = max(score, 0.95)

        if score >= 0.7:
            level = "FRAUD"
        elif score >= 0.4:
            level = "SUSPICIOUS"
        else:
            level = "SAFE"

        signals = self._build_signals(rules)
        reason = self._build_reason(level, rules, ml_fraud)
        return self._format(level, round(score, 3), reason, signals, rules)

    def _build_signals(self, rules):
        label = {
            "authority_impersonation": "Impersonates law-enforcement / govt authority",
            "credential_request": "Requests OTP/PIN/CVV/KYC credentials",
            "urgency_coercion": "Creates artificial urgency / coercion",
            "money_demand": "Demands money transfer",
            "reward_bait": "Offers unrealistic reward / lottery / returns",
        }
        return [label[k] for k in rules]

    def _build_reason(self, level, rules, ml):
        if not rules:
            if level == "SAFE":
                return "No fraud patterns detected; language consistent with legitimate messaging."
            return f"Language model flags risk (fraud likelihood {ml:.0%}) though no explicit rule pattern matched."
        parts = self._build_signals(rules)
        return f"{level}: detected {len(parts)} risk signal(s) — " + "; ".join(parts) + "."

    def _format(self, level, score, reason, signals, rules):
        return {
            "risk_level": level,
            "score": score,
            "reason": reason,
            "signals": signals,
            "recommended_action": ACTION_BY_LEVEL[level],
            "rule_categories": list(rules.keys()),
        }


if __name__ == "__main__":
    d = ScamDetector()
    tests = [
        "Sir this is CBI officer, your Aadhaar linked to money laundering. Send money to RBI account now.",
        "Your OTP for login is 482910. Do not share it with anyone. - HDFC Bank",
        "call me urgent send money",
        "Kal milte hain coffee ke liye, 5 baje theek hai?",
        "Aapka account suspend ho gaya, OTP batao turant warna band ho jayega",
    ]
    for t in tests:
        r = d.predict(t)
        print(f"[{r['risk_level']:11s} {r['score']:.2f}] {t[:55]:55s} -> {r['signals']}")
