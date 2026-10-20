
import asyncio
from pymodbus.client import AsyncModbusTcpClient


async def main():
    client = AsyncModbusTcpClient("127.0.0.1", port=5020)

    try:
        connected = await client.connect()
        if not connected:
            print("Could not connect. Is sim.py running?")
            return

        # Read 13 discrete inputs, starting at address 0
        result = await client.read_discrete_inputs(
            address=0, count=13, device_id=1
        )
        if result.isError():
            print("Discrete-input read failed:", result)
        else:
            print("Discrete inputs:", [
                int(v) for v in result.bits[:13]
            ])

        # Read two input registers, starting at address 0
        result = await client.read_input_registers(
            address=0, count=2, device_id=1
        )
        if result.isError():
            print("Input-register read failed:", result)
        else:
            print("Input registers:", result.registers)

        # Turn conveyor coil 0 on, then off
        result = await client.write_coil(
            address=0, value=True, device_id=1
        )
        print("Conveyor ON write:", result)

        await asyncio.sleep(1.0)

        result = await client.write_coil(
            address=0, value=False, device_id=1
        )
        print("Conveyor OFF write:", result)

    finally:
        client.close()


asyncio.run(main())