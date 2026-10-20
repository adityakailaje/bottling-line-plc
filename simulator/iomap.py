"""CSV-driven mapping between the bottling-line plant and a Modbus datastore.

The frozen docs/io-list.csv is the source of truth for all 24 process I/O
signals. 

"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

# Modbus function codes, also accepted by pymodbus datastore getValues/setValues.
COIL = 1
DISCRETE = 2
HOLDING = 3
INPUT = 4

# Reserved simulator-control holding registers (not part of the 24 process tags).
CTRL_BASE = 100       # HR100..HR107: fault flags
CMD_REG = 120         # HR120: one-shot command code
ARG_REG = 121         # HR121: one-shot command argument

_OBJECT_TO_FC = {
    "COIL": COIL,
    "DI": DISCRETE,
    "HR": HOLDING,
    "IR": INPUT,
}
_SENSOR_OBJECTS = {"DI", "IR"}
_ACTUATOR_OBJECTS = {"COIL", "HR"}


class IoMap:
    """Load the I/O CSV and translate plant tags to Modbus datastore values.

    ``map`` deliberately has the simple shape ``tag -> (function_code, addr)``;
    the end-to-end tests and simulator use this to inspect the resolved mapping.
    """

    def __init__(self, path):
        self.path = Path(path)
        self.map: dict[str, tuple[int, int]] = {}
        self.rows: dict[str, dict[str, str]] = {}
        self.sensors: set[str] = set()
        self.actuators: set[str] = set()
        self.load_errors: list[str] = []
        self._load()

    def _load(self) -> None:
        if not self.path.is_file():
            raise FileNotFoundError(f"I/O list not found: {self.path}")

        with self.path.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            required = {"tag", "modbus_obj", "modbus_addr"}
            columns = set(reader.fieldnames or [])
            missing_columns = sorted(required - columns)
            if missing_columns:
                raise ValueError(
                    f"I/O list {self.path} is missing required column(s): "
                    + ", ".join(missing_columns)
                )

            seen_addresses: dict[tuple[int, int], str] = {}
            for line_no, raw in enumerate(reader, start=2):
                tag = (raw.get("tag") or "").strip()
                obj = (raw.get("modbus_obj") or "").strip().upper()
                addr_text = (raw.get("modbus_addr") or "").strip()
                if not tag:
                    self.load_errors.append(f"line {line_no}: empty tag")
                    continue
                if tag in self.rows:
                    self.load_errors.append(f"line {line_no}: duplicate tag {tag}")
                    continue
                if obj not in _OBJECT_TO_FC:
                    self.load_errors.append(
                        f"{tag}: unsupported modbus_obj {obj!r} (expected DI, IR, COIL or HR)"
                    )
                    continue
                try:
                    addr = int(addr_text)
                except (TypeError, ValueError):
                    self.load_errors.append(f"{tag}: invalid modbus_addr {addr_text!r}")
                    continue
                if addr < 0 or addr > 65535:
                    self.load_errors.append(f"{tag}: Modbus address out of range: {addr}")
                    continue

                fc = _OBJECT_TO_FC[obj]
                address_key = (fc, addr)
                previous = seen_addresses.get(address_key)
                if previous is not None:
                    self.load_errors.append(
                        f"{tag}: duplicate {obj} address {addr} also used by {previous}"
                    )
                    continue
                seen_addresses[address_key] = tag
                self.rows[tag] = dict(raw)
                self.map[tag] = (fc, addr)
                if obj in _SENSOR_OBJECTS:
                    self.sensors.add(tag)
                else:
                    self.actuators.add(tag)

    def check(self, sensor_tags: Iterable[str], actuator_tags: Iterable[str]) -> list[str]:
        """Return readable CSV/plant interface mismatches; empty means compatible."""
        errors = list(self.load_errors)
        expected_sensors = set(sensor_tags)
        expected_actuators = set(actuator_tags)

        for tag in sorted(self.sensors - expected_sensors):
            errors.append(f"{tag}: in the I/O list but not produced by the plant")
        for tag in sorted(expected_sensors - self.sensors):
            if tag in self.actuators:
                errors.append(f"{tag}: plant produces a sensor but I/O list classifies it as an actuator")
            elif tag not in self.map:
                errors.append(f"{tag}: produced by the plant but not in the I/O list")
            else:
                errors.append(f"{tag}: plant sensor is mapped to the wrong Modbus object")

        for tag in sorted(self.actuators - expected_actuators):
            errors.append(f"{tag}: in the I/O list but not consumed by the plant")
        for tag in sorted(expected_actuators - self.actuators):
            if tag in self.sensors:
                errors.append(f"{tag}: plant consumes an actuator but I/O list classifies it as a sensor")
            elif tag not in self.map:
                errors.append(f"{tag}: consumed by the plant but not in the I/O list")
            else:
                errors.append(f"{tag}: plant actuator is mapped to the wrong Modbus object")

        return errors

    def write_sensors(self, dev, sensors: dict) -> None:
        """Write plant sensor values into DI and IR addresses from the CSV."""
        for tag in self.sensors:
            if tag not in sensors:
                raise KeyError(f"Plant did not provide configured sensor {tag}")
            fc, addr = self.map[tag]
            value = sensors[tag]
            if fc == DISCRETE:
                dev.setValues(fc, addr, [bool(value)])
            elif fc == INPUT:
                dev.setValues(fc, addr, [max(0, min(65535, int(value)))])
            else:  # Defensive: check() should catch this before the loop starts.
                raise ValueError(f"Sensor {tag} is mapped to non-sensor Modbus function code {fc}")

    def read_actuators(self, dev) -> dict:
        """Read PLC outputs from COIL and HR addresses into a plant actuator dict."""
        values = {}
        for tag in self.actuators:
            fc, addr = self.map[tag]
            raw = dev.getValues(fc, addr, count=1)[0]
            if fc == COIL:
                values[tag] = bool(raw)
            elif fc == HOLDING:
                values[tag] = int(raw)
            else:  # Defensive: check() should catch this before the loop starts.
                raise ValueError(f"Actuator {tag} is mapped to non-actuator Modbus function code {fc}")
        return values


def sync_faults(dev, plant, mirror: list[int]) -> None:
    """Synchronize plant fault flags and HR100..HR107 with UI/Modbus writers.

    A register differing from its last simulator-written value is treated as a
    Modbus-client change. Otherwise the plant value (possibly changed by the UI)
    is mirrored into the register.
    """
    if len(mirror) != len(plant.faults):
        raise ValueError(
            f"Fault mirror has {len(mirror)} entries but plant has {len(plant.faults)} faults"
        )
    for i, name in enumerate(plant.faults):
        addr = CTRL_BASE + i
        register_value = int(dev.getValues(HOLDING, addr, count=1)[0])
        if register_value != int(bool(mirror[i])):
            plant.faults[name] = bool(register_value)
            mirror[i] = int(bool(register_value))
        else:
            plant_value = int(bool(plant.faults[name]))
            if plant_value != int(bool(mirror[i])):
                dev.setValues(HOLDING, addr, [plant_value])
                mirror[i] = plant_value


def run_command(dev, plant) -> None:
    """Execute HR120/HR121 once and clear both registers after processing."""
    code = int(dev.getValues(HOLDING, CMD_REG, count=1)[0])
    if code == 0:
        return
    arg = int(dev.getValues(HOLDING, ARG_REG, count=1)[0])
    try:
        plant.command(code, arg)
    finally:
        # Clear the command even if an unsupported code or plant command errors.
        dev.setValues(HOLDING, CMD_REG, [0])
        dev.setValues(HOLDING, ARG_REG, [0])
