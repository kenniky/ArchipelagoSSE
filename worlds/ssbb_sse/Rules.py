# Handles logic
from BaseClasses import MultiWorld
from .Items import STAGE_UNLOCK_SUFFIX
from .Common import STAGES


def set_rules(player: int, multiworld: MultiWorld):
    stage_select = multiworld.get_region("Stage Select", player)

    for stage in STAGES:
        stage_select.connect(
            multiworld.get_region(stage.name, player),
            rule=lambda state: state.has(stage.name + STAGE_UNLOCK_SUFFIX, player),
        )
    
    multiworld.completion_condition[player] = lambda state: state.has("Defeat Tabuu", player=player)
