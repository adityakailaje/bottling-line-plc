# Bottling Line PLC Project

A Week 1 proof of concept connecting a Python Modbus TCP simulator to OpenPLC Runtime on a Raspberry Pi. The simulator supplies discrete and analog inputs; the PLC mirrors the button state to a lamp coil and scales the tank-level value into a pump-speed command.

## Status: Week 1

The Week 1 setup and first Modbus round trip are documented in `docs/lab-notebook.md`.

## Quick start

### 1. Prerequisites and network

- Raspberry Pi running OpenPLC Runtime and reachable from your PC.
- Python 3.10+ on the machine running the simulator.
- The Pi and simulator host must be on the same reachable network.
- Keep Modbus ports restricted to your local network; do not expose them to the internet.

Find the Raspberry Pi address over SSH:

```bash
hostname -I
```

Open the OpenPLC dashboard at `http://PI_IP:8080`, where PI_IP should be replaced by the RPi's IP address on common router (or `http://plcpi.local:8080` if local hostname resolution works). 

The OpenPLC Modbus server uses TCP port `502`. The Python simulator listens on TCP port `5020`.


### 2. Start the Python simulator

From the repository root, open a terminal on the computer that will host the simulator:

**Windows PowerShell**
```powershell
cd simulator
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python sim_week1.py
```

**Linux/macOS**
```bash
cd simulator
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python sim_week1.py
```

The simulator should print that it is listening on `0.0.0.0:5020`. Find the simulator computer's LAN IP (`ipconfig` on Windows, `ip a` on Linux). If it is running on Windows, allow Python through the firewall on private networks for TCP port `5020`. Do not create a public router port-forward.

The guide pins `pymodbus==3.6.9` in `simulator/requirements.txt`; keep this version for compatibility with the supplied script.

### 3. Configure the OpenPLC slave device (Week 1 Guide, Step 7)

In the OpenPLC dashboard, open **Slave Devices** → **Add new device** and use:

| Field | Value |
|---|---|
| Device name | `sim` |
| Protocol | `Generic Modbus TCP Device` |
| Slave ID | `1` |
| IP address | `SIM_IP` (the simulator host's LAN IP; use `127.0.0.1` only if the simulator runs on the Pi itself) |
| Port | `5020` |
| Discrete inputs | Start address `0`, size `12` |
| Coils | Start address `0`, size `8` |
| Input registers | Start address `0`, size `2` |
| Holding registers - read | Start address `0`, size `0` |
| Holding registers - write | Start address `0`, size `1` |

Save the device. If the PLC was already running, stop and start it so the new device configuration loads. Confirm the runtime log has no connection errors. The OpenPLC slave-device IP is the **simulator's** IP, not the Raspberry Pi's IP (unless the simulator runs on the Pi).

### 4. Start and check the PLC

1. Upload the relevant Structured Text program (`.st`) through **Programs** in the dashboard if it is not already uploaded; launch it.
2. Click **Start PLC**.
3. Open **Monitoring** and check `I_Button`, `Q_Lamp`, `I_TankLevel_raw`, `Q_PumpSpeed_raw`, `Level_pct`, and `I_Heartbeat` as applicable to the running program.
4. Watch the simulator terminal: `I_Button` changes about every 3 seconds, and `Q_Lamp` should follow it. The pump holding-register value should track approximately half the tank-level input.
5. To stop the test, click **Stop PLC** and press `Ctrl+C` in the simulator terminal.

### 5. Troubleshooting checks

- Connection refused/timeouts: check simulator is running, `SIM_IP`, TCP port `5020`, host firewall, and network reachability.
- Values stay at zero: save the slave device, stop/start the PLC, and check start addresses and sizes.
- Values are shifted by one: the simulator uses zero-based addresses (`zero_mode=True`); preserve the `-0` option when testing with `mbpoll`.
- Editor Generate button unavailable: the `.st` program can be authored directly in a text editor, then uploaded through the dashboard. Ensure the code is valid Structured Text and that the required program variables/locations and runtime mapping are correct.

## Modbus map (zero-based)

| Signal | Modbus object | Address | PLC mapping / purpose |
|---|---|---:|---|
| `I_Button` | Discrete input | 0 | `%IX100.0`, button input |
| `I_Heartbeat` | Discrete input | 11 | `%IX101.3`, heartbeat |
| `I_TankLevel_raw` | Input register | 0 | `%IW100`, raw tank level |
| `Q_Lamp` | Coil | 0 | `%QX100.0`, lamp output |
| `Q_PumpSpeed_raw` | Holding register (write) | 0 | `%QW100`, pump command |

For a readback from the Pi, the Week 1 guide's examples are:

```bash
mbpoll -m tcp -a 1 -0 -1 -t 1 -r 0 -c 12 -p 5020 SIM_IP
mbpoll -m tcp -a 1 -0 -1 -t 0 -r 0 -c 8 -p 5020 SIM_IP
mbpoll -m tcp -a 1 -0 -1 -t 4 -r 0 -c 1 -p 5020 SIM_IP
```

Replace `SIM_IP` with the simulator host's address (which in my case is just my PC's IP). `mbpoll` options may differ by installed version; use `mbpoll -h` if an option is rejected.
