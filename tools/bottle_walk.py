"""
Windows-native replacement for tools/bottle_walk.sh

Usage:
    python tools/bottle_walk.py [HOST] [PORT] [pass|reject]

Requires pymodbus 3.6.9.
"""
import sys
import time
from pymodbus.client import ModbusTcpClient

HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 5020
MODE = sys.argv[3].lower() if len(sys.argv) > 3 else "pass"

if MODE not in ("pass", "reject"):
    raise SystemExit("Mode must be 'pass' or 'reject'.")

client = ModbusTcpClient(HOST, port=PORT, timeout=3)

def check_response(response, operation):
    if response is None or response.isError():
        raise RuntimeError(f"{operation} failed: {response}")

def coil(address, value):
    response = client.write_coil(address, bool(value), slave=1)
    check_response(response, f"write coil {address}={int(bool(value))}")

def read_reg(register_type, address):
    if register_type == 3:
        response = client.read_input_registers(address, count=1, slave=1)
    elif register_type == 1:
        response = client.read_discrete_inputs(address, count=1, slave=1)
    else:
        raise ValueError(f"Unsupported register type: {register_type}")
    check_response(response, f"read type {register_type}, address {address}")
    return response

def index():
    coil(0, 1)
    time.sleep(2.0)
    coil(0, 0)
    time.sleep(0.3)

try:
    if not client.connect():
        raise ConnectionError(
            f"Could not connect to {HOST}:{PORT}. "
            "Check that the simulator is running and the host/port are correct."
        )

    print(f"Connected to {HOST}:{PORT}; mode={MODE}")
    print("release one bottle")
    coil(4, 1)
    time.sleep(0.3)
    coil(4, 0)

    print("index to the fill station")
    index()

    print("fill for 3 s")
    coil(1, 1)
    time.sleep(3.0)
    coil(1, 0)

    print("index to the cap station")
    index()

    print("cap for 1.5 s")
    coil(2, 1)
    time.sleep(1.5)
    coil(2, 0)

    print("index to inspection")
    index()

    volume_response = read_reg(3, 1)
    print(f"fill volume x10 (IR1): {volume_response.registers[0]}")

    cap_response = read_reg(1, 5)
    print(f"cap present (DI5):     {int(cap_response.bits[0])}")

    print("index to the reject station")
    index()

    if MODE == "reject":
        print("fire the reject pusher")
        coil(3, 1)
        time.sleep(0.6)
        coil(3, 0)
    else:
        print("index to the outfeed sensor")
        index()
        print("index off the belt")
        index()

    print("done")

except (OSError, RuntimeError, ConnectionError, ValueError) as exc:
    print(f"ERROR: {exc}", file=sys.stderr)
    raise SystemExit(1)
finally:
    client.close()
