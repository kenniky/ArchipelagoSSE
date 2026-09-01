import asyncio
import logging
import math
import threading
import time
import traceback
from enum import Enum, auto
from pathlib import Path
from typing import Any

import dolphin_memory_engine

from CommonClient import (
    ClientCommandProcessor,
    CommonContext,
    get_base_parser,
    gui_enabled,
    logger,
    server_loop,
)
from NetUtils import ClientStatus
from Utils import async_start, init_logging
from worlds.ssbb_sse.SD import create_sd

from .Common import GAME_NAME, STAGES, SUBSPACE_FIGHTS, get_map_order
from .Items import ITEM_DATA_TABLE, ITEM_REVERSE_LOOKUP, SSEItemType
from .Locations import LOC_DATA_TABLE, LocationType

SERVERLESS_TESTING = False

CONNECTION_REFUSED_GAME_STATUS = (
    "Dolphin failed to connect. Please load an NTSC-USA copy of Super Smash Bros. Brawl. Trying again in 5 seconds..."
)
CONNECTION_LOST_STATUS = (
    "Dolphin connection was lost. Please restart your emulator and make sure Super Smash Bros. Brawl is running."
)
CONNECTION_CONNECTED_STATUS = "Dolphin connected successfully."
CONNECTION_INITIAL_STATUS = "Dolphin connection has not been initiated."

WORD_SIZE = 0x00000004

STAGE_DATA_ADDR = 0x9016DE80
STAGE_STATUS_OFFSET = 0x00000004
STAGE_DIFFICULTY_OFFSET = 0x00000008
STAGE_COMPLETION_OFFSET = 0x00000010
STAGE_SPACING = 0x00000014

CURRENT_SEQUENCE_ADDR = 0x805B8BB0
SEQ_SUBSPACE = 0x90FF3D40

SCREEN_ID_ADDR = 0x90FF3D48

TRIGGER_BASE_ADDR = 0x8049ED34
TRIGGER_MANAGER_REF_ADDR = 0x80B8A698

SCENE_MANAGER_REF_ADDR = 0x805A0060

debug_output = False


class StageDataEnum(Enum):
    AVAILABILITY = auto()
    STATUS = auto()
    DIFFICULTY = auto()
    COMPLETION = auto()


class SSECommandProcessor(ClientCommandProcessor):
    def __init__(self, ctx: CommonContext):
        super().__init__(ctx)

    def _cmd_dolphin(self) -> None:
        """
        Display the current Dolphin emulator connection status.
        """
        if isinstance(self.ctx, SSEContext):
            logger.info(f"Dolphin Status: {self.ctx.dolphin_status}")

    # def _cmd_debug_items(self) -> None:
    #     if isinstance(self.ctx, SSEContext):
    #         logger.info(self.ctx.last_item_idx)
    #         logger.info(self.ctx.unlocked_stages)
    #         logger.info(self.ctx.items_received)

    def _cmd_create_sd(self) -> None:
        """
        Create the SD card that will apply the mod to Brawl.
        See the setup guide for more info.
        """
        if isinstance(self.ctx, SSEContext):
            thread = threading.Thread(target=create_sd, args=(self.ctx,))

            thread.start()

    def _cmd_tabuu_door_progress(self) -> None:
        """
        Print out the progression to opening Tabuu's door.
        """
        found_trophies = len(self.ctx.found_triggers)
        total_trophies = len(SUBSPACE_FIGHTS)

        logger.info(f"You have received {found_trophies} of {total_trophies} total door trophies.")

        needed_pct = self.ctx.slot_data.get("tabuu_trophies_needed", None)

        if needed_pct is None:
            logger.info("Unknown % of trophies needed to progress, check that you're connected")
        else:
            needed = self.ctx.slot_data.get("tabuu_trophies_needed", 100) / 100 * len(SUBSPACE_FIGHTS)
            logger.info(f"You need {needed_pct}% ({math.ceil(needed)}) of the total trophies to be able to fight Tabuu")

    def _cmd_toggle_debug(self) -> None:
        """
        Run this command to enable/disable debug output.
        Debug output can be sent into the Discord channel to assist in fixing bugs
        """
        global debug_output  # noqa: PLW0603
        debug_output = not debug_output

        if debug_output:
            logger.addHandler(self.ctx.debug_handler)
            logger.info(f"debug logs can be found at {self.ctx.debug_file!s}")
        else:
            logger.removeHandler(self.ctx.debug_handler)
            logger.info("debugging turned off")

    # def _cmd_debug_check_in_subspace(self) -> None:
    #     logger.info(f"{CURRENT_SEQUENCE_ADDR:08x}")
    #     logger.info(in_subspace())

    # def _cmd_debug_output(self) -> None:
    #     """
    #     If your client sends a bunch of checks for no reason, run this command.
    #     Copy or screenshot the result into the Discord thread.
    #     """
    #     if not dolphin_memory_engine.is_hooked():
    #         print("not connected to dolphin")

    #     seq = read_word(CURRENT_SEQUENCE_ADDR)
    #     logger.info(format(seq, "04x"))

    #     bytes = read_bytes(seq, 16)
    #     logger.info(format(bytes, "016x"))

    # def _cmd_debug(self) -> None:
    #     logger.info(format(get_subspace_sequence(), "04x"))


