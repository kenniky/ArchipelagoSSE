from BaseClasses import Item, ItemClassification as IC
from enum import Enum, auto
from typing import Dict, NamedTuple, Optional, Set
from .Common import GAME_NAME, STAGES, STICKERS, StickerData


class SSEItemType(Enum):
    STAGE_UNLOCK = auto()
    CHARACTER_UNLOCK = auto()
    STICKER = auto()


class SSEItemData(NamedTuple):
    classification: IC
    code: Optional[int] = None
    type: Optional[SSEItemType] = None
    other_info: dict = {}


class SSEItem(Item):
    game: str = GAME_NAME

    def __init__(
        self,
        name: str,
        player: int,
        data: SSEItemData,
        classification: Optional[IC] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            name,
            data.classification if classification is None else classification,
            data.code,
            player,
        )

        self.data: SSEItemData = data


def populate_items(subspace_world):
    item_pool = []
    player = subspace_world.player

    # Determine unique items first

    item_pool += [
        subspace_world.create_item(level_unlock)
        for level_unlock in STAGE_UNLOCK_DATA_TABLE.keys()
    ]

    # Start with Midair Stadium
    subspace_world.push_precollected(
        subspace_world.create_item("Midair Stadium Unlock")
    )

    # Remove unique items that are precollected
    for item in subspace_world.multiworld.precollected_items[player]:
        if item in item_pool:
            item_pool.remove(item)

    # create filler items
    total_locs = len(subspace_world.multiworld.get_unfilled_locations(player))
    created_items = len(item_pool)
    needed_items = total_locs - created_items

    for _ in range(needed_items):
        item_pool.append(
            subspace_world.create_item(subspace_world.get_filler_item_name())
        )

    subspace_world.multiworld.itempool.extend(item_pool)


def populate_item_groups(subspace_world):
    item_group_dict: Dict[str, Set[str]] = {}

    item_group_dict["Stage Unlocks"] = STAGE_UNLOCK_DATA_TABLE.keys()

    subspace_world.item_name_groups = item_group_dict


def build_sticker_name(sticker_data: StickerData):
    return f"{sticker_data.name} ({sticker_data.series}) Sticker"


STAGE_UNLOCK_OFFSET = 100
CHAR_UNLOCK_OFFSET = 200
MISC_OFFSET = 300
STICKER_OFFSET = 1000

STAGE_UNLOCK_SUFFIX = " Unlock"

STAGE_UNLOCK_DATA_TABLE: dict[str, SSEItemData] = {
    data.name
    + STAGE_UNLOCK_SUFFIX: SSEItemData(
        classification=IC.progression,
        code=STAGE_UNLOCK_OFFSET + data.map_order,
        type=SSEItemType.STAGE_UNLOCK,
        other_info={"map_order": data.map_order, "name": data.name},
    )
    for data in STAGES
}

CHAR_UNLOCK_DATA_TABLE: dict[str, SSEItemData] = {}

STICKER_DATA_TABLE: dict[str, SSEItemData] = {
    build_sticker_name(data): SSEItemData(
        classification=IC.filler,
        code=STICKER_OFFSET + idx,
        type=SSEItemType.STICKER,
        other_info={"byte": data.byte},
    )
    for idx, data in enumerate(STICKERS)
}

MISC_DATA_TABLE: dict[str, SSEItemData] = {
    "Filler Placeholder": SSEItemData(IC.filler, MISC_OFFSET + 0)
}

# Events, ids should be none
EVENT_DATA_TABLE: dict[str, SSEItemData] = {
    "Defeat Tabuu": SSEItemData(IC.progression, None)
}

ITEM_DATA_TABLE = {
    **STAGE_UNLOCK_DATA_TABLE,
    **CHAR_UNLOCK_DATA_TABLE,
    **MISC_DATA_TABLE,
    **EVENT_DATA_TABLE,
    **STICKER_DATA_TABLE,
}

ITEM_TABLE: dict[str, int] = {name: data.code for name, data in ITEM_DATA_TABLE.items()}

ITEM_REVERSE_LOOKUP: dict[int, str] = {
    code: name for name, code in ITEM_TABLE.items() if code is not None
}
