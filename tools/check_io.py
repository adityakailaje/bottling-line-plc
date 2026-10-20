"""Lint docs/io-list.csv: unique tags and addresses, consistent OpenPLC mapping."""

import csv
import sys
from collections import Counter

PATH = sys.argv[1] if len(sys.argv) > 1 else "docs/io-list.csv"
PREFIX = {"DI": "I_", "IR": "I_", "COIL": "Q_", "HR": "Q_"}


def expected(obj, n):
    if obj == "DI":
        return f"%IX{100 + n // 8}.{n % 8}"
    if obj == "COIL":
        return f"%QX{100 + n // 8}.{n % 8}"
    if obj == "IR":
        return f"%IW{100 + n}"
    return f"%QW{100 + n}"  # HR: holding register written by the PLC


with open(PATH, newline="") as f:
    rows = list(csv.DictReader(f))

errors = []
for r in rows:
    tag, obj = r["tag"].strip(), r["modbus_obj"].strip().upper()
    if obj not in PREFIX:
        errors.append(f"{tag}: unknown modbus_obj '{obj}'")
        continue
    if not tag.startswith(PREFIX[obj]):
        errors.append(f"{tag}: {obj} tags must start with {PREFIX[obj]}")
    try:
        n = int(r["modbus_addr"])
    except ValueError:
        errors.append(f"{tag}: modbus_addr must be an integer")
        continue
    if r["openplc_addr"].strip() != expected(obj, n):
        errors.append(f"{tag}: openplc_addr should be {expected(obj, n)}")

for tag, c in Counter(r["tag"] for r in rows).items():
    if c > 1:
        errors.append(f"{tag}: duplicate tag")

for key, c in Counter((r["modbus_obj"], r["modbus_addr"]) for r in rows).items():
    if c > 1:
        errors.append(f"{key}: address used twice")

for e in errors:
    print("ERROR:", e)
print(f"{'FAILED' if errors else 'OK'}: {len(rows)} signals checked")
sys.exit(1 if errors else 0)
