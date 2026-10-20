# Specification: Automated Bottling Line

| Field | Value |
|---|---|
| Version | 0.1 (draft) |
| Date | 2026-10-18 |
| Author | Aditya Kailaje |
| Status | Draft |

## 1. Purpose and use

This document is made to act as the parameter single source of truth (SSoT) for the automated bottling-line specification. The values below are the Week 2 baseline for later simulator and PLC implementation. Each value includes its units and relevant rationale. If a value changes, I realise that I must update the PLC-related specifications, I/O ranges, simulator model, alarms, requirements and tests affected by that change.

Please note that these are specified design values and sanity-check calculations, not claims that the complete bottling process or PID loop has already been implemented or experimentally validated. This project is still under development as of 18-10-2026 when I'll be committing this.

## 2. Product and batch parameters

| Parameter | Value | Units / range | Rationale |
|---|---:|---|---|
| Target fill volume | 330 | ml | Common bottle size and below the 500.0 ml sensor range. |
| Fill tolerance | ±5 | ml | Approximately 1.5% of the target; tight enough to respond to tank-level variation. |
| Default batch size | 24 | accepted bottles | One case of 24 bottles. |
| HMI batch-target limits | 1 to 99 | accepted bottles | PLC must clamp/validate the HMI-entered value; can not simply rely only on HMI-side limits. |

The accepted-bottle count is the batch target. Rejected bottles do not count toward the target accepted quantity.

## 3. Timing parameters

| Parameter | Value | Units | Rationale |
|---|---:|---|---|
| Conveyor index (one station pitch) | 2.0 | s | Assumes conveyor speed 0.25 m/s over a 0.5 m station pitch. |
| Infeed-gate pulse | 0.5 | s | Intended to release one bottle per index. |
| Fill time at 70% tank level | 3.0 | s | 330 ml at approximately 110 ml/s. |
| Maximum compensated fill time | 5.0 | s | Caps compensation; below about 25% tank level, fills are expected to fall short and be rejected. |
| Cap cycle time | 2.0 | s | Shorter than the nominal fill time, so filling sets the cycle timing. |
| Inspection time | 1.0 | s | Shorter than the nominal fill time. |
| Reject-pusher extension | 0.6 | s | Time allowed to clear a rejected bottle from the belt. |
| Nominal cycle time per bottle | 5.6 | s | Calculation: 2.0 s index + 3.0 s fill + 0.6 s reject allowance |
| Approximate nominal throughput | 10.7 | bottles/min | Approximately 60 / 5.6. |
| Approximate duration for 24 bottles | 2.2 | min | Approximate estimate based on 24 nominal 5.6 s cycles; actual time depends on rejects, faults and sequence overhead. |

## 4. Timeouts and filters

  Parameter   Value   Units | Rationale |
|---|---:|---|---|
| Index timeout | 8 | s | Four times the nominal 2.0 s index duration. |
| FLUSH timeout | 20 | s | Allows several conveyor indexes to clear bottles already in flight. |
| Fill-station timeout | 6 | s | Approximately twice the nominal 3.0 s fill duration. |
| Cap-station timeout | 4 | s | Approximately twice the nominal 2.0 s cap cycle. |
| Inspection-station timeout | 3 | s | Approximately three times the nominal 1.0 s inspection duration. |
| Reject-station timeout | 2 | s | Allows the 0.6 s pusher extension plus sequence margin. |
| Communication heartbeat timeout | 2.0 | s | Represents approximately four missed heartbeat toggles at 0.5 s per toggle. |
| Conveyor run-feedback timeout | 2.0 | s | Allows time for the drive/run feedback to respond after a run command. |
| Safety-alarm on-delay | 0 | s | Safety trips are immediate in the simulated control logic. |
| Process-alarm on-delay | 0.5 | s | Filters brief process-signal fluctuations/noise. Individual alarms may specify a different delay where shown in `specification.md` and `alarms.md`. |

