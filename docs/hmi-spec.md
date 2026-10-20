# Specification: Automated Bottling Line

| Field | Value |
|---|---|
| Version | 0.1 (draft) |
| Date | 2026-10-18 |
| Author | Aditya Kailaje |
| Status | Draft |

## 1. Purpose

This document specifies the  HMI (Human-Machine Interface) for the simulated automated bottling line. It defines the screen layout, displayed values, operator commands, entry limits, signal mapping, and interaction rules required for smooth operation.

The HMI is a specified deliverable for a later implementation stage; this document does not claim that the HMI has already been built or tested.

## 2. HMI screen layout

The main screen shall follow the following wireframe:

```text
+-----------------------------------------------------------------------+
| MODE: AUTO       STATE: PROCESSING                   [ALARM BANNER]   |
+----------------------------------+------------------------------------+
| Line mimic (stations, bottles)   | Tank level [#######---] 70.0 %     |
| gate > fill > cap > inspect > out| Setpoint 70.0 %      Trend 5 min   |
+----------------------------------+------------------------------------+
| Good 18       Reject 2    Batch 3| Last fill 331.2 ml                  |
+----------------------------------+------------------------------------+
| [START] [STOP] [RESET] [ACK]        Mode: (Auto) (Manual)             |
| Manual: [Conv] [Fill] [Cap] [Reject]       Batch target [ 24 ]        |
+-----------------------------------------------------------------------+
```

The values in this drawing are illustrative only. Live values must come from the PLC status block; do not hard-code the sample values.

## 3. Screen elements and behaviour

| Element | Signal(s) | Type | Required behaviour |
|---|---|---|---|
| State and mode banner | `ST_State`, `HMI_AutoSel` | Display | Show the state number as text and identify Auto or Manual mode. The state number shall use the defined state map: 0 IDLE, 10 INDEXING, 20 PROCESSING, 30 DISCHARGE, 40 BATCH_CHECK, 45 FLUSH, 50 BATCH_DONE, 90 FAULT, 99 ESTOP. |
| Alarm banner and alarm list | `ST_AlarmWord` | Display | Decode active alarm bits into alarm ID and message. Colour by priority and make unacknowledged alarms visibly distinct; flash while unacknowledged. |
| Tank gauge and trend | `ST_TankLevel_x10` | Display | Display tank level from 0 to 100% and a rolling five-minute trend. `ST_TankLevel_x10` is expressed in tenths of a percentage point (0–1000 = 0.0–100.0%). |
| Tank-level setpoint | `HMI_LevelSP_x10` | Numeric entry | Enter setpoint in 0.1% units. HMI limits shall be 50–90% (500–900 raw). The PLC must independently clamp/validate to the same range. |
| Batch target | `HMI_BatchTarget` | Numeric entry | Target accepted bottles per batch. Default 24; HMI limits 1–99. The PLC must independently clamp/validate to 1–99. |
| Production counters | `ST_GoodCount`, `ST_RejectCount`, `ST_BatchCount` | Display | Display good/accepted, rejected and batch counters, with per-batch and total values where supported by the implementation. Ensure the meanings of per-batch and total values are made clear to the operator. |
| Last fill volume | `ST_LastFill_x10` | Display | Show last measured fill volume in ml to one decimal place; raw value is in 0.1 ml units. |
| Start | `HMI_Start` | Momentary command | On press, write 1, then return to 0 after approximately 300 ms. PLC uses rising-edge detection. |
| Stop | `HMI_Stop` | Momentary command | On press, write 1, then return to 0 after approximately 300 ms. In Auto, this requests the specified controlled stop at the end of the current cycle. |
| Reset | `HMI_Reset` | Momentary command | On press, write 1, then return to 0 after approximately 300 ms. PLC detects the rising edge. Reset only clears a latched fault/E-stop when the cause has cleared. |
| Acknowledge | `HMI_Ack` | Momentary command | On press, write 1, then return to 0 after approximately 300 ms. Acknowledge warnings or leave BATCH_DONE as specified; it does not reset faults or restart the line. |
| Auto/Manual selector | `HMI_AutoSel` | Level command | `1 = Auto`, `0 = Manual`. Mode change shall follow the specified stop-to-IDLE behaviour; PLC logic remains authoritative. |
| Manual jog buttons | `HMI_ManConv`, `HMI_ManFill`, `HMI_ManCap`, `HMI_ManReject` | Held commands | Show only in Manual mode. Each jog works only when the appropriate interlocks are satisfied. PLC ignores these commands in Auto and during a fault/E-stop. |
| Auto-acknowledge batch | `HMI_AutoAckBatch` | Level command | Place on an engineering/test tab, not among normal operator controls. Used for unattended endurance testing. It must not reset a fault or E-stop. |
| Running status lamp | `ST_Running` | Status display | Green indication when running. |
| Fault status lamp | `ST_Fault` | Status display | Red indication when a fault is active. |
| E-stop status lamp | `ST_EStop` | Status display | Red flashing indication when E-stop is active. |

## 4. Alarm indication and command semantics

### Alarm priorities

- **P1:** Safety-critical/immediate stop response.
- **P2:** Stops or degrades production.
- **P3:** Informational warning; the line may continue.

The HMI shall show alarm IDs and readable messages, not just an integer alarm word. Unacknowledged alarms shall be clearly distinguished from acknowledged alarms. Refer to [alarms.md](alarms.md) for the authoritative conditions, delays, priorities and clear rules.

### Acknowledge is not Reset

