"""Process parameters for the automated bottling line.

Single source of truth: docs/parameters.md.
Keep plant physics parameters here; PLC sequence logic and alarm behaviour
must also consume the relevant values from this specification.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Params:
    # Simulation
    dt: float = 0.02                 # simulation step, s

    # Conveyor and geometry (metres along the belt)
    belt_speed: float = 0.25         # m/s
    belt_accel: float = 1.0          # m/s^2, start and stop ramp
    pitch: float = 0.5               # station pitch, m
    window: float = 0.08             # position-sensor half-width, m
    x_fill: float = 0.5
    x_cap: float = 1.0
    x_inspect: float = 1.5
    x_reject: float = 2.0
    x_outfeed: float = 2.5
    x_end: float = 3.0               # bottles leave the belt here

    # Product and stations
    target_fill_ml: float = 330.0    # target bottle fill, ml
    fill_tolerance_ml: float = 5.0   # acceptance tolerance: target +/- 5 ml
    bottle_capacity_ml: float = 350.0
    cap_time_s: float = 1.0          # continuous run to seat a cap, s
    cap_cycle_s: float = 2.0         # full capper cycle, s; distinct from seating time
    pusher_time_s: float = 0.6       # reject-pusher extension interval, s
    bin_capacity: int = 10

    # Supply tank and pump
    tank_l: float = 20.0
    tank_start_pct: float = 70.0
    pump_max_lps: float = 0.20       # litres/s at 100% command
    leak_lps: float = 0.03           # additional outflow when leak fault is active
    valve_k_mls: float = 131.5       # flow = K * sqrt(level fraction), ml/s
    low_low_pct: float = 10.0        # low-low threshold, %
    low_ls_pct: float = 20.0          # low-level switch threshold, %
    high_ls_pct: float = 90.0         # high-level switch threshold, %
    high_high_pct: float = 95.0       # high-high threshold, %

    # Tank-level controller starting estimates (not tuned/validated)
    tank_setpoint_pct: float = 70.0
    tank_setpoint_min_pct: float = 50.0
    tank_setpoint_max_pct: float = 90.0
    pid_kp: float = 1.5
    pid_ti_s: float = 20.0

    # Fill-time compensation limits
    max_compensated_fill_time_s: float = 5.0

    # Sensor noise
    fill_noise_ml: float = 1.0       # +/- ml
    level_noise_pct: float = 0.2     # +/- percentage points
