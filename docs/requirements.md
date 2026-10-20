# Specification: Automated Bottling Line

| Field | Value |
|---|---|
| Version | 0.1 (draft) |
| Date | 2026-10-18 |
| Author | Aditya Kailaje |
| Status | Draft |

## 1. Purpose

This document defines stable, individually testable requirements for the automated bottling-line simulation. Requirement IDs and verification-test references are assigned. Requirements are not marked passed until the corresponding test has been executed and evidence recorded.

Key for Prefixes: **R-S** = safety, **R-O** = operation, **R-Q** = quality, **R-P** = process control, **R-X** = system.

## 2. Requirements and verification traceability

| ID | Requirement | Verified by |
|---|---|---|
| R-S1 | On E-stop, the PLC shall de-energise all actuator outputs within one scan (50 ms); the simulator shall see this within one scan plus one polling period (100 ms). | T04 |
| R-S2 | E-stop and faults shall latch until the cause is cleared and a Reset rising edge is received. | T05, T06 |
| R-S3 | After a PLC restart or power cycle, outputs shall be off and the state shall be IDLE, with no automatic restart. | T14 |
| R-S4 | Loss of the simulator heartbeat for 2 s shall raise A04 and drive outputs to the safe state. | T15 |
| R-S5 | A conveyor overload shall stop the line and latch A02. | T06 |
| R-S6 | The fill valve shall open only when the conveyor is stopped and a bottle is at the fill position. | T03 |
| R-O1 | In Auto, the line shall run index, process and discharge cycles until the batch target is met. | T02, T13 |
| R-O2 | Manual jogs shall work only in Manual mode and only when interlocks are satisfied. | T03 |
| R-O3 | A mode change shall force the line to a stopped state. | T03 |
| R-O4 | At batch completion, the line shall flush, stop and wait for Acknowledge; the accepted-bottle count shall equal the target exactly. | T13 |
| R-O5 | A jam or station timeout shall raise A03 and stop the line. | T10 |
| R-O6 | A conveyor commanded on without run feedback for 2 s shall raise A09. | T18 |
| R-Q1 | Bottles outside 330 ml ±5 ml shall be rejected. | T07 |
| R-Q2 | Bottles without a cap shall be rejected. | T08 |
| R-Q3 | If the reject bin is full, the line shall hold in DISCHARGE and raise A07. | T09 |
| R-Q4 | Three consecutive rejects shall raise A06. | T07 |
| R-Q5 | Fill time shall be compensated for tank level between 25% and 90%. | T07, T12 |
| R-P1 | The tank level shall hold within 3% of setpoint in steady state. | T12, T16 |
| R-P2 | A setpoint step from 50% to 70% shall settle within 60 s with overshoot under 10%. | T12 |
| R-P3 | Tank level below 10% shall inhibit filling and raise A05. | T11 |
| R-P4 | Tank level above 95% shall set the pump to zero and raise A08. | T17 |
| R-X0 | Every signal shall match the I/O list in address, polarity and scaling. | T01 |
| R-X1 | The PLC scan shall remain stable at 50 ms with Modbus polling active. | T16 |
| R-X2 | The HMI shall show state, counters, alarms and tank level, and allow Start, Stop, Reset and Acknowledge. | T02, T13 |
| R-X3 | The line shall run unattended for 30 minutes without an unhandled fault. | T16 |

## 3. Verification conventions

- Execute tests according to [test-plan.md](test-plan.md).
- Record test date, actual result, pass/fail status and evidence reference for every execution.
- A requirement is considered verified only when the referenced test passes and the evidence is available.
- If a test fails, record the observed behaviour, corrective action and retest result. Do not silently edit the requirement to fit the implementation.
- Where a parameter or address changes, update [parameters.md](parameters.md), [io-list.csv](io-list.csv), [io-list-hmi.csv](io-list-hmi.csv), the test plan and affected requirements together.

## 4. Alarm coverage check

| Alarm | Meaning | Verification test |
|---|---|---|
| A01 | E-stop tripped | T04, T05 |
| A02 | Conveyor overload | T06 |
| A03 | Jam or timeout | T10 |
| A04 | Communication lost | T15 |
| A05 | Tank low-low | T11 |
| A06 | Consecutive rejects | T07 |
| A07 | Reject bin full | T09 |
| A08 | Tank high-high | T17 |
| A09 | Run feedback lost | T18 |

## 5. State coverage check

| State | State number | Planned test coverage |
|---|---:|---|
| IDLE | 0 | T01, T03, T14 |
| INDEXING | 10 | T02, T10 |
| PROCESSING | 20 | T02, T04, T07, T08, T11 |
| DISCHARGE | 30 | T02, T09 |
| BATCH_CHECK | 40 | T13 |
| FLUSH | 45 | T13 |
| BATCH_DONE | 50 | T13 |
| FAULT | 90 | T06, T10, T11, T15, T18 |
| ESTOP | 99 | T04, T05 |

## Change log

| Version | Date | Change | Reason |
|---|---|---|---|
| 0.1 | 2026-10-18 | Added the Week 2 guide's R-S1 through R-X3 requirements and their test references, plus alarm/state coverage checks. | Establish testable requirements and traceability for specification review. |
