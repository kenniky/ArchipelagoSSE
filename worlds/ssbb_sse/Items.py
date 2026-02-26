from BaseClasses import Item, ItemClassification as IC
from enum import Enum, auto
from typing import NamedTuple, Optional
from .Common import GAME_NAME, STAGES


class SSEItemType(Enum):
    STAGE_UNLOCK = auto()
    CHARACTER_UNLOCK = auto()


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
        **kwargs
    ) -> None:
        super().__init__(
            name,
            data.classification if classification is None else classification,
            data.code,
            player,
        )

        self.data: SSEItemData = data


STAGE_UNLOCK_OFFSET = 100
CHAR_UNLOCK_OFFSET = 200
MISC_OFFSET = 300

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
}

ITEM_TABLE: dict[str, int] = {
    name: data.code for name, data in ITEM_DATA_TABLE.items()
}

ITEM_REVERSE_LOOKUP: dict[int, str] = {
    code: name for name, code in ITEM_TABLE.items() if code is not None
}
