# Specification: Automated Bottling Line

| Field | Value |
|---|---|
| Version | 0.1 (draft) |
| Date | 2026-10-18 |
| Author | Aditya Kailaje |
| Status | Draft |

## 1. Purpose

This document records the design decisions that establish the specification baseline for the automated bottling line. Decisions affect the PLC sequence, simulator, alarms, I/O map, HMI and test campaign.

These are specification decisions for later implementation and verification. They do not imply that the complete line, HMI or PID controller has already been implemented or tested.

## 2. Decision log

| ID | Decision | Rationale |
|---|---|---|
| D-01 | Set the default batch target to 24 accepted bottles, with an HMI entry range of 1–99. | A batch of 24 represents one case. The PLC will clamp the value so an invalid HMI entry cannot be used directly. |
| D-02 | Set the target fill volume to 330 ml with an acceptance tolerance of ±5 ml. | This is the selected bottle target and gives a defined, testable quality limit for inspection and reject logic. |
| D-03 | Use a 20 L tank with a default level setpoint of 70% (14 L). | The chosen setpoint leaves room above and below for tank-level control and disturbances. |
| D-04 | Use flashing green in IDLE, steady green while running, amber for warnings (flashing at BATCH DONE), steady red for FAULT, and flashing red for ESTOP. | This gives the operator a consistent, quickly readable indication of the current state. This decision supersedes the earlier project plan's green-steady-in-IDLE convention. |
| D-05 | Run the tank-level PI/PID control in every state except ESTOP; force pump output to zero above the high-high tank threshold. | The tank should be kept near setpoint before production starts, while ESTOP must turn the pump command off. |
| D-06 | Reject a bottle if its measured fill volume is outside 330 ml ±5 ml **or** the cap is missing. | Fill volume and cap presence are independent quality checks; either failure is enough to reject the bottle. |
| D-07 | Track four counters: Released, Accepted, Rejected and Outfeed. Add state FLUSH (45) so remaining accepted bottles clear the line before BATCH DONE. | Counting only at outfeed can overshoot the requested accepted batch because bottles may still be in flight. The extra counters and FLUSH state make batch completion explicit. This decision supersedes the simpler batch logic in the earlier project plan. |
| D-08 | Require a Reset rising edge and a cleared cause before clearing a latched fault or E-stop. Keep Acknowledge separate; it does not restart the line. | This avoids a held button repeatedly resetting the system and prevents acknowledgement from being mistaken for permission to restart. |
| D-09 | Ignore Start while any fault is latched. | The operator must deliberately clear the fault before requesting a new run. |
| D-10 | Use 0 s on-delay for safety alarms and 0.5 s on-delay for process alarms unless an alarm specifies a different timeout. | Safety trips should be immediate; a short process delay filters brief signal fluctuations. Specific watchdogs and timeout alarms retain their defined timings. |
| D-11 | Add `I_ConvRunning` at discrete input 12 (`%IX101.4`), add `HMI_Ack` at coil 24 (`%QX103.0`), and add `HMI_AutoAckBatch` at coil 25 (`%QX103.1`). Add alarm A09 and tests T17/T18. | The motor function block needs a run-feedback input; warnings and BATCH DONE need an acknowledge command; unattended endurance testing needs an optional batch auto-acknowledge command. |
| D-12 | Make Stop a controlled stop at the end of the current cycle; make E-stop immediate. | A normal Stop should avoid leaving a bottle part-way through a cycle. E-stop has higher priority and must trigger the specified immediate response. |

## 3. Consequences and documents affected

| Decision(s) | Documents / implementation areas affected |
|---|---|
| D-01, D-02, D-03 | [parameters.md](parameters.md), [specification.md](specification.md), [hmi-spec.md](hmi-spec.md), [requirements.md](requirements.md), [test-plan.md](test-plan.md) |
| D-04, D-05, D-06, D-07, D-08, D-09, D-10, D-12 | [specification.md](specification.md), [alarms.md](alarms.md), [requirements.md](requirements.md), [test-plan.md](test-plan.md), future PLC sequence and process-control implementation |
| D-11 | [io-list.csv](io-list.csv), [io-list-hmi.csv](io-list-hmi.csv), [alarms.md](alarms.md), [requirements.md](requirements.md), [test-plan.md](test-plan.md), future simulator and OpenPLC slave-device configuration |

The I/O list is the intended map for the complete simulated bottling line. The Week 1 simulator is still a smaller round-trip demonstration, so its existing addresses must not be assumed to implement the complete Week 2 map. Implement and verify the updated map during the simulator work before relying on these signals in the running control logic.

## 4. Peer-review notes


| Ref | Reviewer comment | Response | Follow-up / status |
|---|---|---|---|
| PR-M1 | “I think the batch logic needs a bit more detail. If you only count bottles when they reach the outfeed, couldn’t a few bottles already on the conveyor push the batch past 24?” | “Yes, that was the gap I wanted to close. I’ve specified separate Released, Accepted, Rejected and Outfeed counters, and added the FLUSH state. The in-flight count is `Released - Accepted - Rejected`, and the infeed gate stops releasing bottles when the accepted target plus bottles still in flight reaches the target. Once the target is accepted, the line clears the remaining bottles before declaring BATCH DONE.” | Check the state logic and counters when implementing T13. |
| PR-M2 | “The alarm table says acknowledge and reset in a few places. Can the operator accidentally acknowledge a fault and have the machine start again?” | “That would be a bad surprise, so I’ve made the distinction explicit: Acknowledge is only for recognising warnings or leaving BATCH DONE; Reset is a separate rising-edge command and only clears a latched fault when its cause is gone. Neither command should start the line, and Start is ignored while a fault is latched.” | Verify command semantics in T05, T06, T09 and T13. |


## 5. Change-control rules

1. Treat the decisions above as the Week 2 draft baseline.
2. If a decision changes, add a new entry or update the decision with a clear ID, date, reason and affected documents; do not silently change an agreed value.
3. Cross-check the change against the parameters, I/O mapping, alarms, HMI, requirements and test cases.
4. Before freezing the specification, complete the peer review and resolve or record every comment.
5. When the specification is reviewed and frozen, update document headers and change logs to the version required by the Week 2 guide. After tagging the baseline, every change requires a change-log entry and a version bump.

## Change log

| Version | Date | Change | Reason |
|---|---|---|---|
| 0.1 | 2026-10-18 | Recorded Week 2 decisions D-01–D-12 and added clearly labelled mock peer-review examples and a template for actual review notes. | Keep key design choices and their rationale visible and traceable across the specification. |
