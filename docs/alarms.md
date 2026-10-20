# Specification: Automated Bottling Line

| Field | Value |
|---|---|
| Version | 0.1 (draft) |
| Date | 2026-10-18 |
| Author | Aditya Kailaje |
| Status | Draft |

## 1. Purpose and scope

This document defines the Week 2 alarm philosophy, alarm list, fault codes, HMI alarm-word mapping, and reusable `FB_Alarm` interface for the simulated automated bottling line.

The alarm behaviour is a specification for the PLC and simulator work to follow. The list does not imply that all alarms have already been implemented or tested. Alarm thresholds and process values are defined in [parameters.md](parameters.md), while signal names and addresses are defined in [io-list.csv](io-list.csv) and [io-list-hmi.csv](io-list-hmi.csv).

## 2. Alarm philosophy

### 2.1 Definitions

- **Fault:** A condition that stops the line. It is latched and requires a reset after the cause has cleared, as practised in industry.
- **Warning:** A condition that may allow the line to continue unless a specific action is stated. It remains latched until acknowledged once the cause is gone, except where the alarm is explicitly self-clearing.
- **Acknowledge:** Indicates that the operator has seen the alarm. It may silence or mark the indication as acknowledged, but it does not restart the line or clear a latched fault.
- **Reset:** Clears a latched fault or E-stop only when the cause has cleared. Reset is detected on a rising edge; a held command must not repeatedly reset the system.
- **Priority P1:** Safety-critical or immediate stop response.
- **Priority P2:** Stops or degrades production.
- **Priority P3:** Operator information; line can continue.

### 2.2 General rules

1. Safety-related inputs use the polarity convention `1 = healthy`; for example, `I_EStop_OK = 0` means E-stop/trip.
2. Safety alarms have a 0 s on-delay. Process alarms normally use a 0.5 s on-delay to filter brief signal fluctuations; individual alarm settings in the table below will be used.
3. A fault remains latched after its initiating condition clears until a Reset rising edge is received and the cause is no longer present.
4. A warning is acknowledged separately from fault reset. Acknowledge must never restart the line or clear a latched safety fault.
5. E-stop has the highest priority. When `I_EStop_OK = 0`, the PLC enters ESTOP and de-energises all actuator outputs in the specified control model.
6. The E-stop in this project is a simulation learning model implemented in ordinary PLC logic. Real machinery requires appropriately designed hard-wired or safety-rated emergency-stop equipment and must not rely solely on ordinary PLC software.
7. The HMI alarm banner and list use `ST_AlarmWord` to display alarm ID/message and priority. The HMI should indicate unacknowledged alarms distinctly (for example, flashing as specified in `hmi-spec.md`).

## 3. Final alarm list

| ID | Alarm | Trigger condition | On-delay | Class / priority | Required action | Clear / acknowledge rule |
|---|---|---|---:|---|---|---|
| A01 | E-stop tripped | `I_EStop_OK = 0` | 0 s | Fault / P1 | De-energise all actuator outputs and enter ESTOP (state 99); fault code 1. | E-stop input healthy and Reset rising edge received. |
| A02 | Conveyor overload | `I_ConvOL_OK = 0` | 0 s | Fault / P1 | Stop the line, enter FAULT (state 90); fault code 2. | Overload condition cleared and Reset rising edge received. |
| A03 | Jam or timeout | Indexing exceeds 8 s, a station timeout occurs, or FLUSH exceeds 20 s. | Timer / applicable timeout | Fault / P2 | Stop the line and enter FAULT (state 90). Fault code 3 for index/FLUSH timeout or 4 for station timeout. | Cause cleared and Reset rising edge received. |
| A04 | Communication lost | `I_Heartbeat` does not change for 2.0 s. | 2.0 s | Fault / P1 | Drive outputs to the specified safe state and enter FAULT (state 90); fault code 5. | Heartbeat is toggling again and Reset rising edge received. |
| A05 | Tank low-low | Tank level falls below 10%. | 0.5 s | Fault / P2 | Inhibit filling, stop the line and enter FAULT (state 90); fault code 6. | Tank level rises above 20% and Reset rising edge received. |
| A06 | Consecutive rejects | Three rejects occur consecutively. | None | Warning / P3 | Annunciate the warning; the line continues running. | Acknowledge command. |
| A07 | Reject bin full | `I_RejectBinFull = 1`. | 0.5 s | Warning / P2 | If a reject is required, hold the sequence in DISCHARGE until the bin-full condition is resolved. | Bin emptied and Acknowledge command received. |
| A08 | Tank high-high | Tank level rises above 95%. | 0.5 s | Warning / P2 | Force pump-speed command to zero. | Self-clears when tank level falls below 90%; no reset is specified for this alarm. |
| A09 | Run feedback lost | `Q_ConveyorRun = 1` while `I_ConvRunning = 0` continuously for 2.0 s. | 2.0 s | Fault / P2 | Stop the line and enter FAULT (state 90); fault code 7. | Cause cleared and Reset rising edge received. |

**Notes**

- The applicable index, station and FLUSH time limits are defined in [parameters.md](parameters.md).
- A05 is based on the tank level below 10%; the clearing condition requires the level to be above 20% as specified by the Week 2 guide.
- A08 is explicitly self-clearing when tank level falls below 90%. It is not a latched fault.
- A07 can hold the sequence at DISCHARGE when a rejected bottle needs to be removed. It is a warning with a process hold, not a safety-rated function.
- A03 covers different timeout sources. The fault code distinguishes index/FLUSH timeout (3) from station timeout (4).