class SSEContext(CommonContext):
    command_processor = SSECommandProcessor
    game: str = GAME_NAME

    items_handling: int = 0b111

    slot_data: dict

    def __init__(self, server_address: str | None, password: str | None) -> None:
        """
        Initialize the SSE context.

        :param server_address: Address of the Archipelago server.
        :param password: Password for server authentication.
        """

        super().__init__(server_address, password)
        self.dolphin_sync_task: asyncio.Task[None] | None = None
        self.dolphin_status: str = CONNECTION_INITIAL_STATUS
        self.awaiting_rom: bool = False

        self.last_item_idx: int = 0

        self.counter: int = 0

        self.unlocked_stages: set[int] = set()
        self.found_triggers: set[int] = set()

        # TODO: use
        self.has_send_death: bool = False

        self.debug_file = Path(f"sse_debug_{int(time.time())}.txt").resolve()
        self.debug_handler = logging.FileHandler(self.debug_file)
        formatter = logging.Formatter(fmt="%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        self.debug_handler.setFormatter(formatter)

    def on_package(self, cmd, args):
        if cmd == "Connected":
            self.slot_data = args.get("slot_data", {})
            async_start(
                self.send_msgs(
                    [
                        {
                            "cmd": "Get",
                            "keys": [
                                self.data_key_item_idx(),
                                self.data_key_stages(),
                                self.data_key_triggers(),
                            ],
                        }
                    ]
                ),
                name="get_data",
            )
        elif cmd == "Retrieved":
            self.last_item_idx = args["keys"].get(self.data_key_item_idx(), None)
            if args["keys"].get(self.data_key_stages(), []) is not None:
                self.unlocked_stages = set(args["keys"].get(self.data_key_stages(), []))
            else:
                self.unlocked_stages = set()

            if args["keys"].get(self.data_key_triggers(), []) is not None:
                self.found_triggers = set(args["keys"].get(self.data_key_triggers(), []))
            else:
                self.found_triggers = set()

            if self.last_item_idx is None:
                self.last_item_idx = 0
        elif cmd == "ReceivedItems":
            if debug_output:
                logger.debug(args)
            pass

    async def server_auth(self, password_requested: bool = False):
        # logger.info('authing')
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    async def disconnect(self, allow_autoreconnect: bool = False) -> None:
        """
        Disconnect the client from the server and reset game state variables.

        :param allow_autoreconnect: Allow the client to auto-reconnect to the server. Defaults to `False`.

        """
        self.auth = None
        await super().disconnect(allow_autoreconnect)

    def on_deathlink(self, data: dict[str, Any]) -> None:
        """
        Handle a DeathLink event.

        :param data: The data associated with the DeathLink event.
        """
        super().on_deathlink(data)
        # TODO: implement

    def data_key_item_idx(self):
        return f"item_idx_{self.auth}"

    def data_key_stages(self):
        return f"stages_{self.auth}"

    def data_key_triggers(self):
        return f"triggers_{self.auth}"

    def dump_data(self):
        return {
            self.data_key_item_idx(): self.last_item_idx,
            self.data_key_stages(): self.unlocked_stages.copy(),
            self.data_key_triggers: self.found_triggers.copy(),
        }


def get_reference(reference: int):
    return read_word(reference)


def bit_mask(bit_num: int):
    # 1 indexed
    return 0b1 << (8 - bit_num)


def read_byte(console_address: int) -> int:
    """
    Read a byte from Dolphin memory.

    :param console_address: Address to read from.
    :return: The value read from memory.
    """
    return dolphin_memory_engine.read_byte(console_address)


def write_byte(console_address: int, hex_str: str) -> None:
    """
    Write a byte to Dolphin memory.

    :param console_address: Address to write to.
    :param value: Value to write.
    """
    dolphin_memory_engine.write_byte(console_address, int(hex_str, 16))


def read_bytes(console_address: int, num: int) -> int:
    """
    Read bytes from Dolphin memory.

    :param console_address: Address to read from.
    :param num: number of bytes to read
    :return: The value read from memory.
    """
    return int.from_bytes(dolphin_memory_engine.read_bytes(console_address, num))


def write_bytes(console_address: int, hex_str: str) -> None:
    """
    Write some bytes to Dolphin memory.

    :param console_address: Address to write to.
    :param value: Value to write.
    """
    dolphin_memory_engine.write_bytes(console_address, bytes.fromhex(hex_str))


def read_word(console_address: int) -> int:
    """
    Read a string from Dolphin memory.

    :param console_address: Address to start reading from.
    :param strlen: Length of the string to read.
    :return: The string.
    """
    return read_bytes(console_address, WORD_SIZE)


def read_string(console_address: int, strlen: int) -> str:
    """
    Read a string from Dolphin memory.

    :param console_address: Address to start reading from.
    :param strlen: Length of the string to read.
    :return: The string.
    """
    return dolphin_memory_engine.read_bytes(console_address, strlen).split(b"\0", 1)[0].decode()


def read_bit(console_address: str, bit_number: int) -> bool:
    byte = read_byte(int(console_address, 16))
    bitmask = bit_mask(bit_number)

    return byte & bitmask != 0


def read_global_trigger(trigger_id: int) -> bool:
    word_offset = trigger_id // 32
    bit_offset = trigger_id % 32

    word = read_word(get_reference(TRIGGER_BASE_ADDR) + WORD_SIZE * word_offset)
    bit_mask = 1 << bit_offset
    return word & bit_mask != 0


async def set_global_trigger(trigger_id: int):
    # set in trigger database

    word_offset = trigger_id // 32
    bit_offset = trigger_id % 32

    trigger_addr = get_reference(TRIGGER_BASE_ADDR) + WORD_SIZE * word_offset

    word = read_word(trigger_addr)
    bit_mask = 1 << bit_offset
    new_word = word | bit_mask

    if new_word != word:
        if debug_output:
            logger.debug(
                f"setting trigger {trigger_id} at address {trigger_addr:08x}, changed from {word:08x} to {new_word:08x}"
            )

        write_bytes(
            trigger_addr,
            format(new_word, "08x"),
        )

    # set in trigger manager
    curr_screen = read_word(SCREEN_ID_ADDR)
    if curr_screen in [0x0D, 0x10, 0x15, 0x18, 0x1B]:
        trigger_manager_addr = read_word(TRIGGER_MANAGER_REF_ADDR)
        next_trigger = read_word(trigger_manager_addr + 0x40)

        while next_trigger != 0x0:
            curr_trigger = read_word(next_trigger + 0x0C)
            if curr_trigger == trigger_id:
                write_byte(next_trigger + 0x2C, "01")
                break

            next_trigger = read_word(next_trigger)


def get_stage_data_addr(stage: str | int, data: StageDataEnum) -> int:
    if isinstance(stage, str):
        stage = get_map_order(stage)

    offset = 0x0
    if data == StageDataEnum.STATUS:
        offset = STAGE_STATUS_OFFSET
    elif data == StageDataEnum.DIFFICULTY:
        offset = STAGE_DIFFICULTY_OFFSET
    elif data == StageDataEnum.COMPLETION:
        offset = STAGE_COMPLETION_OFFSET

    return STAGE_DATA_ADDR + stage * STAGE_SPACING + offset


def get_subspace_sequence() -> int:
    # kind of just copies internal logic. Not sure if there's a better way
    scene_manager_addr = get_reference(SCENE_MANAGER_REF_ADDR)

    num_scenes = read_word(scene_manager_addr + 0x274)

    sequence_list = scene_manager_addr + 0x1A8

    for i in range(num_scenes):
        sequence_addr = get_reference(sequence_list + 0x4 * i)
        sequence_name_addr = get_reference(sequence_addr)

        sequence_name = read_string(sequence_name_addr, 11)
        if sequence_name == "sqAdventure":
            return sequence_addr

    return 0x0


def in_subspace() -> bool:
    try:
        curr_seq = read_word(CURRENT_SEQUENCE_ADDR)

        if curr_seq != SEQ_SUBSPACE:
            return False

        screen_id = read_word(SCREEN_ID_ADDR)

        return screen_id > 0x06 and screen_id < 0x1E
    except Exception as e:
        if debug_output:
            logger.debug("failed to check if in subspace")
            logger.debug(str(e))
        return False


async def check_locations(ctx: SSEContext) -> None:
    if not in_subspace():
        return

    for loc in LOC_DATA_TABLE.values():
        checked = False

        if loc.location_type == LocationType.STAGE_COMPLETION:
            completion_status = read_word(
                get_stage_data_addr(loc.other_info["map_order"], StageDataEnum.STATUS),
            )
            if completion_status in (0x0003, 0x0004):
                checked = True

        if loc.location_type in [LocationType.ORANGE_CUBE, LocationType.SUBSPACE_FIGHT]:
            if read_global_trigger(loc.other_info["trigger_id"]):
                checked = True

        # others to be implemented

        if checked:
            if loc.name == "The Great Maze Completion":
                if not ctx.finished_game:
                    await ctx.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])
                    ctx.finished_game = True
            if loc.code is not None:
                ctx.locations_checked.add(loc.code)

    locations_checked = ctx.locations_checked.difference(ctx.checked_locations)
    if locations_checked:
        await ctx.send_msgs([{"cmd": "LocationChecks", "locations": locations_checked}])


