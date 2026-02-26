from BaseClasses import Region
from worlds.AutoWorld import World
from .Common import STAGES
from .Locations import (
    STAGE_COMPLETION_SUFFIX,
    SSELocation,
    LOC_DATA_TABLE,
)
from .Options import SSEOptions


class SSELevel(Region):
    pass


def create_regions(player: int, world: World, options: SSEOptions):
    multiworld = world.multiworld
    multiworld.regions.append(SSELevel("Stage Select", player, multiworld))

    for stage in STAGES:
        if stage.name in options.stage_disable.value:
            continue

        level = SSELevel(stage.name, player, multiworld)

        # Stage clear locations
        level_completion_location = stage.name + STAGE_COMPLETION_SUFFIX
        level.locations = []

        if stage.name == "The Great Maze":
            great_maze_clear = SSELocation(
                player,
                parent=level,
                data=LOC_DATA_TABLE[level_completion_location],
            )
            great_maze_clear.place_locked_item(world.create_item("Defeat Tabuu"))
            level.locations.append(great_maze_clear)
        else:
            level.locations.append(
                SSELocation(
                    player,
                    parent=level,
                    data=LOC_DATA_TABLE[level_completion_location],
                )
            )

        multiworld.regions.append(level)
