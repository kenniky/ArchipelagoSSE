import traceback
from CommonClient import (
    ClientCommandProcessor,
    CommonContext,
    get_base_parser,
    logger,
    server_loop,
    gui_enabled,
)
from typing import Optional, Any
import asyncio
from enum import Enum, auto

from NetUtils import ClientStatus
import Utils
from .Locations import LOC_DATA_TABLE, LocationType
from .Common import GAME_NAME, STAGES, get_map_order
from .Items import ITEM_DATA_TABLE, SSEItemType, ITEM_REVERSE_LOOKUP
import dolphin_memory_engine

CONNECTION_REFUSED_GAME_STATUS = "Dolphin failed to connect. Please load Super Smash Bros. Brawl. Trying again in 5 seconds..."
CONNECTION_LOST_STATUS = "Dolphin connection was lost. Please restart your emulator and make sure Super Smash Bros. Brawl is running."
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


class SSEContext(CommonContext):
    command_processor = SSECommandProcessor
    game: str = GAME_NAME

    items_handling: int = 0b111

    def __init__(self, server_address: Optional[str], password: Optional[str]) -> None:
        """
        Initialize the SSE context.

        :param server_address: Address of the Archipelago server.
        :param password: Password for server authentication.
        """

        super().__init__(server_address, password)
        self.dolphin_sync_task: Optional[asyncio.Task[None]] = None
        self.dolphin_status: str = CONNECTION_INITIAL_STATUS
        self.awaiting_rom: bool = False

        self.unlocked_stages: set[int] = set()

        # TODO: use
        self.has_send_death: bool = False

        # Name of the current stage as read from the game's memory. Sent to trackers whenever its value changes to
        # facilitate automatically switching to the map of the current stage.
        self.current_stage_name: str = ""

        # Set of visited stages. A dictionary (used as a set) of all visited stages is set in the server's data storage
        # and updated when the player visits a new stage for the first time. To track which stages are new and need to
        # cause the server's data storage to update, the TWW AP Client keeps track of the visited stages in a set.
        # Trackers can request the dictionary from data storage to see which stages the player has visited.
        # It starts as `None` until it has been read from the server.
        self.visited_stage_names: Optional[set[str]] = None

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
        self.current_stage_name = ""
        self.visited_stage_names = None
        await super().disconnect(allow_autoreconnect)

    def on_deathlink(self, data: dict[str, Any]) -> None:
        """
        Handle a DeathLink event.

        :param data: The data associated with the DeathLink event.
        """
        super().on_deathlink(data)
        # TODO: implement


def read_byte(console_address: int) -> int:
    """
    Read a byte from Dolphin memory.

    :param console_address: Address to read from.
    :return: The value read from memory.
    """
    return int.from_bytes(dolphin_memory_engine.read_byte(console_address))


def write_byte(console_address: int, hex_str: str) -> None:
    """
    Write a byte to Dolphin memory.

    :param console_address: Address to write to.
    :param value: Value to write.
    """
    dolphin_memory_engine.write_byte(console_address, hex_str)


def read_word(console_address: int) -> int:
    """
    Read a word (4 bytes) from Dolphin memory.

    :param console_address: Address to read from.
    :return: The value read from memory.
    """
    return int.from_bytes(dolphin_memory_engine.read_bytes(console_address, WORD_SIZE))


def write_word(console_address: int, hex_str: str) -> None:
    """
    Write a word (4 bytes) to Dolphin memory.

    :param console_address: Address to write to.
    :param value: Value to write.
    """
    dolphin_memory_engine.write_bytes(console_address, bytes.fromhex(hex_str))


def read_string(console_address: int, strlen: int) -> str:
    """
    Read a string from Dolphin memory.

    :param console_address: Address to start reading from.
    :param strlen: Length of the string to read.
    :return: The string.
    """
    return (
        dolphin_memory_engine.read_bytes(console_address, strlen)
        .split(b"\0", 1)[0]
        .decode()
    )


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


def in_subspace() -> bool:
    curr_seq = read_word(CURRENT_SEQUENCE_ADDR)

    return curr_seq == SEQ_SUBSPACE


async def check_locations(ctx: SSEContext) -> None:
    if not in_subspace():
        return
    for loc in LOC_DATA_TABLE.values():
        checked = False

        if loc.location_type == LocationType.STAGE_COMPLETION:
            completion_status = read_word(
                get_stage_data_addr(loc.other_info["map_order"], StageDataEnum.STATUS)
            )
            if completion_status in (0x0003, 0x0004):
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
    for item in ctx.items_received:
        item_data = ITEM_DATA_TABLE[ITEM_REVERSE_LOOKUP[item.item]]

        if item_data.type == SSEItemType.STAGE_UNLOCK:
            ctx.unlocked_stages.add(item_data.other_info["map_order"])


async def update_stage_unlocks(ctx: SSEContext) -> None:
    if not in_subspace():
        return

    for stage_data in STAGES:
        availability_addr = get_stage_data_addr(
            stage_data.map_order, StageDataEnum.AVAILABILITY
        )
        status_addr = get_stage_data_addr(stage_data.map_order, StageDataEnum.STATUS)
        if stage_data.map_order in ctx.unlocked_stages:
            # print(availability_addr)
            # stage is unlocked
            write_word(availability_addr, '00000000')
            if read_word(status_addr) == 0x00000000:
                write_word(status_addr, '00000001')
        else:
            # stage is not unlocked
            write_word(availability_addr, '00000001')


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
            except asyncio.TimeoutError:
                pass
            sleep_time = 0.0
        ctx.watcher_event.clear()

        try:
            if (
                dolphin_memory_engine.is_hooked()
                and ctx.dolphin_status == CONNECTION_CONNECTED_STATUS
            ):
                if not in_subspace():
                    # do nothing
                    sleep_time = 0.1
                    continue
                if ctx.slot is not None:
                    # connected to the server
                    await give_items(ctx)
                    await check_locations(ctx)
                    await update_stage_unlocks(ctx)
                else:
                    await ctx.server_auth()
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
                    logger.info(
                        "Connection to Dolphin failed, attempting again in 5 seconds..."
                    )
                    ctx.dolphin_status = CONNECTION_LOST_STATUS
                    await ctx.disconnect()
                    sleep_time = 5
                    continue
        except Exception:
            dolphin_memory_engine.un_hook()
            logger.info(
                "Connection to Dolphin failed, attempting again in 5 seconds..."
            )
            logger.error(traceback.format_exc())
            ctx.dolphin_status = CONNECTION_LOST_STATUS
            await ctx.disconnect()
            sleep_time = 5
            continue


def main(*args: str) -> None:
    Utils.init_logging("The Subspace Emissary Client")

    async def _main(connect: Optional[str], password: Optional[str]) -> None:
        ctx = SSEContext(connect, password)
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="ServerLoop")
        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()
        await asyncio.sleep(1)

        ctx.dolphin_sync_task = asyncio.create_task(
            dolphin_sync_task(ctx), name="DolphinSync"
        )

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
