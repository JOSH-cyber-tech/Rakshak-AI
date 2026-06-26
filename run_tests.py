"""
Smoke + accuracy tests. Run: python3 run_tests.py
"""
import sys, time
from ml.detector import ScamDetector
from ml.session import FraudSessionDetector
from link.url_safety import analyze_url
from voice.voice_fraud import analyze_transcript
from graph.fraud_graph import FraudGraph
from geo.geo_fraud import GeoFraudLayer, demo_points
from casefile.case_generator import generate_case
from data.synth import generate_messages, generate_fraud_graph

ok = 0; fail = 0
def check(name, cond):
    global ok, fail
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    ok += cond; fail += (not cond)

print("Module 1 — Scam detection")
d = ScamDetector()
check("digital arrest -> FRAUD", d.predict("CBI officer arrest warrant send money to RBI account share OTP")["risk_level"] == "FRAUD")
check("legit OTP -> SAFE", d.predict("Your OTP is 482910. Do not share it. - HDFC Bank")["risk_level"] == "SAFE")
check("normal chat -> SAFE", d.predict("Kal coffee 5 baje?")["risk_level"] == "SAFE")
check("Hinglish scam -> FRAUD", d.predict("Aapka account band ho jayega OTP batao turant warna")["risk_level"] == "FRAUD")

print("Module 1 — held-out metrics")
rows = generate_messages(n_per_class=150, seed=999)
tp=fp=tn=fn=0
for text,label,_ in rows:
    pf = d.predict(text)["risk_level"] in ("FRAUD","SUSPICIOUS"); af = label=="FRAUD"
    tp+= pf and af; fp+= pf and not af; tn+= (not pf) and (not af); fn+= (not pf) and af
prec=tp/(tp+fp); rec=tp/(tp+fn); fpr=fp/(fp+tn)
print(f"    precision={prec:.3f} recall={rec:.3f} FPR={fpr:.3f}")
check("recall >= 0.95", rec >= 0.95)
check("precision >= 0.85", prec >= 0.85)

print("Module 2 — Session detector")
fsd = FraudSessionDetector(d); t0=time.time()
for i,m in enumerate(["hi","This is CBI Aadhaar money laundering","digital arrest do not disconnect","Transfer 50000 RBI share OTP"]):
    r = fsd.ingest("s1", m, ts=t0+i*60)
check("escalates to CRITICAL", r["severity"] == "CRITICAL" and r["active_scam_session"]=="YES")

print("Module 3 — Graph")
fg = FraudGraph(); fg.bulk_load(generate_fraud_graph()); g = fg.analyze()
check("kingpin is mastermind", g["central_nodes"][0]["id"] == "PH:+91-9000000001")
check("mules detected", any(n["role"]=="money_mule" for n in g["nodes"]))

print("Module 4 — Geo")
geo = GeoFraudLayer(); geo.bulk_add(demo_points()); gr = geo.analyze()
check("hotspots found", len(gr["hotspots"]) > 0)

print("Module 5 — Link")
check("phishing -> DANGEROUS", analyze_url("http://sbi-kyc-update.xyz/login")["risk_level"]=="DANGEROUS")
check("legit -> SAFE", analyze_url("https://www.onlinesbi.sbi/")["risk_level"]=="SAFE")

print("Module 6 — Voice")
check("scam script -> FRAUD", analyze_transcript("CBI arrest do not tell family transfer safe account", d)["risk_level"]=="FRAUD")

print("Module 7 — Case file")
case = generate_case(message_result=d.predict("CBI arrest send money OTP"), graph_result=g, subject="PH:x")
check("confirmed fraud case", case["classification"]=="CONFIRMED_FRAUD")
check("has integrity hash", len(case["integrity_hash"])==64)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
