"""Bottling-line plant simulator: Modbus TCP server + fixed-step plant loop.

Usage:  python sim.py [--ui] [--port 5020] [--iolist ../docs/io-list.csv] [--log events.csv]
"""
import argparse
import asyncio
import csv
import time
from pathlib import Path

from pymodbus.datastore import (ModbusSequentialDataBlock,
                                ModbusServerContext, ModbusSlaveContext)
from pymodbus.server import StartAsyncTcpServer

from iomap import IoMap, run_command, sync_faults
from params import Params
from plant import ACTUATOR_TAGS, FAULTS, SENSOR_TAGS, Plant

DEFAULT_IOLIST = Path(__file__).resolve().parent.parent / "docs" / "io-list.csv"
QUIET = {"I_Heartbeat"}          # toggles constantly; keep it out of the event log


def build_context():
    def block():
        return ModbusSequentialDataBlock(0, [0] * 200)
    # zero_mode=True: client address 0 is list index 0 (no +1 offset)
    store = ModbusSlaveContext(di=block(), co=block(), hr=block(), ir=block(),
                               zero_mode=True)
    return ModbusServerContext(slaves=store, single=True)


class EventLog:
    """Prints (and optionally saves) every change of a digital signal."""

    def __init__(self, path=None, echo=True):
        self.prev, self.echo = {}, echo
        self.file = open(path, "w", newline="") if path else None
        self.writer = csv.writer(self.file) if self.file else None
        if self.writer:
            self.writer.writerow(["t_s", "tag", "value"])

    def update(self, values, t):
        for tag, v in values.items():
            if tag in QUIET or not isinstance(v, bool):
                continue
            if self.prev.get(tag) != v:
                if self.prev.get(tag) is not None or v:
                    if self.echo:
                        print(f"[{t:8.2f}s] {tag:<16} -> {int(v)}")
                    if self.writer:
                        self.writer.writerow([f"{t:.2f}", tag, int(v)])
                        self.file.flush()
                self.prev[tag] = v


async def plant_loop(plant, iomap, ctx, log, view=None):
    dev = ctx[0]
    mirror = [0] * len(FAULTS)
    next_t = time.monotonic()
    last_status = 0.0
    while True:
        sync_faults(dev, plant, mirror)
        run_command(dev, plant)
        acts = iomap.read_actuators(dev)
        plant.last_outputs = acts
        sensors = plant.step(acts)
        iomap.write_sensors(dev, sensors)
        log.update({**sensors, **acts}, plant.t)
        if view is not None and not view.update(plant, sensors, acts):
            return
        if log.echo and plant.t - last_status >= 10.0:
            last_status = plant.t
            print(f"[{plant.t:8.2f}s] status: tank {plant.level_pct:5.1f} %  "
                  f"on belt {len(plant.bottles)}  rejected {plant.stats['rejected']}")
        next_t += plant.p.dt
        await asyncio.sleep(max(0.0, next_t - time.monotonic()))


async def amain(args):
    plant = Plant(Params(), seed=args.seed)
    iomap = IoMap(args.iolist)
    errors = iomap.check(SENSOR_TAGS, ACTUATOR_TAGS)
    if errors:
        raise SystemExit("I/O list does not match the plant:\n  " + "\n  ".join(errors))
    ctx = build_context()
    view = None
    if args.ui:
        from ui import View          # imported only when needed
        view = View()
    log = EventLog(args.log)
    print(f"Simulator listening on {args.host}:{args.port}  "
          f"({len(iomap.map)} signals from {args.iolist})")
    server = asyncio.create_task(
        StartAsyncTcpServer(context=ctx, address=(args.host, args.port)))
    loop = asyncio.create_task(plant_loop(plant, iomap, ctx, log, view))
    done, pending = await asyncio.wait({server, loop}, return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()
    for task in done:
        task.result()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=5020)
    ap.add_argument("--iolist", default=str(DEFAULT_IOLIST))
    ap.add_argument("--log", default=None, help="write digital events to this CSV")
    ap.add_argument("--seed", type=int, default=None, help="fix the sensor-noise seed")
    ap.add_argument("--ui", action="store_true", help="show the pygame view")
    try:
        asyncio.run(amain(ap.parse_args()))
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
