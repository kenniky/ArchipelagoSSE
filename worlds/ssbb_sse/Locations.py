from typing import Optional
from dataclasses import dataclass, field
from BaseClasses import Location, Region
from enum import Enum, auto

from .Common import GAME_NAME, STAGES


class MemoryType(Enum):
    BIT = auto()
    BYTE = auto()
    WORD = auto()
    OTHER = auto()


class LocationType(Enum):
    STAGE_COMPLETION = auto()
    ORANGE_CUBE = auto()
    GREAT_MAZE_FIGHT = auto()


@dataclass
class SSELocationData:
    name: Optional[str] = None
    code: Optional[int] = None

    location_type: Optional[LocationType] = None

    active: bool = True

    other_info: dict = field(default_factory=dict)


class SSELocation(Location):
    game: str = GAME_NAME

    data: Optional[SSELocationData]

    def __init__(
        self,
        player: int,
        parent: Optional[Region] = None,
        data: Optional[SSELocationData] = None,
    ):
        assert data is not None, "location is missing data!"

        super().__init__(player, data.name, data.code, parent)

        self.data = data


STAGE_COMPLETION_OFFSET = 100
ORANGE_BOX_COMPLETION_OFFSET = 200

STAGE_COMPLETION_SUFFIX = " Completion"

STAGE_COMPLETION_LOC_DATA: dict[str, SSELocationData] = {
    stage.name
    + STAGE_COMPLETION_SUFFIX: SSELocationData(
        name=stage.name + STAGE_COMPLETION_SUFFIX,
        code=None if stage.name == "The Great Maze" else stage.map_order + STAGE_COMPLETION_OFFSET,
        location_type=LocationType.STAGE_COMPLETION,
        other_info={"map_order": stage.map_order},
    )
    for stage in STAGES
}

LOC_DATA_TABLE = {**STAGE_COMPLETION_LOC_DATA}

LOCATION_TABLE = {key: val.code for key, val in LOC_DATA_TABLE.items()}