## 5. Supply tank and pump parameters

| Parameter | Value | Units / range | Rationale |
|---|---:|---|---|
| Tank capacity at 100% level | 20 | L | Holds approximately 60 bottles' nominal fill volume (20 L / 0.33 L per bottle ≈ 60.6). |
| Tank-level setpoint | 70 | % | Equivalent to 14 L in a 20 L tank, providing headroom above and below the setpoint. |
| HMI tank setpoint limits | 50 to 90 | % | HMI entry range; PLC must enforce the same limits independently. |
| Pump maximum inflow at 100% command | 0.20 | L/s | Approximately three times the estimated average consumption while the line runs. |
| Low-low tank-level threshold (LL) | 10 | % | Stop-class threshold; inhibits filling and stops the line as specified in the control/alarm specification. |
| Low-level switch | 20 | % | Low-level switch threshold. |
| High-level switch | 90 | % | High-level switch threshold. |
| High-high tank-level threshold (HH) | 95 | % | High-high threshold; pump output is forced to zero. |
| Valve flow coefficient, K | 131.5 | ml/s | Coefficient for the square-root tank-level flow model; gives approximately 110 ml/s at 70% level. |
| PI/PID proportional gain, Kp | 1.5 | — | Starting estimate only. |
| PI/PID integral time, Ti | 20 | s | Starting estimate only. |
| Pump-command output range | 0 to 100 | % | Clamp controller output to the permitted range. |
| Controller action | Direct acting | — | Starting configuration as specified in the Week 2 guide; verify action and response during later tuning. |
| Fill-volume simulated noise | ±1 | ml | Makes the fill tolerance and filtering meaningful in simulation. |
| Tank-level simulated noise | ±0.2 | percentage points | Makes filtering and controller behaviour meaningful in simulation. |

**Controller status:** `Kp = 1.5` and `Ti = 20 s` are initial estimates, not tuned or validated values. PID tuning is planned for Week 6 in my project plan. Use anti-windup and output clamping as part of the future controller implementation; verify controller direction and response in testing.

## 6. PLC scan cycle and Modbus polling

| Parameter | Value | Units | Status / rationale |
|---|---:|---|---|
| PLC task scan cycle | 50 | ms | Target scan cycle from the project plan and Week 2 guide. |
| OpenPLC slave-device polling period | 100 | ms | Initial configuration used during Week 1/early setup. |
| Planned slave-device polling period | 50 | ms | Planned reduction for Week 4; do not record it as active until changed and verified. |
| Assumed network latency | Below 50 | ms | Design assumption from the Week 2 scope, to be validated. It is not the measured Week 1 round-trip latency. |

Keep measured observations separate from specified values. For example, Week 1 simulator logs showed round-trip latency mostly around 0.20–0.22 s with occasional readings around 0.31 s; those measurements describe the current test setup and do not replace the design assumption above.

## 7. Fill-time compensation model

The PLC shall estimate the valve flow from the measured tank level and calculate the fill duration from the target volume.

### Equations

Let:

- `L_pct` = measured tank level in percent, from 0 to 100.
- `L_frac` = tank level as a fraction, `L_pct / 100`.
- `K` = valve flow coefficient, 131.5 ml/s.
- `Q_est` = estimated flow in ml/s.
- `V_target` = target fill volume, 330 ml.
- `t_fill` = calculated fill duration in seconds.

The specified model is:

```text
L_frac = L_pct / 100
Q_est = K × sqrt(L_frac)
t_fill = V_target / Q_est
t_command = min(t_fill, 5.0 s)
```

The worked examples below use the values specified in the Week 2 guide. Values are rounded to the precision shown there.

### Sanity check 1 — compensated fill versus fixed 3.0 s fill

