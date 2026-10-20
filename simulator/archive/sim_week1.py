import asyncio
import time
from pymodbus.datastore import (
    ModbusSlaveContext,
    ModbusSequentialDataBlock,
    ModbusServerContext,
)
from pymodbus.server import StartAsyncTcpServer

HOST, PORT = "0.0.0.0", 5020
COIL, DISCRETE, HOLDING, INPUT = 1, 2, 3, 4 # function-code keys in pymodbus

def block():
    return ModbusSequentialDataBlock(0, [0] * 100)


# zero_mode=True makes client address 0 map to list index 0 (no +1 offset)
store = ModbusSlaveContext(di=block(), co=block(), hr=block(), ir=block(), zero_mode=True)
context = ModbusServerContext(slaves=store, single=True)

async def plant():
    dev = context[0]
    t0 = time.monotonic()
    t_button = t0
    tick = button = heartbeat = level = 0
    last_lamp = None
    while True:
        await asyncio.sleep(0.1)
        tick += 1
        if tick % 5 == 0:
            heartbeat ^= 1
        if tick % 30 == 0:
            button ^= 1
            t_button = time.monotonic()
            print(f"[{t_button - t0:6.1f}s] I_Button -> {button}")
        level = (level + 328) % 32768
        dev.setValues(DISCRETE, 0, [button])
        dev.setValues(DISCRETE, 11, [heartbeat])
        dev.setValues(INPUT, 0, [level])

        lamp = int(dev.getValues(COIL, 0, 1)[0])
        if lamp != last_lamp:
            now = time.monotonic()
            print(f"[{now - t0:6.1f}s] Q_Lamp -> {lamp} "
                    f"({now - t_button:.2f} s after last button change)")
            last_lamp = lamp
        if tick % 10 == 0:
            pump = dev.getValues(HOLDING, 0, 1)[0]
            print(f" level(IR0)={level:5d} pump(HR0)={pump:5d}")


async def main():
    task = asyncio.create_task(plant())
    print(f"Simulator listening on {HOST}:{PORT} (Ctrl+C to stop)")
    await StartAsyncTcpServer(context=context, address=(HOST, PORT))
    await task
if __name__ == "__main__":
    asyncio.run(main())