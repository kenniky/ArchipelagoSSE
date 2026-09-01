# Handles logic
from rule_builder.rules import Has
from worlds.AutoWorld import World

from .Common import STAGES
from .Items import STAGE_UNLOCK_PREFIX
from .Options import SSEOptions


# Rules apply even if the checks aren't included!
def set_rules(player: int, world: World, options: SSEOptions):
    multiworld = world.multiworld
    stage_select = multiworld.get_region("Stage Select", player)

    for stage in STAGES:
        stage_region = multiworld.get_region(stage.name, player)

        world.create_entrance(stage_select, stage_region, Has(STAGE_UNLOCK_PREFIX + stage.name))

    world.set_completion_rule(Has("Defeat Tabuu"))
