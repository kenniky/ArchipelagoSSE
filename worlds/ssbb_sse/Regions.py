from BaseClasses import Region
from .Common import STAGES
from .Locations import (
    STAGE_COMPLETION_SUFFIX,
    SSELocation,
    LOC_DATA_TABLE,
)


class SSELevel(Region):
    pass


def create_regions(player: int, world):
    multiworld = world.multiworld
    multiworld.regions.append(Region("Stage Select", player, world))

    for stage in STAGES:
        level = SSELevel(stage.name, player, world)

        # Stage clear locations
        level_completion_location = stage.name + STAGE_COMPLETION_SUFFIX
        level.locations = []

        if stage.name == "The Great Maze":
            great_maze_clear = SSELocation(
                player,
                level_completion_location,
                data=LOC_DATA_TABLE[level_completion_location],
            )
            great_maze_clear.place_locked_item(world.create_item("Defeat Tabuu"))
            level.locations.append(great_maze_clear)
        else:
            level.locations.append(
                SSELocation(
                    player,
                    level_completion_location,
                    data=LOC_DATA_TABLE[level_completion_location],
                )
            )

        multiworld.regions.append(level)