async def give_items(ctx: SSEContext) -> None:
    ctx.counter += 1

    if ctx.last_item_idx is None:
        if debug_output:
            logger.debug("last item idx got set to None")
        ctx.last_item_idx = 0

    original_values = ctx.dump_data()

    for idx, item in enumerate(ctx.items_received):
        item_data = ITEM_DATA_TABLE[ITEM_REVERSE_LOOKUP[item.item]]

        if item_data.type == SSEItemType.STAGE_UNLOCK:
            if debug_output and item_data.other_info["map_order"] not in ctx.unlocked_stages:
                logger.debug(f"unlocking stage {item_data.other_info['map_order']}: {item_data.other_info['name']}")
            ctx.unlocked_stages.add(item_data.other_info["map_order"])

        if item_data.type == SSEItemType.STICKER:
            # don't send these multiple times
            if idx < ctx.last_item_idx:
                continue

            if debug_output:
                logger.debug(f"sending sticker {item_data.other_info['byte']}")
            byte_addr = int(item_data.other_info["byte"], 16)
            curr_value = read_bytes(byte_addr, 2)

            curr_value += 1
            curr_value |= 0x8000

            write_bytes(byte_addr, format(curr_value, "04x"))

        if item_data.type == SSEItemType.TABUU_DOOR:
            # print(f"received door item {item_data}")
            if debug_output and item_data.other_info["trigger_id"] not in ctx.found_triggers:
                logger.debug(f"setting tabuu door id {item_data.other_info['trigger_id']}")
            ctx.found_triggers.add(item_data.other_info["trigger_id"])

            if len(ctx.found_triggers) >= ctx.slot_data.get("tabuu_trophies_needed", 100) / 100 * len(SUBSPACE_FIGHTS):
                if debug_output and len(ctx.found_triggers) < len(SUBSPACE_FIGHTS):
                    logger.debug("passed threshold, setting all tabuu doors")
                for fight_data in SUBSPACE_FIGHTS:
                    ctx.found_triggers.add(fight_data.item_trigger_id)

    ctx.last_item_idx = len(ctx.items_received)

    await set_found_triggers(ctx)

    # Persistent storage
    if ctx.counter > 100 or ctx.dump_data() != original_values:
        # Fire every 10 seconds, or if data has changed
        ctx.counter = 0

        # update server data
        await ctx.send_msgs(
            [
                {
                    "cmd": "Set",
                    "key": ctx.data_key_item_idx(),
                    "default": 0,
                    "want_reply": True,
                    "operations": [{"operation": "replace", "value": ctx.last_item_idx}],
                },
                {
                    "cmd": "Set",
                    "key": ctx.data_key_stages(),
                    "default": [],
                    "want_reply": True,
                    "operations": [
                        {
                            "operation": "replace",
                            "value": list(ctx.unlocked_stages),
                        }
                    ],
                },
                {
                    "cmd": "Set",
                    "key": ctx.data_key_triggers(),
                    "default": [],
                    "want_reply": True,
                    "operations": [
                        {
                            "operation": "replace",
                            "value": list(ctx.found_triggers),
                        }
                    ],
                },
            ]
        )