| Tank level | Estimated flow (ml/s) | Calculated compensated time | Actual commanded time after 5.0 s clamp | Volume with compensation (ml) | Volume using fixed 3.0 s (ml) | Guide's result |
|---:|---:|---:|---:|---:|---:|---|
| 85% | 121.2 | 2.72 s | 2.72 s | 330.0 | 363.7 | Fixed-time fill rejects: +33.7 ml over target. |
| 70% | 110.0 | 3.00 s | 3.00 s | 330.0 | 330.0 | Both pass. |
| 50% | 93.0 | 3.55 s | 3.55 s | 330.0 | 278.9 | Fixed-time fill rejects: −51.1 ml. |
| 25% | 65.7 | 5.02 s | 5.00 s | 328.7 | 197.2 | Compensated fill passes at −1.3 ml from target. |
| 20% | 58.8 | 5.61 s | 5.00 s | 294.0 | 176.4 | Both reject; compensated fill is 36.0 ml below target. |

Pass/fail limits are 325–335 ml inclusive (330 ml ±5 ml). These calculations illustrate why compensation is needed: it makes fill volume tolerate level changes down to approximately 25%, while the 5.0 s cap means a low level around 20% still produces an underfill. A later reject test (T07 in the project plan) can force this condition by setting the simulated tank to 20%.

## 8. Tank-balance sanity check

### Sanity check 2 — average consumption, pump capacity and settling time

| Check | Calculation | Result | Interpretation |
|---|---|---:|---|
| Average product consumption while filling | 0.33 L / 5.6 s | ≈0.059 L/s | The pump's steady-state command is estimated at around 30% if inflow scales approximately with command. |
| Net tank gain at 100% pump command while line runs | 0.20 − 0.059 L/s | ≈0.14 L/s | The maximum net gain is approximately 0.7 percentage points of tank capacity per second for a 20 L tank. |
| Level increase from 50% to 70% | (70% − 50%) × 20 L | 4 L | Volume needed for the requested level step. |
| Idealised fill time for the 4 L step with the line idle | 4 L / 0.20 L/s | ≈20 s | Assumes maximum pump inflow and no product consumption. |
| Approximate fill time for the 4 L step while running | 4 L / (0.20 − 0.059) L/s | ≈30 s | Uses approximate net inflow while the bottling line consumes product. |
| Controller settling-time requirement | Specified acceptance target | Within 60 s | The estimate leaves room for a gradual controller response; actual performance must be tested after PID tuning. |

These are order-of-magnitude checks, not a substitute for simulator measurements. The 0.20 L/s pump inflow, flow model and consumption estimate must be represented consistently in the simulator.

## 9. Implementation and change-control notes

- `parameters.md` is the  SSoT for the numerical values used by the simulator in Week 3 and subsequent PLC logic.
- The I/O list must use compatible raw ranges: fill-volume input 0–500.0 ml (raw 0–5000 at 0.1 ml/count), tank level 0–100% (raw 0–32767), and pump command 0–100% (raw 0–32767), as specified in the I/O design.
- Validate HMI-entered batch target (1–99) and tank setpoint (50–90%) in PLC logic; client-side limits alone are insufficient.
- When changing a parameter, check affected calculations, PLC constants, simulator behaviour, I/O range/scaling, alarm thresholds, requirement acceptance criteria and test cases. Record the reason in [decisions.md](decisions.md) and update the specification version/change log as appropriate.
- Alarm definitions and their specific delay/clear behaviour are maintained in [alarms.md](alarms.md). Signal addresses/scaling are maintained in [io-list.csv](io-list.csv) and [io-list-hmi.csv](io-list-hmi.csv). HMI entry/display details are maintained in [hmi-spec.md](hmi-spec.md).

## Change log

| Version | Date | Change | Reason |
|---|---|---|---|
| 0.1 | 2026-10-18 | Added the planned Week 2 parameter tables, rationale, fill-compensation worked example, tank-balance sanity check and implementation notes. | Establish a single documented parameter baseline for later simulator and PLC implementation. |
