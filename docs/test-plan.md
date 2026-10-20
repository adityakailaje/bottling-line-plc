# Specification: Automated Bottling Line

| Field | Value |
|---|---|
| Version | 0.1 (draft) |
| Date | 2026-10-18 |
| Author | [Your Name] |
| Status | Draft |

## 1. Purpose and test-record rules

This is the Week 2 baseline test plan for the simulated bottling-line PLC. It is based on Section 10 of the project plan and includes the additional requirements from the Week 2 Specification Guide, notably the revised T04 acceptance method and the new T17/T18 tests.

The plant, complete PLC sequence, HMI and process controller are planned implementation items. **All tests below are pending until actually executed.** Do not record Pass merely because the expected result is specified.

For every execution, fill in the execution record at the end of the relevant test with the date, observed result, Pass/Fail, evidence path and any corrective action. Capture a screenshot or simulator/runtime log excerpt for every test. Failed tests must be fixed and retested.

### Common test setup

- Raspberry Pi running OpenPLC Runtime.
- Python plant simulator implementing the signal map from [io-list.csv](io-list.csv).
- OpenPLC slave device configured for the simulator on Modbus TCP port 5020, with 13 discrete inputs, 8 coils, 2 input registers and 1 holding register.
- HMI connected to the OpenPLC Runtime's own Modbus server using the separate address block in [io-list-hmi.csv](io-list-hmi.csv).
- PLC task target: 50 ms; initial slave polling period: 100 ms.
- Numerical parameters from [parameters.md](parameters.md); alarm definitions from [alarms.md](alarms.md).
- Safety preconditions checked before tests that are not intended to trip E-stop: `I_EStop_OK = 1`, no active latched fault, and all test actuators/environment in a known state.

Do not connect this test plan to real plant equipment. The E-stop here is a simulated learning model, not a certified safety test.

## 2. Test summary

| Test | Scenario | Requirements / alarms covered |
|---|---|---|
| T01 | I/O verification | R-X0 |
| T02 | Normal Auto run | R-O1, R-X2 |
| T03 | Manual interlocks | R-S6, R-O2, R-O3 |
| T04 | E-stop during fill | R-S1, A01 |
| T05 | E-stop release | R-S2, A01 |
| T06 | Conveyor overload | R-S2, R-S5, A02 |
| T07 | Underfill reject | R-Q1, R-Q4, R-Q5, A06 |
| T08 | Missing cap | R-Q2 |
| T09 | Reject bin full | R-Q3, A07 |
| T10 | Bottle jam / timeout | R-O5, A03 |
| T11 | Tank low-low | R-P3, A05 |
| T12 | PID step response | R-Q5, R-P1, R-P2 |
| T13 | Batch complete | R-O1, R-O4, R-X2 |
| T14 | PLC restart | R-S3 |
| T15 | Communication loss | R-S4, A04 |
| T16 | Endurance | R-P1, R-X1, R-X3 |
| T17 | Tank high-high | R-P4, A08 |
| T18 | Run feedback lost | R-O6, A09 |

## 3. Detailed tests

### T01 — I/O verification

**Purpose:** Confirm all simulator-side signals match the specified address, polarity and scaling.

**Preconditions:** Simulator and OpenPLC Runtime available; all test values can be observed or driven by the simulator; the I/O list linter has been run.

**Procedure**
1. For every row in `docs/io-list.csv`, toggle/force each simulator input in turn and observe its mapped value in OpenPLC Monitoring or with a Modbus test tool.
2. For every output, command a known value from the PLC test program and verify that the simulator observes the expected coil or holding-register value.
3. Check analog minimum, representative intermediate and maximum values where practical.
4. Confirm the HMI address block is separate and does not collide with simulator-side I/O.
5. Compare actual object, zero-based address, OpenPLC mapping, polarity and range against the CSV. Run `python tools/check_io.py docs/io-list.csv`.

**Expected result / pass criterion:** Every signal matches `io-list.csv` in address, polarity and scaling; no unexpected shared addresses or orphan signals. The linter returns `OK: 24 signals checked`.

**Evidence:** Linter output, Monitoring screenshot and Modbus-tool output.

**Execution record:** Date: ____  Result: Pending  Pass/Fail: ____  Evidence: ____  Defect/fix: ____

### T02 — Normal Auto run

**Purpose:** Verify the standard automatic index/process/discharge cycle and basic HMI indications.

**Preconditions:** Safety healthy, no active fault, simulator in normal mode, batch target configured, product/plant model ready.

**Procedure**
1. Select Auto on the HMI.
2. Press Start once.
3. Run the process for 10 bottles.
4. Observe the state progression, station actions, good/reject counters, alarm banner and tank indication.

