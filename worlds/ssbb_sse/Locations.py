from typing import Dict, Optional, Set
from dataclasses import dataclass, field
from BaseClasses import Location, Region
from enum import Enum, auto

from .Common import GAME_NAME, STAGES, ORANGE_CUBES, OrangeCubeData, StageData


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


def define_location_groups(subspace_world):
    location_group_dict: Dict[str, Set[str]]

    location_group_dict["Stage Completions"] = STAGE_COMPLETION_LOC_DATA.keys()

    subspace_world.location_name_groups = location_group_dict


def build_stage_unlock_name(stage_name: str):
    return stage_name + " Completion"


def build_orange_cube_name(stage: str, description: str):
    return stage + " - " + description


def build_name_from_location_data(loc_data: StageData | OrangeCubeData):
    if type(loc_data) is StageData:
        return build_stage_unlock_name(loc_data.name)

    if type(loc_data) is OrangeCubeData:
        return build_orange_cube_name(loc_data.stage, loc_data.description)

    return None


STAGE_COMPLETION_OFFSET = 100
ORANGE_CUBE_COMPLETION_OFFSET = 200

STAGE_COMPLETION_LOC_DATA: dict[str, SSELocationData] = {
    build_name_from_location_data(stage): SSELocationData(
        name=build_name_from_location_data(stage),
        code=(
            None
            if stage.name == "The Great Maze"
            else stage.map_order + STAGE_COMPLETION_OFFSET
        ),
        location_type=LocationType.STAGE_COMPLETION,
        other_info={"map_order": stage.map_order},
    )
    for stage in STAGES
}

ORANGE_CUBE_LOC_DATA: dict[str, SSELocationData] = {
    build_name_from_location_data(cube_info): SSELocationData(
        name=build_name_from_location_data(cube_info),
        code=idx + ORANGE_CUBE_COMPLETION_OFFSET,
        location_type=LocationType.ORANGE_CUBE,
        other_info={"byte": cube_info.byte_address, "bit": cube_info.bit},
    )
    for idx, cube_info in enumerate(ORANGE_CUBES)
}

LOC_DATA_TABLE = {**STAGE_COMPLETION_LOC_DATA, **ORANGE_CUBE_LOC_DATA}

LOCATION_TABLE = {key: val.code for key, val in LOC_DATA_TABLE.items()}
