import sys
sys.stdout.reconfigure(encoding="utf-8")

from bot.agent import chat

SESSION = "farmer_001"

MESSAGES = [
    "Hello",
    "What do you do?",
    "CBI ne call kiya arrest warrant hai mere naam pe",
    "Good morning",
    "Phir se CBI ka call aaya alag number se",
    "Ek aur call aaya lottery ka — KBC mein jeeta hai",
    "Maine woh zip file khol di jo HR ne bheji thi",
]

DIVIDER = "─" * 45

for i, msg in enumerate(MESSAGES, 1):
    r = chat(SESSION, msg)
    conf = f"{r['confidence']:.2f}" if r.get("confidence") is not None else "None"
    scam = r.get("scam_type") or "None"
    severity = r.get("severity", "")

    header = (
        f"Turn {i} | Intent: {r.get('intent', '?')} | "
        f"Engine: {r.get('engine')} | "
        f"Scam: {scam} | "
        f"Confidence: {conf} | "
        f"History: {r['history_length']} msgs"
    )
    if severity:
        header += f" | Severity: {severity}"

    print(header)
    print(r["answer"])
    print(DIVIDER)
