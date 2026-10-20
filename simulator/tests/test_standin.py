"""A throw-away stand-in controller drives the plant through real cycles.
It is NOT the PLC program; it only proves the plant can support the specified cycle."""
import math

from plant import ACTUATOR_TAGS, Plant


def make_controller(pump_enabled=True):
    st = {"state": "INDEX", "t0": 0.0, "t_fill": 3.0, "reject": False, "starts": []}

    def control(pl, ins):
        p, now = pl.p, pl.t
        a = {t: False for t in ACTUATOR_TAGS}
        pct = ins["I_TankLevel_raw"] / 32767 * 100
        if pump_enabled:
            a["Q_PumpSpeed_raw"] = int(max(0.0, min(100.0, 30 + 3 * (70 - pct))) * 327.67)
        s, dt0 = st["state"], now - st["t0"]
        if s == "INDEX":
            a["Q_ConveyorRun"] = True
            a["Q_InfeedGate"] = dt0 < 0.5
            aligned = all(min(abs(b.x - k * p.pitch) for k in range(7)) <= 0.05
                          for b in pl.bottles)
            if dt0 > 1.5 and aligned:
                flow = p.valve_k_mls * math.sqrt(max(pct, 1.0) / 100)
                st.update(state="PROCESS", t0=now, t_fill=min(5.0, 330.0 / flow))
        elif s == "PROCESS":
            a["Q_FillValve"] = dt0 < st["t_fill"] and ins["I_FillPos"]
            a["Q_CapperRun"] = dt0 < 2.0 and ins["I_CapPos"]
            if dt0 >= max(st["t_fill"], 2.0) + 0.2:
                vol = ins["I_FillVolume_x10"] / 10.0
                bad = ins["I_InspectPos"] and (not ins["I_CapPresent"] or abs(vol - 330) > 5)
                st.update(state="DISCHARGE", t0=now, reject=bad)
        elif s == "DISCHARGE":
            a["Q_RejectPusher"] = st["reject"] and dt0 < 0.7
            if dt0 >= 0.8:
                st["starts"].append(now)
                st.update(state="INDEX", t0=now)
        return a

    return control, st


def drive(pl, seconds, control):
    ins = pl.step({})
    for _ in range(int(seconds / pl.p.dt)):
        ins = pl.step(control(pl, ins))
    return ins


def test_nominal_run_fills_caps_and_exits_good_bottles():
    pl = Plant(seed=3)
    control, st = make_controller()
    drive(pl, 90, control)
    exits = pl.stats["exits"]
    assert len(exits) >= 6
    assert all(capped and 325 <= vol <= 335 for vol, capped in exits)
    assert pl.stats["rejected"] == 0


def test_cycle_time_is_close_to_the_specified_six_seconds():
    pl = Plant(seed=3)
    control, st = make_controller()
    drive(pl, 90, control)
    gaps = [b - a for a, b in zip(st["starts"], st["starts"][1:])]
    assert gaps and all(5.5 <= g <= 6.5 for g in gaps)


def test_low_tank_forces_rejects_as_designed_for_test_t07():
    pl = Plant(seed=3)
    pl.command(1, 200)                       # 20 % and no pump, so it stays low
    control, st = make_controller(pump_enabled=False)
    drive(pl, 60, control)
    assert pl.stats["rejected"] >= 3
    assert all(capped and 325 <= vol <= 335 for vol, capped in pl.stats["exits"])
