import sqlite3, json
with sqlite3.connect('data/app.db') as conn:
    runs = conn.execute('SELECT id, status, model_used FROM agent_runs ORDER BY id DESC LIMIT 3').fetchall()
    for r in runs:
        meta = {}
        try:
            meta = json.loads(r[2] or '{}')
        except Exception:
            pass
        print(f"run {r[0]}: status={r[1]}")
        print(f"  error={meta.get('error')}")
        print(f"  steps={meta.get('steps_completed')}")
        print(f"  flags={len(meta.get('verification_flags', []))}")
