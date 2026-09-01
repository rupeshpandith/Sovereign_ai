"""
Deep grounding diagnosis:
1. What does acquired_text actually look like from the DB?
2. What does verify_grounding see vs corpus?
3. What exact strings fail the substring check?
"""
import sys, json, sqlite3
sys.path.insert(0, '.')

# ── 1. Pull the last run's extracted text from DB ──────────────────────────
with sqlite3.connect('data/app.db') as conn:
    docs = conn.execute(
        "SELECT id, filename, extracted_text FROM documents ORDER BY id DESC LIMIT 5"
    ).fetchall()
    runs = conn.execute(
        "SELECT id, status, model_used FROM agent_runs ORDER BY id DESC LIMIT 5"
    ).fetchall()

print("=== RECENT DOCUMENTS ===")
for d in docs:
    text_preview = (d[2] or '')[:120].replace('\n', '\\n')
    print(f"  doc id={d[0]} name={d[1]} extracted_chars={len(d[2] or '')} preview={text_preview!r}")

print("\n=== RECENT AGENT RUNS ===")
for r in runs:
    meta = {}
    try: meta = json.loads(r[2] or '{}')
    except: pass
    flags = meta.get('verification_flags', [])
    print(f"  run id={r[0]} status={r[1]} flags={len(flags)}")
    for f in flags[:3]:
        print(f"    FLAG: {f}")

# ── 2. Simulate grounding check exactly as planner does ───────────────────
from app.agent.planner import verify_grounding
from app.rag.retrieve import retrieve_inspection_chunks, retrieve_sop_chunks

# Use the most recently uploaded inspection report text
doc_id, doc_filename, doc_text = docs[0]
acquired_text = doc_text or ''

print(f"\n=== ACQUIRED TEXT (len={len(acquired_text)}) ===")
print(repr(acquired_text[:400]))

# Simulate extracted dict as the model returns it
extracted_sim = {
    "equipment_id": "P-204",
    "inspection_date": "2026-08-15",
    "measurements": [
        {"parameter": "Vibration (NDE end)", "reading": "5.8 mm/s RMS", "unit": "mm/s RMS"},
        {"parameter": "Vibration (DE end)",  "reading": "6.7 mm/s RMS", "unit": "mm/s RMS"},
        {"parameter": "Bearing Temp (DE)",   "reading": "78 °C",         "unit": "°C"},
        {"parameter": "Bearing Temp (NDE)",  "reading": "74 °C",         "unit": "°C"},
        {"parameter": "Discharge Pressure",  "reading": "14.2 bar",      "unit": "bar"},
        {"parameter": "Motor Current",       "reading": "38.4 A",        "unit": "A"},
    ],
    "sop_ref": "SOP-17",
}

# Get real RAG evidence (same as planner)
sop_evidence = retrieve_sop_chunks("approval note P-204 SOP-17", n_results=4)
ir_evidence  = retrieve_inspection_chunks("P-204 inspection findings", equipment_tag="P-204", n_results=3)
all_evidence = sop_evidence + ir_evidence

print(f"\n=== RAG EVIDENCE ({len(all_evidence)} chunks) ===")
for ev in all_evidence:
    print(f"  source={ev.source_file} conf={ev.confidence:.2f} quote_len={len(ev.exact_quote)}")
    print(f"    quote: {ev.exact_quote[:100]!r}")

# Run grounding WITHOUT source_text (old behaviour)
flags_old = verify_grounding(extracted_sim, all_evidence, source_text="")
print(f"\n=== GROUNDING WITHOUT source_text: {len(flags_old)} flags ===")

# Run grounding WITH source_text (new behaviour)
flags_new = verify_grounding(extracted_sim, all_evidence, source_text=acquired_text)
print(f"\n=== GROUNDING WITH source_text: {len(flags_new)} flags ===")
for f in flags_new:
    print(f"  STILL FLAGGED: {f.claim_type}={f.value!r}")
    # Show what we actually searched for vs what's in the corpus
    corpus = '\n'.join(e.exact_quote for e in all_evidence).lower() + '\n' + acquired_text.lower()
    val = f.value.lower()
    print(f"    searching for: {val!r}")
    # Is it in acquired_text?
    in_acq = val in acquired_text.lower()
    print(f"    in acquired_text: {in_acq}")
    if not in_acq:
        # Show nearest match
        for candidate in [val[:5], val.split()[0]]:
            idx = acquired_text.lower().find(candidate)
            if idx >= 0:
                print(f"    nearest in text ({candidate!r}): {acquired_text[max(0,idx-5):idx+30]!r}")
