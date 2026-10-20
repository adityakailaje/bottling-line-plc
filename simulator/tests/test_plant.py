"""Unit tests: each one proves a statement in the Week 2 specification."""
from params import Params
from plant import ACTUATOR_TAGS, SENSOR_TAGS, Bottle, Plant


def act(**kw):
    d = {t: False for t in ACTUATOR_TAGS}
    d["Q_PumpSpeed_raw"] = 0
    d.update(kw)
    return d


def run(plant, seconds, a):
    ins = {}
    for _ in range(round(seconds / plant.p.dt)):
        ins = plant.step(a)
    return ins


def test_sensor_dictionary_is_complete():
    ins = Plant(seed=1).step(act())
    assert set(ins) == set(SENSOR_TAGS)


def test_fill_at_nominal_level_is_within_tolerance():
    pl = Plant(seed=1)
    pl.bottles = [Bottle(x=pl.p.x_fill)]
    run(pl, 3.0, act(Q_FillValve=True))
    assert abs(pl.bottles[0].fill_ml - 330.0) < 3.0          # spec: 330 +/- 5 ml


def test_fill_at_low_level_falls_short():
    pl = Plant(seed=1)
    pl.command(1, 200)                                       # tank to 20 %
    pl.bottles = [Bottle(x=pl.p.x_fill)]
    run(pl, 3.0, act(Q_FillValve=True))
    assert pl.bottles[0].fill_ml < 200.0                     # about 176 ml


def test_valve_without_bottle_spills_and_drains_tank():
    pl = Plant(seed=1)
    run(pl, 2.0, act(Q_FillValve=True))
    assert pl.stats["spilled_ml"] > 200 and pl.level_pct < 70.0


def test_cap_needs_continuous_run_time():
    pl = Plant(seed=1)
    pl.bottles = [Bottle(x=pl.p.x_cap)]
    run(pl, 0.5, act(Q_CapperRun=True))
    assert not pl.bottles[0].capped
    run(pl, 0.2, act())                                      # stopping resets the timer
    run(pl, 0.5, act(Q_CapperRun=True))
    assert not pl.bottles[0].capped
    run(pl, 0.6, act(Q_CapperRun=True))
    assert pl.bottles[0].capped


def test_nocap_fault_prevents_capping():
    pl = Plant(seed=1)
    pl.faults["nocap"] = True
    pl.bottles = [Bottle(x=pl.p.x_cap)]
    run(pl, 2.0, act(Q_CapperRun=True))
    assert not pl.bottles[0].capped


def test_reject_pusher_removes_bottle_and_fills_bin():
    pl = Plant(seed=1)
    pl.bottles = [Bottle(x=pl.p.x_reject)]
    run(pl, 0.6, act(Q_RejectPusher=True))
    assert pl.bottles == [] and pl.bin_count == 1 and pl.stats["rejected"] == 1


def test_bin_full_sensor_and_empty_command():
    pl = Plant(seed=1)
    pl.bin_count = pl.p.bin_capacity
    assert pl.step(act())["I_RejectBinFull"] is True
    pl.command(2)
    assert pl.step(act())["I_RejectBinFull"] is False


def test_fill_bin_command_for_test_t09():
    pl = Plant(seed=1)
    pl.command(4)
    assert pl.step(act())["I_RejectBinFull"] is True


def test_index_distance_matches_ramped_belt():
    pl = Plant(seed=1)
    pl.bottles = [Bottle(x=0.0)]
    run(pl, 2.0, act(Q_ConveyorRun=True))
    expected = 0.25 * (2.0 - 0.25 / (2 * 1.0))               # v * (t - v / 2a)
    assert abs(pl.bottles[0].x - expected) < 0.01


def test_stop_on_sensor_edge_with_comms_latency_stays_in_window():
    """PLC stops the belt 0.25 s after the fill sensor rises (poll + scan + poll)."""
    pl = Plant(seed=1)
    pl.bottles = [Bottle(x=0.0)]
    stop_at, ins = None, {}
    for _ in range(int(6 / pl.p.dt)):
        run_cmd = stop_at is None or pl.t < stop_at
        ins = pl.step(act(Q_ConveyorRun=run_cmd))
        if ins["I_FillPos"] and stop_at is None:
            stop_at = pl.t + 0.25
    assert pl.speed == 0.0
    assert ins["I_FillPos"] is True
    assert abs(pl.bottles[0].x - pl.p.x_fill) <= pl.p.window


def test_pump_raises_level_at_spec_rate():
    pl = Plant(seed=1)
    pl.command(1, 500)                                       # 50 %
    run(pl, 10.0, act(Q_PumpSpeed_raw=32767))
    assert abs(pl.level_pct - 60.0) < 0.5                    # 0.2 L/s * 10 s = 2 L = 10 %


def test_gate_releases_one_bottle_per_rising_edge():
    pl = Plant(seed=1)
    run(pl, 1.0, act(Q_InfeedGate=True))
    assert pl.stats["released"] == 1


def test_infeed_empty_fault_releases_nothing():
    pl = Plant(seed=1)
    pl.faults["infeed_empty"] = True
    ins = run(pl, 1.0, act(Q_InfeedGate=True))
    assert pl.stats["released"] == 0 and ins["I_InfeedPresent"] is False


def test_overload_stops_belt_and_drops_ok_signal():
    pl = Plant(seed=1)
    pl.faults["overload"] = True
    ins = run(pl, 1.0, act(Q_ConveyorRun=True))
    assert pl.speed == 0.0 and ins["I_ConvOL_OK"] is False and ins["I_ConvRunning"] is False


def test_jam_keeps_belt_running_but_bottles_stuck():
    pl = Plant(seed=1)
    pl.faults["jam"] = True
    pl.bottles = [Bottle(x=0.0)]
    ins = run(pl, 2.0, act(Q_ConveyorRun=True))
    assert pl.bottles[0].x == 0.0 and ins["I_ConvRunning"] is True


def test_run_feedback_loss_fault():
    pl = Plant(seed=1)
    pl.faults["runfb_loss"] = True
    ins = run(pl, 1.5, act(Q_ConveyorRun=True))
    assert pl.speed > 0.2 and ins["I_ConvRunning"] is False


def test_heartbeat_toggles_and_can_freeze():
    pl = Plant(seed=1)
    seen = set()
    for _ in range(100):
        seen.add(pl.step(act())["I_Heartbeat"])
    assert seen == {True, False}
    pl.faults["hb_freeze"] = True
    seen = {pl.step(act())["I_Heartbeat"] for _ in range(100)}
    assert len(seen) == 1


def test_tank_switches_follow_level():
    pl = Plant(seed=1)
    pl.command(1, 150)
    ins = pl.step(act())
    assert ins["I_TankLow_LS"] is False and ins["I_TankHigh_LS"] is False
    pl.command(1, 970)
    ins = pl.step(act())
    assert ins["I_TankLow_LS"] is True and ins["I_TankHigh_LS"] is True


def test_p_only_level_control_leaves_the_expected_offset_with_a_leak():
    """Preview of Week 6: P-only control (Kp 3, base 0) settles near 65 % with the leak on."""
    pl = Plant(seed=1)
    pl.faults["leak"] = True
    ins = {}
    for _ in range(int(400 / pl.p.dt)):
        pct = ins.get("I_TankLevel_raw", 22937) / 32767 * 100
        pump = max(0.0, min(100.0, 3.0 * (70.0 - pct)))
        ins = pl.step(act(Q_PumpSpeed_raw=int(pump * 327.67)))
    assert 63.5 < pl.level_pct < 66.5
