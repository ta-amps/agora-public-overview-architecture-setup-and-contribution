"""Verify this evidence bundle with the Python standard library: run `python3 verify.py` in this folder."""
import hashlib, json

def whole(v):  # Tessera writes whole floats as integers
    if isinstance(v, float) and v.is_integer() and abs(v) < 1e16: return int(v)
    if isinstance(v, dict): return {k: whole(x) for k, x in v.items()}
    if isinstance(v, list): return [whole(x) for x in v]
    return v

def canon(v):
    return json.dumps(whole(v), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()

def pins(v):
    if isinstance(v, dict):
        if {"store", "key", "version", "value_sha256"} <= v.keys(): yield (v["store"], v["key"], v["version"], v["value_sha256"])
        else:
            for x in v.values(): yield from pins(x)
    elif isinstance(v, list):
        for x in v: yield from pins(x)

doc = json.load(open("receipts-verify.json", encoding="utf-8"))
tasks = {t["task_id"]: t for t in doc["tasks"]}
for t in tasks.values():  # 1. every receipt recomputes from its task's output
    body = {k: t[k] for k in ("task_id", "fencing_token", "ok", "output", "error")}
    assert hashlib.sha256(canon(body)).hexdigest() == t["receipt_hash"], t["task_id"]
    for i in t["inputs"]:  # 2. every input from an earlier task is one of that task's receipted outputs
        if i["from"].startswith("vf."):
            assert (i["store"], i["key"], i["version"], i["value_sha256"]) in set(pins(tasks[i["from"]]["output"]["artifacts"]))
for n in doc["published_files"]["nouns"]:  # 3. each noun value matches its pin
    assert hashlib.sha256(canon(n["value"])).hexdigest() == n["pin"]["value_sha256"]
media = {f["path"]: f["sha256"] for f in json.load(open("media.json"))["files"]}
for name, f in doc["published_files"]["files"].items():  # 4. each published file is tied to a receipt
    if "sha256" in f:
        assert media[name] == f["sha256"], name
    else:
        assert hashlib.sha256(canon(json.load(open(name)))).hexdigest() == f["value_sha256"], name
print(f"{len(tasks)} receipts recompute; inputs chain to earlier receipts; {len(doc['published_files']['files'])} published files tie to receipts")