- **Acknowledge** means the operator has seen the warning/alarm indication. It may mark or silence the annunciation, but it does not restart the line or clear a latched safety fault.
- **Reset** clears a latched fault/E-stop only after its cause is no longer present and a Reset rising edge is received.
- The HMI must not combine these two actions into a single button.
- `HMI_AutoAckBatch` is only for engineering/endurance testing and is not a fault reset.

## 5. HMI signal/address mapping

The HMI uses the OpenPLC Runtime's own Modbus server, not the simulator's Modbus server. The guide uses a separate address block to avoid collisions with simulator I/O. HMI-written commands/setpoints are read by the PLC; PLC-written status values are read by the HMI. Maintain one writer per address.

The machine status signals `ST_Running`, `ST_Fault` and `ST_EStop` are listed in the project plan as PLC-to-HMI coils even though their OpenPLC addresses reside in the `%Q` image. Treat direction as the HMI protocol contract: only PLC logic writes these status values; the HMI reads them.

### Command and status coils

| Signal | Modbus object/address | OpenPLC address | Direction | Data / behaviour |
|---|---|---|---|---|
| `HMI_Start` | Coil 8 | `%QX101.0` | HMI → PLC | Momentary command; pulse approx. 300 ms |
| `HMI_Stop` | Coil 9 | `%QX101.1` | HMI → PLC | Momentary command; pulse approx. 300 ms |
| `HMI_Reset` | Coil 10 | `%QX101.2` | HMI → PLC | Momentary command; pulse approx. 300 ms |
| `HMI_AutoSel` | Coil 11 | `%QX101.3` | HMI → PLC | Level command; 1 Auto, 0 Manual |
| `HMI_ManConv` | Coil 12 | `%QX101.4` | HMI → PLC | Held jog command; Manual mode only |
| `HMI_ManFill` | Coil 13 | `%QX101.5` | HMI → PLC | Held jog command; Manual mode only |
| `HMI_ManCap` | Coil 14 | `%QX101.6` | HMI → PLC | Held jog command; Manual mode only |
| `HMI_ManReject` | Coil 15 | `%QX101.7` | HMI → PLC | Held jog command; Manual mode only |
| `ST_Running` | Coil 16 | `%QX102.0` | PLC → HMI | Running status |
| `ST_Fault` | Coil 17 | `%QX102.1` | PLC → HMI | Fault status |
| `ST_EStop` | Coil 18 | `%QX102.2` | PLC → HMI | E-stop status |
| `HMI_Ack` | Coil 24 | `%QX103.0` | HMI → PLC | Momentary acknowledge; pulse approx. 300 ms |
| `HMI_AutoAckBatch` | Coil 25 | `%QX103.1` | HMI → PLC | Level command; engineering/endurance tests |

### HMI holding registers

| Signal | Modbus object/address | OpenPLC address | Direction | Data / behaviour |
|---|---|---|---|---|
| `HMI_BatchTarget` | HR 10 | `%QW110` | HMI → PLC | Batch target, default 24, PLC limit 1–99 |
| `HMI_LevelSP_x10` | HR 11 | `%QW111` | HMI → PLC | Tank setpoint in tenths of a percent; 500–900 means 50.0–90.0% |
| `ST_State` | HR 20 | `%QW120` | PLC → HMI | Master state number |
| `ST_GoodCount` | HR 21 | `%QW121` | PLC → HMI | Good/accepted count |
| `ST_RejectCount` | HR 22 | `%QW122` | PLC → HMI | Rejected count |
| `ST_BatchCount` | HR 23 | `%QW123` | PLC → HMI | Batch counter/status value; define its exact display meaning in the implementation |
| `ST_TankLevel_x10` | HR 24 | `%QW124` | PLC → HMI | Tank level in tenths of a percentage point; 0–1000 = 0.0–100.0% |
| `ST_AlarmWord` | HR 25 | `%QW125` | PLC → HMI | Bit-packed active alarms; bits 0–8 map A01–A09; bits 9–15 reserved |
| `ST_LastFill_x10` | HR 26 | `%QW126` | PLC → HMI | Last fill in tenths of a millilitre; 0–5000 = 0–500.0 ml |

The row-by-row machine/HMI map is also kept in [io-list-hmi.csv](io-list-hmi.csv). The I/O CSV is the address source of truth; this document defines how the HMI presents and uses the signals.

## 6. Validation and operator feedback

1. The PLC must clamp `HMI_BatchTarget` to 1–99 before use.
2. The PLC must clamp `HMI_LevelSP_x10` to 500–900 (50.0–90.0%) before use.
3. If an entered value is changed by PLC-side clamping, display the effective accepted value on the HMI.
4. HMI command pulses must be returned to zero; PLC logic must edge-detect Start, Stop, Reset and Acknowledge commands.
5. HMI commands never override PLC interlocks, fault handling or E-stop behaviour.
6. Show the current mode, state, alarm conditions, tank level, counts and last measured fill so the operator can understand why the line is running, stopped or holding.
7. The line mimic is an indication of the simulated plant state; it must not be treated as a real safety display.

## 7. Verification

HMI functionality is verified through the requirements and test plan in [requirements.md](requirements.md) and [test-plan.md](test-plan.md). Relevant checks include displaying the correct state/counters/alarms/level, accepting Start/Stop/Reset/Acknowledge commands, enforcing PLC-side input limits, restricting manual jogs to Manual mode, and showing E-stop/fault status. Record actual results and evidence only after tests are run.

## Change log

| Version | Date | Change | Reason |
|---|---|---|---|
| 0.1 | 2026-10-18 | Defined HMI wireframe, screen elements, command semantics, entry limits, address map and verification expectations. | Align HMI specification with the Week 2 project plan. |