**Expected result / pass criterion:** The line completes the ten-bottle run without an unexpected alarm; counters match the simulated outcomes; station sequence proceeds through index, process and discharge. HMI displays state, counters, alarms and tank level.

**Requirements:** R-O1, R-X2.

**Evidence:** HMI screenshot and simulator/PLC log covering the run.

**Execution record:** Date: ____  Result: Pending  Pass/Fail: ____  Evidence: ____  Defect/fix: ____

### T03 — Manual interlocks

**Purpose:** Verify manual commands cannot bypass mode or safety interlocks.

**Preconditions:** Line stopped; manual and auto selection available.

**Procedure**
1. Select Manual and test each jog (conveyor, fill, capper, reject) with its interlocks satisfied.
2. Repeat each jog while E-stop is tripped; none may energise.
3. Select Auto and try manual jogs; they must be ignored.
4. In Manual, try the fill jog while a bottle is absent from the fill position and while the conveyor is running.
5. Request a mode change while the line is running.

**Expected result / pass criterion:** Actuators move only when the relevant interlocks are satisfied. Manual jogs are ignored in Auto and under E-stop. The fill valve opens only when a bottle is at the fill position and the conveyor is stopped. A mode change forces the line to a stopped state before changing modes.

**Requirements:** R-S6, R-O2, R-O3.

**Evidence:** HMI/Monitoring screenshots and simulator output log for each rejected/accepted jog condition.

**Execution record:** Date: ____  Result: Pending  Pass/Fail: ____  Evidence: ____  Defect/fix: ____

### T04 — E-stop during fill

**Purpose:** Verify immediate, highest-priority output shutdown.

**Preconditions:** Auto sequence active and the fill valve commanded open; timestamped simulator logging enabled.

**Procedure**
1. Start a fill cycle and verify `Q_FillValve = 1`.
2. Trip E-stop by setting `I_EStop_OK = 0`.
3. Measure the time from the trip to all actuator outputs reading zero in the simulator log.
4. Check state and alarm indication.

**Expected result / pass criterion:** PLC de-energises all actuator outputs within one scan (50 ms); the simulator sees outputs off within one scan plus one polling period, i.e. 100 ms under the specified 50 ms scan/100 ms polling setup. The valve closes, state becomes ESTOP (99), and A01 is active.

**Requirements / alarm:** R-S1, A01.

**Evidence:** Timestamped simulator log showing trip and output shutdown; Monitoring screenshot showing state 99.

**Execution record:** Date: ____  Result: Pending  Pass/Fail: ____  Measured shutdown time: ____ ms  Evidence: ____  Defect/fix: ____

### T05 — E-stop release

**Purpose:** Verify E-stop stays latched after the input returns healthy.

**Preconditions:** T04 has put the PLC into ESTOP.

**Procedure**
1. Restore `I_EStop_OK = 1`.
2. Do not press Reset.
3. Observe state and outputs.
4. Press Reset once (rising edge) after confirming the cause is cleared.

**Expected result / pass criterion:** The line stays stopped and outputs remain off after E-stop is released without Reset. Once E-stop is healthy and a Reset rising edge is received, the latch clears and the controller returns to IDLE; no automatic restart occurs.

**Requirements / alarm:** R-S2, A01.

**Evidence:** Screenshots/log before and after Reset.

**Execution record:** Date: ____  Result: Pending  Pass/Fail: ____  Evidence: ____  Defect/fix: ____

### T06 — Conveyor overload

**Purpose:** Verify overload trip, latching and reset behaviour.

**Preconditions:** Line running in Auto with simulator fault injection available.

**Procedure**
1. Inject a conveyor overload so `I_ConvOL_OK = 0`.
2. Observe state, outputs and alarm A02.
3. Restore `I_ConvOL_OK = 1` but do not press Reset.
4. Verify the fault remains latched.
5. Press Reset once after the cause has cleared.

**Expected result / pass criterion:** Line stops and enters FAULT (90); A02 latches with fault code 2. It clears only after overload cause is removed and Reset rising edge is received.

**Requirements / alarm:** R-S2, R-S5, A02.

**Evidence:** Simulator input log and Monitoring/alarm screenshot.

**Execution record:** Date: ____  Result: Pending  Pass/Fail: ____  Evidence: ____  Defect/fix: ____

### T07 — Underfill reject

**Purpose:** Verify fill-time compensation, measured-volume rejection and the consecutive-reject warning.

**Preconditions:** Normal Auto sequence, fill measurement available, tank-level control/simulator can be set to specified levels.

