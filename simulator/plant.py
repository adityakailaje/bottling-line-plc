"""Physical model of the bottling line. No Modbus, no UI: easy to unit-test."""
import math
import random
from dataclasses import dataclass

from params import Params

# Tags the plant produces (sensors, to the PLC) and consumes (actuators, from it).
SENSOR_TAGS = (
    "I_EStop_OK", "I_InfeedPresent", "I_FillPos", "I_CapPos", "I_InspectPos",
    "I_CapPresent", "I_RejectBinFull", "I_OutfeedSensor", "I_ConvOL_OK",
    "I_TankLow_LS", "I_TankHigh_LS", "I_Heartbeat", "I_ConvRunning",
    "I_TankLevel_raw", "I_FillVolume_x10",
)
ACTUATOR_TAGS = (
    "Q_ConveyorRun", "Q_FillValve", "Q_CapperRun", "Q_RejectPusher",
    "Q_InfeedGate", "Q_BeaconGreen", "Q_BeaconAmber", "Q_BeaconRed",
    "Q_PumpSpeed_raw",
)
# Fault flags, in the order of holding registers 100..107 (see iomap.py)
FAULTS = ("estop", "overload", "jam", "nocap", "leak",
          "hb_freeze", "infeed_empty", "runfb_loss")


@dataclass
class Bottle:
    x: float = 0.0
    fill_ml: float = 0.0
    capped: bool = False
    cap_timer: float = 0.0


class Plant:
    def __init__(self, params=None, seed=None):
        self.p = params or Params()
        self.rng = random.Random(seed)
        self.faults = {name: False for name in FAULTS}
        self.bottles = []
        self.level_l = self.p.tank_l * self.p.tank_start_pct / 100.0
        self.speed = 0.0               # belt speed, m/s
        self.pusher = 0.0              # 0 retracted .. 1 extended
        self.bin_count = 0
        self.t = 0.0
        self.hb = False
        self.hb_timer = 0.0
        self.gate_prev = False
        self.last_outputs = {}
        self.stats = {"released": 0, "rejected": 0, "spilled_ml": 0.0,
                      "exits": []}     # exits: (fill_ml, capped) per bottle

    # ---- helpers -------------------------------------------------------
    @property
    def level_pct(self):
        return max(0.0, min(100.0, 100.0 * self.level_l / self.p.tank_l))

    def near(self, x_station):
        """Bottles inside the sensor window of a station."""
        return [b for b in self.bottles if abs(b.x - x_station) <= self.p.window]

    def command(self, code, arg=0):
        """One-shot test commands (also reachable over Modbus)."""
        if code == 1:                  # set tank level, arg = percent x 10
            self.level_l = self.p.tank_l * max(0, min(1000, arg)) / 1000.0
        elif code == 2:                # empty the reject bin
            self.bin_count = 0
        elif code == 3:                # clear all faults
            for name in self.faults:
                self.faults[name] = False
        elif code == 4:                # fill the reject bin (for test T09)
            self.bin_count = self.p.bin_capacity

    # ---- one simulation step ------------------------------------------
    def step(self, act, dt=None):
        p, f = self.p, self.faults
        dt = dt or p.dt
        self.t += dt

        # conveyor: speed ramps toward target; a jam blocks the bottles only
        run = bool(act.get("Q_ConveyorRun")) and not f["overload"]
        target = p.belt_speed if run else 0.0
        dv = p.belt_accel * dt
        self.speed += max(-dv, min(dv, target - self.speed))
        if not f["jam"]:
            for b in self.bottles:
                b.x += self.speed * dt
        for b in [b for b in self.bottles if b.x >= p.x_end]:
            self.bottles.remove(b)
            self.stats["exits"].append((b.fill_ml, b.capped))

        # infeed gate: a rising edge releases one bottle if there is room
        gate = bool(act.get("Q_InfeedGate"))
        if gate and not self.gate_prev and not f["infeed_empty"]:
            if not any(b.x < p.pitch * 0.5 for b in self.bottles):
                self.bottles.append(Bottle(x=0.0))
                self.stats["released"] += 1
        self.gate_prev = gate

        # tank, fill valve and filling
        flow_mls = p.valve_k_mls * math.sqrt(self.level_pct / 100.0)
        outflow_l = 0.0
        if act.get("Q_FillValve") and self.level_l > 0:
            outflow_l = flow_mls / 1000.0 * dt
            under = self.near(p.x_fill)
            put = 0.0
            if under:
                put = min(flow_mls * dt, p.bottle_capacity_ml - under[0].fill_ml)
                under[0].fill_ml += put
            self.stats["spilled_ml"] += flow_mls * dt - put
        pump = max(0, min(32767, int(act.get("Q_PumpSpeed_raw", 0)))) / 32767.0
        inflow_l = p.pump_max_lps * pump * dt
        leak_l = p.leak_lps * dt if f["leak"] else 0.0
        self.level_l = max(0.0, min(p.tank_l, self.level_l + inflow_l - outflow_l - leak_l))

        # capper: must run continuously for cap_time_s
        capper = bool(act.get("Q_CapperRun"))
        for b in self.near(p.x_cap):
            b.cap_timer = b.cap_timer + dt if capper else 0.0
            if b.cap_timer >= p.cap_time_s and not f["nocap"]:
                b.capped = True

        # reject pusher: removes a bottle at the reject station when extended
        rate = dt / p.pusher_time_s
        extend = bool(act.get("Q_RejectPusher"))
        self.pusher = max(0.0, min(1.0, self.pusher + (rate if extend else -rate)))
        if self.pusher >= 0.9:
            for b in self.near(p.x_reject):
                self.bottles.remove(b)
                self.bin_count += 1
                self.stats["rejected"] += 1

        return self._sensors(dt)

    def _sensors(self, dt):
        p, f = self.p, self.faults
        insp = self.near(p.x_inspect)
        if not f["hb_freeze"]:
            self.hb_timer += dt
            if self.hb_timer >= 0.5 - 1e-9:
                self.hb_timer = 0.0
                self.hb = not self.hb
        pct = self.level_pct
        noisy = pct + self.rng.uniform(-p.level_noise_pct, p.level_noise_pct)
        vol = 0.0
        if insp:
            vol = insp[0].fill_ml + self.rng.uniform(-p.fill_noise_ml, p.fill_noise_ml)
        return {
            "I_EStop_OK": not f["estop"],
            "I_InfeedPresent": not f["infeed_empty"],
            "I_FillPos": bool(self.near(p.x_fill)),
            "I_CapPos": bool(self.near(p.x_cap)),
            "I_InspectPos": bool(insp),
            "I_CapPresent": bool(insp and insp[0].capped),
            "I_RejectBinFull": self.bin_count >= p.bin_capacity,
            "I_OutfeedSensor": bool(self.near(p.x_outfeed)),
            "I_ConvOL_OK": not f["overload"],
            "I_TankLow_LS": pct > p.low_ls_pct,
            "I_TankHigh_LS": pct >= p.high_ls_pct,
            "I_Heartbeat": self.hb,
            "I_ConvRunning": self.speed > 0.1 * p.belt_speed and not f["runfb_loss"],
            "I_TankLevel_raw": int(max(0.0, min(100.0, noisy)) / 100.0 * 32767),
            "I_FillVolume_x10": int(max(0.0, min(500.0, vol)) * 10),
        }
