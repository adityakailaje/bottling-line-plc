"""Print the headline numbers from the stand-in controller runs (see Step 6)."""
import sys
sys.path.insert(0, "tests")

from plant import Plant
from test_standin import drive, make_controller

pl = Plant(seed=3)
control, st = make_controller()
drive(pl, 90, control)
gaps = [b - a for a, b in zip(st["starts"], st["starts"][1:])]
vols = [round(v, 1) for v, _ in pl.stats["exits"]]
print(f"nominal run, 90 s: {len(vols)} bottles out, rejected {pl.stats['rejected']}")
print(f"  volumes (ml): {vols}")
print(f"  cycle time: min {min(gaps):.2f} s, max {max(gaps):.2f} s; tank {pl.level_pct:.1f} %")

pl = Plant(seed=3)
pl.command(1, 200)                                   # tank to 20 %, pump off
control, st = make_controller(pump_enabled=False)
drive(pl, 60, control)
print(f"low tank, 60 s: released {pl.stats['released']}, rejected {pl.stats['rejected']}, "
      f"good out {len(pl.stats['exits'])}, tank {pl.level_pct:.1f} %")