**Procedure**
1. Run bottles at representative tank levels within the specified compensation range (25–90%).
2. Observe calculated fill time and measured volume.
3. Confirm any bottle measured outside 330 ml ±5 ml is rejected.
4. Force three consecutive out-of-tolerance fills using simulator fault/level settings and observe A06.
5. Check the line continues while A06 is a warning.

**Expected result / pass criterion:** Fill time is compensated for tank level from 25% to 90%; bottles below 325 ml or above 335 ml are rejected. Three consecutive rejects raise A06 and the line continues. At approximately 20% tank level, the 5.0 s fill-time clamp may cause underfill, as shown by the parameter sanity check.

**Requirements / alarms:** R-Q1, R-Q4, R-Q5, A06.

**Evidence:** Trend/log of tank level, fill time and measured fill volumes; HMI alarm screenshot; reject counter.

**Execution record:** Date: ____  Result: Pending  Pass/Fail: ____  Evidence: ____  Defect/fix: ____

### T08 — Missing cap

**Purpose:** Verify cap inspection rejects an uncapped bottle.

**Preconditions:** Auto process available and cap-presence fault injection enabled.

**Procedure**
1. Inject an empty cap feed or set `I_CapPresent = 0` for a bottle at inspection.
2. Allow the bottle to complete the inspection/discharge stage.
3. Observe reject-pusher action and counters.

**Expected result / pass criterion:** The uncapped bottle is rejected and the rejected count increments. It is not counted as an accepted bottle.

**Requirement:** R-Q2.

**Evidence:** Simulator log and HMI/Monitoring screenshot showing cap input and result.

**Execution record:** Date: ____  Result: Pending  Pass/Fail: ____  Evidence: ____  Defect/fix: ____

### T09 — Reject bin full

**Purpose:** Verify the line holds safely when a rejected bottle cannot be discharged.

**Preconditions:** Auto sequence at or approaching DISCHARGE with a bottle requiring rejection.

**Procedure**
1. Set `I_RejectBinFull = 1` as a reject is required.
2. Observe state, output and alarm A07.
3. Empty the simulated reject bin by setting `I_RejectBinFull = 0`.
4. Acknowledge the warning and observe sequence recovery.

**Expected result / pass criterion:** The sequence holds in DISCHARGE while a reject is required and the bin is full; A07 is displayed after its 0.5 s filter. After the bin is emptied and acknowledged, the sequence resumes. Acknowledge does not reset a fault or restart the line from a fault state.

**Requirement / alarm:** R-Q3, A07.

**Evidence:** State/alarm screenshot before and after clear/acknowledge; simulator log.

**Execution record:** Date: ____  Result: Pending  Pass/Fail: ____  Evidence: ____  Defect/fix: ____

### T10 — Bottle jam / timeout

**Purpose:** Verify a jam or station timeout stops the line.

**Preconditions:** Line running, simulator can hold a position sensor off or block bottle movement.

**Procedure**
1. Start an Auto cycle.
2. Simulate a jam by blocking outfeed/movement or holding a required station sensor off.
3. Wait for the applicable index, station or FLUSH timeout.
4. Observe state, outputs, A03 and fault code.

**Expected result / pass criterion:** Timeout causes A03 and FAULT (90), and the line stops safely. Fault code is 3 for index/FLUSH timeout or 4 for station timeout. Reset is effective only after the cause is cleared.

**Requirement / alarm:** R-O5, A03.

**Evidence:** Timestamped timeout log and alarm/Monitoring screenshot.

**Execution record:** Date: ____  Result: Pending  Pass/Fail: ____  Evidence: ____  Defect/fix: ____

### T11 — Tank low-low

**Purpose:** Verify low-low inhibits filling and stops the line.

**Preconditions:** Auto sequence is filling, or is ready to enter a fill operation; tank-level simulation is controllable.