async def update_stage_unlocks(ctx: SSEContext) -> None:
    # needs to be constantly fired
    if not in_subspace():
        return

    # disable character get notifications
    write_byte(0x9016E546, "F0")
    write_byte(0x9016E545, "FF")
    write_byte(0x9016E544, "FF")
    write_byte(0x9016E54B, "FF")
    write_byte(0x9016E54A, "FF")

    for stage_data in STAGES:
        availability_addr = get_stage_data_addr(stage_data.map_order, StageDataEnum.AVAILABILITY)
        status_addr = get_stage_data_addr(stage_data.map_order, StageDataEnum.STATUS)
        if stage_data.map_order in ctx.unlocked_stages:
            # print(availability_addr)
            # stage is unlocked
            write_bytes(availability_addr, "00000000")
            if read_word(status_addr) == 0x00000000:
                write_bytes(status_addr, "00000001")

            # Patch PT in the Ruins, if not encountered yet
            if stage_data.name == "The Ruins":
                pt_byte = read_byte(0x90172740)
                if pt_byte == 0x0:
                    write_byte(0x90172740, "88")
        else:
            # stage is not unlocked
            write_bytes(availability_addr, "00000001")


async def set_found_triggers(ctx: SSEContext) -> None:
    if not in_subspace():
        return

    addresses = {}

    for trigger in ctx.found_triggers:
        word_offset = trigger // 32
        bit_offset = trigger % 32

        word_address = get_reference(TRIGGER_BASE_ADDR) + WORD_SIZE * word_offset

        if word_address not in addresses:
            addresses[word_address] = read_word(word_address)

        addresses[word_address] |= 1 << bit_offset

        # set in trigger manager
        curr_screen = read_word(SCREEN_ID_ADDR)
        if curr_screen in [0x0D, 0x10, 0x15, 0x18, 0x1B]:
            trigger_manager_addr = read_word(TRIGGER_MANAGER_REF_ADDR)
            next_trigger = read_word(trigger_manager_addr + 0x40)

            while next_trigger != 0x0:
                curr_trigger = read_word(next_trigger + 0x0C)
                if curr_trigger == trigger:
                    write_byte(next_trigger + 0x2C, "01")
                    break

                next_trigger = read_word(next_trigger)

    for address, val in addresses.items():
        write_bytes(address, format(val, "08x"))