## 4. Fault codes and HMI alarm word

### 4.1 Fault-code mapping

| Fault code | Meaning | Alarm ID | `ST_AlarmWord` bit |
|---:|---|---|---:|
| 1 | E-stop | A01 | 0 |
| 2 | Conveyor overload | A02 | 1 |
| 3 | Index or FLUSH timeout | A03 | 2 |
| 4 | Station timeout | A03 | 2 |
| 5 | Communication lost | A04 | 3 |
| 6 | Tank low-low | A05 | 4 |
| — | Consecutive rejects | A06 | 5 |
| — | Reject bin full | A07 | 6 |
| — | Tank high-high | A08 | 7 |
| 7 | Run feedback lost | A09 | 8 |

Bits 9–15 of `ST_AlarmWord` are reserved. A03 fault codes 3 and 4 share alarm-word bit 2 because both use alarm A03; the separate fault code identifies the timeout source.

### 4.2 Alarm-word behaviour

- `ST_AlarmWord` is exposed to the HMI through holding register 25 (`%QW125`), as specified in the csv [io-list-hmi.csv](io-list-hmi.csv).
- Bits 0–8 correspond to alarms A01–A09 as shown in the table above.
- The HMI decodes set bits into alarm IDs and messages and displays the associated priority.
- Unacknowledged status is handled by the alarm/HMI logic; the alarm word is the active-alarm bit map, not a substitute for the separate acknowledge command.
- `HMI_Ack` is mapped to coil 24 (`%QX103.0`). `HMI_Reset` is mapped separately to coil 10 (`%QX101.2`). Acknowledge and Reset must not be treated as interchangeable commands.
- `HMI_AutoAckBatch` is a separate optional engineering/test command used for unattended batch-end acknowledgement during endurance testing. It is not an alarm reset.

## 5. Reusable `FB_Alarm` interface

The Week 2 guide specifies the following interface for a reusable alarm function block:

| Pin | Direction | Type | Meaning |
|---|---|---|---|
| `Cond` | Input | `BOOL` | Raw alarm condition. |
| `OnDelay` | Input | `TIME` | Condition must remain active for this duration before the alarm becomes active. |
| `Latching` | Input | `BOOL` | `TRUE` for faults and most warnings; `FALSE` for self-clearing alarms such as A08. |
| `Ack_Reset` | Input | `BOOL` | Rising-edge acknowledge/reset command as appropriate to the configured alarm. Reset clears a latch only when `Cond = FALSE`. |
| `Active` | Output | `BOOL` | Alarm condition active after the configured on-delay. |
| `Latched` | Output | `BOOL` | Remains TRUE after `Cond` clears until the configured clearing command is received. |
| `Unacked` | Output | `BOOL` | TRUE while the alarm has been raised and not acknowledged; used by the HMI to indicate unacknowledged alarms. |

Implementation note: although the interface table groups the input as `Ack_Reset`, the alarm philosophy distinguishes operator Acknowledge from fault Reset. In the PLC implementation, handle those command semantics explicitly so that acknowledging an alarm cannot reset a fault, clear an E-stop, or restart the line. `Ack_Reset` represents the function-block command interface described in the Week 2 guide, not permission to merge the two operator actions into one system-level action.

## 6. Verification and traceability

The requirements and test plan are the source of truth for test IDs and acceptance evidence:

- [requirements.md](requirements.md)
- [test-plan.md](test-plan.md)

Alarm-focused checks will include at least the following cases:

| Test reference | Alarm / behaviour to verify | Expected result |
|---|---|---|
| T04 | E-stop response (A01) | Outputs go to zero within one scan plus one polling period (100 ms per the guide's acceptance criterion). |
| T05 / T06 | Latching/reset and overload (A02) | Fault remains latched until the cause clears and Reset is received; overload stops the line. |
| T07 | Consecutive rejects (A06) | Three consecutive rejects raise A06; line continues. |
| T09 | Reject bin full (A07) | Sequence holds in DISCHARGE when a reject is required and resumes after the bin is emptied and acknowledged. |
| T10 | Jam/station timeout (A03) | Timeout raises A03 and stops the line. |
| T11 | Tank low-low (A05) | Level below 10% inhibits filling and raises A05; clearing requires level above 20% and Reset. |
| T15 | Communication loss (A04) | Heartbeat loss for 2 s raises A04 and drives outputs to the specified safe state. |
| T17 | Tank high-high (A08) | Level above 95% for the 0.5 s filter sets pump command to zero; alarm clears below 90%. |
| T18 | Run feedback lost (A09) | Conveyor commanded on with run feedback absent for 2 s raises A09 and stops the line. |

When tests are run, actual results will be recorded in this file. This file (in this commit) only defines expected behaviour; it does not claim that these tests have already passed.

## Change log

| Version | Date | Change | Reason |
|---|---|---|---|
| 0.1 | 2026-10-18 | Documented alarm philosophy, alarms A01–A09, fault-code/alarm-word mapping, `FB_Alarm` interface and Week 2 test links. | Align alarm requirements with the Week 2 Specification Guide and the project plan. |
