# Week 1 Lab Notebook — Setup and First Modbus Round Trip

**Date:** 2026-10-18  
**Project:** Bottling Line PLC  
**Platform:** Raspberry Pi + OpenPLC Runtime + Python Modbus TCP simulator


## What I did

- Prepared the Raspberry Pi OS environment, enabled SSH, updated packages, and installed the required tools.
- Installed OpenPLC Runtime and used the web dashboard to configure the runtime. The Modbus server was configured on TCP port `502`; DNP3 and EtherNet/IP were not needed. “Start in run mode” was left unchecked, and the slave-device polling period/timeout were set to 100 ms/1000 ms.
- Created the project repository structure and Python simulator environment. The simulator uses `pymodbus==3.6.9`, listens on TCP port `5020`, and exposes the Week 1 discrete inputs, coil, and registers using zero-based addressing.
- Added the simulator as an OpenPLC slave device:
  - Device name: `sim`
  - Protocol: `Generic Modbus TCP Device`
  - Slave ID: `1`
  - IP/port: `<SIMULATOR_LAN_IP>:5020`
  - Discrete inputs: start `0`, size `12`
  - Coils: start `0`, size `8`
  - Input registers: start `0`, size `2`
  - Holding registers — read: start `0`, size `0`
  - Holding registers — write: start `0`, size `1`
- Wrote the Structured Text program directly in a `.st` file using a text editor rather than generating it through OpenPLC Editor. Uploaded the `.st` file through the OpenPLC dashboard and used the runtime to launch it.
- Checked the simulator console and OpenPLC Monitoring page for the input/output round trip and analog values.

## Round-trip latency

- **Measurement method:** Use the simulator console's `Q_Lamp -> ... (... s after last button change)` message. The script timestamps the last `I_Button` transition and the observed `Q_Lamp` transition using `time.monotonic()`.
- **Measured typical latency:** **0.21s**
- **Observed range (if measured):** **0.2-0.32s**
- **Interpretation:** Latency includes simulator update timing, OpenPLC slave polling, PLC task execution, and the return write to the simulator. Wi-Fi and host scheduling can add to the variation observed.

## A Problem I faced and fixes/workarounds

### OpenPLC Editor Generate button was greyed out

**Problem:** The OpenPLC Editor's “Generate program for OpenPLC Runtime” / Generate button was disabled, so I could not use the normal editor-generated `.st` workflow.

**Fix/workaround:** I authored the Structured Text directly in a plain-text editor and saved it as a `.st` file, then uploaded that file through the OpenPLC dashboard under **Programs**. I launched the uploaded program from the dashboard. This bypassed the Editor's code-generation step while retaining the runtime upload/compile workflow.


## Decisions made

- **Direct `.st` editing:** Used a text editor because the Editor Generate button was greyed out. This kept progress moving.
- **Modbus transport:** Used Modbus TCP on the local network. The simulator listens on `5020`; OpenPLC's own Modbus server is on `502`.
- **Startup safety:** Left “Start in run mode” unchecked so the PLC does not automatically resume control after a reboot.
- **Network security:** Kept ports `502` and `5020` on the local network only and did not configure router port forwarding.

## Verification and evidence

- [ ] Simulator starts and prints that it is listening on port `5020`.
- [ ] OpenPLC runtime is reachable at `http://192.168.1.139:8080/`.
- [ ] Slave device `sim` is saved with the settings above.
- [ ] `I_Button` changes and `Q_Lamp` follows it.
- [ ] Actual round-trip latency recorded above from console output.
- [ ] `PRG_Analog` checks completed: pump value approximately half of tank-level raw input, `Level_pct` scales from 0–100%, and heartbeat toggles.
- [ ] Independent `mbpoll` readback completed.
- [ ] Fault tests completed: simulator stopped/restarted; PLC stopped/started.
- [ ] Screenshots saved: slave-device settings, Monitoring, `mbpoll` output, and simulator console.
- [ ] Final Git commit pushed.

## End-of-week summary

The Week 1 workflow was adapted to bypass the disabled OpenPLC Editor Generate button by authoring Structured Text directly in a `.st` file.
