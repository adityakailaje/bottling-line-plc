"""Round-trip latency from a simulator event log (sim.py --log events.csv).

Usage: python tools/latency.py events.csv TRIGGER_TAG VALUE RESPONSE_TAG VALUE
Example: python tools/latency.py events.csv I_EStop_OK 0 Q_BeaconRed 1
"""
import csv
import sys

path, trig, trig_v, resp, resp_v = sys.argv[1:6]
with open(path, newline="") as f:
    rows = [(float(r["t_s"]), r["tag"], r["value"]) for r in csv.DictReader(f)]

delays = []
for i, (t, tag, v) in enumerate(rows):
    if tag == trig and v == trig_v:
        for t2, tag2, v2 in rows[i + 1:]:
            if tag2 == resp and v2 == resp_v:
                delays.append(t2 - t)
                break
if not delays:
    sys.exit("no matching trigger/response pairs found")
for d in delays:
    print(f"{d * 1000:7.0f} ms")
print(f"n={len(delays)}  mean={sum(delays) / len(delays) * 1000:.0f} ms  max={max(delays) * 1000:.0f} ms")
