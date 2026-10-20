"""End-to-end check over real Modbus TCP: every I/O list row is exercised."""
import asyncio

from pymodbus.client import AsyncModbusTcpClient

import sim
from iomap import CMD_REG, ARG_REG, CTRL_BASE, COIL, DISCRETE, HOLDING, INPUT, IoMap
from params import Params
from plant import ACTUATOR_TAGS, FAULTS, SENSOR_TAGS, Plant

PORT = 5031


def test_io_list_and_plant_agree():
    io = IoMap(sim.DEFAULT_IOLIST)
    assert io.check(SENSOR_TAGS, ACTUATOR_TAGS) == []
    assert len(io.map) == 24


async def scenario():
    io = IoMap(sim.DEFAULT_IOLIST)
    plant, ctx = Plant(Params(), seed=1), sim.build_context()
    server = asyncio.create_task(sim.StartAsyncTcpServer(context=ctx, address=("127.0.0.1", PORT)))
    loop = asyncio.create_task(sim.plant_loop(plant, io, ctx, sim.EventLog(echo=False)))
    await asyncio.sleep(0.5)
    client = AsyncModbusTcpClient("127.0.0.1", port=PORT)
    await client.connect()

    async def read(tag):
        fc, addr = io.map[tag]
        if fc == DISCRETE:
            return int((await client.read_discrete_inputs(addr, 1, slave=1)).bits[0])
        return (await client.read_input_registers(addr, 1, slave=1)).registers[0]

    async def hr(addr, value):
        await client.write_register(addr, value, slave=1)
        await asyncio.sleep(0.15)

    try:
        # 1. every actuator: write over Modbus, the plant must see it at the listed address
        for tag in sorted(io.actuators):
            fc, addr = io.map[tag]
            if fc == COIL:
                await client.write_coil(addr, True, slave=1)
                await asyncio.sleep(0.12)
                assert plant.last_outputs[tag] is True, tag
                await client.write_coil(addr, False, slave=1)
            else:
                await client.write_register(addr, 1234, slave=1)
                await asyncio.sleep(0.12)
                assert plant.last_outputs[tag] == 1234, tag
                await client.write_register(addr, 0, slave=1)
            await asyncio.sleep(0.12)
        # 2. idle values of every sensor
        idle = {"I_EStop_OK": 1, "I_InfeedPresent": 1, "I_FillPos": 0, "I_CapPos": 0,
                "I_InspectPos": 0, "I_CapPresent": 0, "I_RejectBinFull": 0,
                "I_OutfeedSensor": 0, "I_ConvOL_OK": 1, "I_TankLow_LS": 1,
                "I_TankHigh_LS": 0, "I_ConvRunning": 0}
        for tag, want in idle.items():
            assert await read(tag) == want, tag
        assert 22000 < await read("I_TankLevel_raw") < 23800
        assert await read("I_FillVolume_x10") == 0
        # 3. heartbeat toggles
        seen = set()
        for _ in range(14):
            seen.add(await read("I_Heartbeat"))
            await asyncio.sleep(0.1)
        assert seen == {0, 1}
        # 4. fault registers drive the matching sensors
        for name, tag, want in [("estop", "I_EStop_OK", 0), ("overload", "I_ConvOL_OK", 0),
                                ("infeed_empty", "I_InfeedPresent", 0)]:
            await hr(CTRL_BASE + FAULTS.index(name), 1)
            assert await read(tag) == want, name
            await hr(CTRL_BASE + FAULTS.index(name), 0)
            assert await read(tag) == 1, name
        # 5. run feedback follows the conveyor, and can be forced low
        await client.write_coil(io.map["Q_ConveyorRun"][1], True, slave=1)
        await asyncio.sleep(1.3)
        assert await read("I_ConvRunning") == 1
        await hr(CTRL_BASE + FAULTS.index("runfb_loss"), 1)
        assert await read("I_ConvRunning") == 0
        await hr(CTRL_BASE + FAULTS.index("runfb_loss"), 0)
        await client.write_coil(io.map["Q_ConveyorRun"][1], False, slave=1)
        # 6. command register: tank to 5 % and 97 %
        await hr(CMD_REG + 1, 50)
        await hr(CMD_REG, 1)
        assert await read("I_TankLow_LS") == 0 and await read("I_TankLevel_raw") < 2500
        await hr(CMD_REG + 1, 970)
        await hr(CMD_REG, 1)
        assert await read("I_TankHigh_LS") == 1
        # 7. the command register clears itself
        regs = await client.read_holding_registers(CMD_REG, 2, slave=1)
        assert regs.registers == [0, 0]
    finally:
        client.close()
        for task in (loop, server):
            task.cancel()
        await asyncio.gather(loop, server, return_exceptions=True)


def test_every_io_row_over_modbus():
    asyncio.run(scenario())