async def dolphin_sync_task(ctx: SSEContext) -> None:
    """
    The task loop for managing the connection to Dolphin.

    While connected, read the emulator's memory to look for any relevant changes made by the player in the game.

    :param ctx: The Subspace Emissary client context.
    """
    logger.info("Starting Dolphin connector. Use /dolphin for status information.")
    sleep_time = 0.0
    while not ctx.exit_event.is_set():
        if sleep_time > 0.0:
            try:
                # ctx.watcher_event gets set when receiving ReceivedItems or LocationInfo, or when shutting down.
                await asyncio.wait_for(ctx.watcher_event.wait(), sleep_time)
            except TimeoutError:
                pass
            sleep_time = 0.0
        ctx.watcher_event.clear()

        try:
            if not SERVERLESS_TESTING and ctx.slot is None:
                sleep_time = 1.0
                continue
                # await ctx.server_auth()
            if dolphin_memory_engine.is_hooked() and ctx.dolphin_status == CONNECTION_CONNECTED_STATUS:
                if SERVERLESS_TESTING:
                    sleep_time = 10000
                    continue
                if not in_subspace():
                    # do nothing
                    sleep_time = 0.1
                    continue
                if ctx.slot is not None:
                    # connected to the server
                    await give_items(ctx)
                    await check_locations(ctx)
                    await update_stage_unlocks(ctx)
                sleep_time = 0.1
            else:
                if ctx.dolphin_status == CONNECTION_CONNECTED_STATUS:
                    logger.info("Connection to Dolphin lost, reconnecting...")
                    ctx.dolphin_status = CONNECTION_LOST_STATUS
                logger.info("Attempting to connect to Dolphin...")
                dolphin_memory_engine.hook()
                if dolphin_memory_engine.is_hooked():
                    if dolphin_memory_engine.read_bytes(0x80000000, 6) != b"RSBE01":
                        logger.info(CONNECTION_REFUSED_GAME_STATUS)
                        ctx.dolphin_status = CONNECTION_REFUSED_GAME_STATUS
                        dolphin_memory_engine.un_hook()
                        sleep_time = 5
                    else:
                        logger.info(CONNECTION_CONNECTED_STATUS)
                        ctx.dolphin_status = CONNECTION_CONNECTED_STATUS
                        ctx.locations_checked = set()
                else:
                    logger.info("Connection to Dolphin failed, attempting again in 5 seconds...")
                    ctx.dolphin_status = CONNECTION_LOST_STATUS
                    await ctx.disconnect()
                    sleep_time = 5
                    continue
        except Exception:
            dolphin_memory_engine.un_hook()
            logger.info("Connection to Dolphin failed, attempting again in 5 seconds...")
            logger.error(traceback.format_exc())
            ctx.dolphin_status = CONNECTION_LOST_STATUS
            await ctx.disconnect()
            sleep_time = 5
            continue