**Procedure**
1. Force tank level below 10% (the project plan's test procedure forces it to zero during fill).
2. Observe fill-valve command, state and A05.
3. Restore tank level to above 20%.
4. Press Reset once after the alarm cause has cleared.

**Expected result / pass criterion:** Filling is inhibited and A05 activates after the specified 0.5 s process-alarm on-delay; the line enters the defined stop/fault behaviour with fault code 6. The latch clears only when level is above 20% and Reset rising edge is received.

**Requirement / alarm:** R-P3, A05.

**Evidence:** Tank-level and valve command log plus alarm screenshot.

**Execution record:** Date: ____  Result: Pending  Pass/Fail: ____  Evidence: ____  Defect/fix: ____

### T12 — PID step response

**Purpose:** Verify tank-level setpoint response and fill compensation under tank-level changes.

**Preconditions:** Tank PID implementation is available and stable; line/model conditions are controlled.

**Procedure**
1. Put the level setpoint at 50%.
2. Record tank level and pump command.
3. Step the setpoint to 70%.
4. Record the tank-level and pump-command trace until the response settles.
5. Record any overshoot and steady-state deviation. Check that compensation remains active for levels between 25% and 90%.

**Expected result / pass criterion:** The setpoint step settles within 60 s with overshoot under 10%. In steady state, tank level is within 3% of setpoint. Fill time remains compensated over 25–90% tank level. These are design acceptance values and must be measured, not assumed.

**Requirements:** R-Q5, R-P1, R-P2.

**Evidence:** Time-stamped level/setpoint/pump trace and recorded settling/overshoot calculations.

**Execution record:** Date: ____  Result: Pending  Pass/Fail: ____  Settling time: ____ s  Overshoot: ____ %  Evidence: ____  Defect/fix: ____

### T13 — Batch complete

**Purpose:** Verify exact batch count, FLUSH behaviour and acknowledge.

**Preconditions:** Auto sequence functional; no faults active; HMI batch target can be changed.

**Procedure**
1. Set HMI batch target to 6.
2. Run in Auto until six bottles have passed inspection as accepted.
3. Observe BATCH_CHECK, FLUSH and BATCH_DONE progression.
4. Confirm the infeed gate stays closed during FLUSH and the conveyor clears the accepted bottles from the line.
5. At BATCH_DONE, press `HMI_Ack`.
6. Check Released, Accepted, Rejected, Outfeed and in-flight values for consistency.

**Expected result / pass criterion:** Line flushes, stops and waits in BATCH_DONE until acknowledged. Accepted bottles equal the batch target exactly (6). During the batch, `In flight = Released − Accepted − Rejected`; at the end of FLUSH, Outfeed equals Accepted. Acknowledge leaves BATCH_DONE and resets batch counters as specified by the sequence design.

**Requirements:** R-O1, R-O4, R-X2.

**Evidence:** HMI screenshot at BATCH_DONE, counters, simulator log and state transitions.

**Execution record:** Date: ____  Result: Pending  Pass/Fail: ____  Accepted: ____  Rejected: ____  Outfeed: ____  Evidence: ____  Defect/fix: ____

### T14 — PLC restart

**Purpose:** Verify safe startup and absence of automatic restart.

**Preconditions:** PLC/simulator map operational; a controlled run is active or the PLC is otherwise in a non-IDLE state.

**Procedure**
1. Record current state and outputs.
2. Restart OpenPLC Runtime (or power-cycle the Pi if performing the full check).
3. Observe state and actuator outputs before issuing any operator command.

**Expected result / pass criterion:** On restart, outputs are off and state is IDLE (0). The machine does not resume the previous cycle automatically; a new valid Start command is required.

**Requirement:** R-S3.

**Evidence:** Runtime/Monitoring screenshot immediately after restart and simulator output log.

**Execution record:** Date: ____  Result: Pending  Pass/Fail: ____  Evidence: ____  Defect/fix: ____

### T15 — Communication loss

**Purpose:** Verify heartbeat watchdog response and recovery.

**Preconditions:** Line running and simulator heartbeat toggling every 500 ms.

**Procedure**
1. Stop the simulator process or otherwise freeze the heartbeat.
2. Record the time of the last heartbeat transition.
3. Observe the communication watchdog, alarm A04 and outputs.
4. Restart the simulator and verify heartbeat returns.
5. Press Reset once after communication is healthy.

**Expected result / pass criterion:** A04 activates after no heartbeat transition for 2 s and outputs go to the specified safe state; fault code 5 is recorded. Reconnection alone does not clear the latched fault; Reset is required after the heartbeat is healthy.

**Requirement / alarm:** R-S4, A04.

**Evidence:** Timestamped simulator/runtime logs and alarm screenshot.

**Execution record:** Date: ____  Result: Pending  Pass/Fail: ____  Evidence: ____  Defect/fix: ____

### T16 — Endurance

**Purpose:** Verify unattended stability over 30 minutes.

**Preconditions:** Normal sequence, simulator, PLC and HMI running; fault injection disabled except for naturally generated process behaviour; optional engineering auto-acknowledge available.

**Procedure**
1. Enable `HMI_AutoAckBatch` for this engineering/endurance test.
2. Set a known valid batch target and start Auto.
3. Run unattended for 30 minutes while recording scan time, tank level, pump command, counters and active alarms.
4. Check counter consistency and review logs for unhandled faults.
5. Disable auto-acknowledge after the test.

**Expected result / pass criterion:** No unhandled fault occurs in 30 minutes; scan cycle remains stable at the 50 ms target with Modbus polling active; tank level holds within 3% of setpoint in steady state; counters remain consistent. At approximately 5.6 s per bottle, expect roughly 12–13 batches in 30 minutes, subject to simulator and sequence overhead.

**Requirements:** R-P1, R-X1, R-X3.

**Evidence:** 30-minute log, scan-time evidence, counter summary and start/end HMI screenshots.

**Execution record:** Date: ____  Result: Pending  Pass/Fail: ____  Unhandled faults: ____  Evidence: ____  Defect/fix: ____

### T17 — Tank high-high (Week 2 addition)

**Purpose:** Verify the high-high tank alarm and pump cutoff, closing the missing A08 test identified during creation of the Week 2 guide.

**Preconditions:** Tank-level simulation and pump output are controllable; no higher-priority E-stop is active.

**Procedure**
1. Force simulated tank level above 97%.
2. Hold it above the 95% high-high threshold for at least the 0.5 s process-alarm filter.
3. Observe A08 and `Q_PumpSpeed_raw`.
4. Lower the tank level below 90% and observe alarm clearing.

**Expected result / pass criterion:** After the 0.5 s filter, A08 appears and pump output goes to zero. A08 clears when tank level falls below 90%; no Reset is required for this self-clearing alarm.

**Requirement / alarm:** R-P4, A08.

**Evidence:** Level/pump trace with timestamps and alarm display.

**Execution record:** Date: ____  Result: Pending  Pass/Fail: ____  Evidence: ____  Defect/fix: ____

### T18 — Run feedback lost (Week 2 addition)

**Purpose:** Verify the conveyor run-feedback watchdog and A09.

**Preconditions:** Simulator exposes `I_ConvRunning` at discrete input 12 / `%IX101.4`; no E-stop active.

**Procedure**
1. Command the conveyor on.
2. Hold `I_ConvRunning = 0` while `Q_ConveyorRun = 1`.
3. Keep the condition present for 2.0 s and observe alarm/state.
4. Restore run feedback/cause and issue Reset after the cause has cleared.

**Expected result / pass criterion:** A09 appears after 2 s, the line stops and enters FAULT (90), and fault code 7 is recorded. The fault clears only after the cause is gone and Reset rising edge is received.

**Requirement / alarm:** R-O6, A09.

**Evidence:** Timestamped `Q_ConveyorRun` / `I_ConvRunning` trace and alarm/Monitoring screenshot.

**Execution record:** Date: ____  Result: Pending  Pass/Fail: ____  Evidence: ____  Defect/fix: ____

## 4. Traceability completeness checks

Before the Week 2 specification is frozen, verify all of the following:

- Every requirement in [requirements.md](requirements.md) maps to at least one test.
- Every test T01–T18 maps to at least one requirement.
- Every alarm A01–A09 appears in at least one test.
- Every master state (0, 10, 20, 30, 40, 45, 50, 90, 99) is reached or explicitly observed in at least one test.
- The I/O linter returns `OK: 24 signals checked` for `docs/io-list.csv`.
- Evidence is saved under the repository's `media/` folder or referenced by a stable path.

## 5. Test summary and sign-off

| Test ID | Date executed | Result (Pass/Fail/Blocked) | Evidence reference | Defect / corrective action / retest |
|---|---|---|---|---|
| T01 | — | Not run | — | — |
| T02 | — | Not run | — | — |
| T03 | — | Not run | — | — |
| T04 | — | Not run | — | — |
| T05 | — | Not run | — | — |
| T06 | — | Not run | — | — |
| T07 | — | Not run | — | — |
| T08 | — | Not run | — | — |
| T09 | — | Not run | — | — |
| T10 | — | Not run | — | — |
| T11 | — | Not run | — | — |
| T12 | — | Not run | — | — |
| T13 | — | Not run | — | — |
| T14 | — | Not run | — | — |
| T15 | — | Not run | — | — |
| T16 | — | Not run | — | — |
| T17 | — | Not run | — | — |
| T18 | — | Not run | — | — |

**Review status:** Draft. Specification review, peer review, execution results and approval remain to be completed.

## Change log

| Version | Date | Change | Reason |
|---|---|---|---|
| 0.1 | 2026-10-18 | Created T01–T16 from the project plan and incorporated the Week 2 updates for T04, T12, T13, T16, plus new T17/T18. Added procedures, acceptance criteria, requirement/alarm traceability and test record fields. | Establish a reproducible test plan before implementing the full simulator and control sequence. |
