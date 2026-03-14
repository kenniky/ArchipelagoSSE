from BaseClasses import Region
from worlds.AutoWorld import World
from .Common import STAGES, ORANGE_CUBES
from .Locations import (
    build_name_from_location_data,
    build_stage_unlock_name,
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
        level = SSELevel(stage.name, player, multiworld)
        level.locations = []

        # orange cubes
        for orange_cube_data in ORANGE_CUBES:
            is_correct_stage = orange_cube_data.stage == stage.name
            if stage.name == "The Great Maze":
                is_correct_stage = "The Great Maze" in orange_cube_data.stage

            if not is_correct_stage:
                continue

            level.locations.append(
                SSELocation(
                    player,
                    parent=level,
                    data=LOC_DATA_TABLE[
                        build_name_from_location_data(orange_cube_data)
                    ],
                )
            )

        # Stage clear location
        level_completion_location = build_stage_unlock_name(stage.name)

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
