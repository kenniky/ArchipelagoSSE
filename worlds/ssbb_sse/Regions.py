from BaseClasses import Region
from rule_builder.rules import HasAll
from worlds.AutoWorld import World

from .Common import ORANGE_CUBES, STAGES, SUBSPACE_FIGHTS
from .Items import TABUU_DOOR_DATA_TABLE
from .Locations import (
    LOC_DATA_TABLE,
    SSELocation,
    build_name_from_location_data,
    build_stage_unlock_name,
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
                    data=LOC_DATA_TABLE[build_name_from_location_data(orange_cube_data)],
                )
            )

        # Stage clear location
        level_completion_name = build_stage_unlock_name(stage.name)
        level_completion_location = SSELocation(player, parent=level, data=LOC_DATA_TABLE[level_completion_name])

        if stage.name == "The Great Maze":
            level_completion_location.place_locked_item(world.create_item("Defeat Tabuu"))
            world.set_rule(level_completion_location, HasAll(*TABUU_DOOR_DATA_TABLE.keys()))

            for subspace_fight_data in SUBSPACE_FIGHTS:
                level.locations.append(
                    SSELocation(
                        player,
                        parent=level,
                        data=LOC_DATA_TABLE[build_name_from_location_data(subspace_fight_data)],
                    )
                )

        level.locations.append(level_completion_location)

        multiworld.regions.append(level)