def background_updating() -> None:
    global SEQ_SUBSPACE  # noqa: PLW0603

    while True:
        time.sleep(10)

        if not dolphin_memory_engine.is_hooked():
            continue

        new_sequence = get_subspace_sequence()

        if SEQ_SUBSPACE != new_sequence:
            if debug_output:
                logger.debug(f"updating subspace sequence from {SEQ_SUBSPACE:08x} to {new_sequence:08x}")

            SEQ_SUBSPACE = new_sequence


def main(*args: str) -> None:
    init_logging("The Subspace Emissary Client")

    async def _main(connect: str | None, password: str | None) -> None:
        ctx = SSEContext(connect, password)
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="ServerLoop")
        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()
        await asyncio.sleep(1)

        ctx.dolphin_sync_task = asyncio.create_task(dolphin_sync_task(ctx), name="DolphinSync")

        await ctx.exit_event.wait()
        # Wake the sync task, if it is currently sleeping, so it can start shutting down when it sees that the
        # exit_event is set.
        ctx.watcher_event.set()
        ctx.server_address = None

        await ctx.shutdown()

        if ctx.dolphin_sync_task:
            await ctx.dolphin_sync_task

    parser = get_base_parser()
    parsed_args = parser.parse_args(args)

    import colorama

    colorama.init()
    asyncio.run(_main(parsed_args.connect, parsed_args.password))
    colorama.deinit()
