# Handles logic
from BaseClasses import MultiWorld
from .Items import STAGE_UNLOCK_SUFFIX
from .Common import STAGES


def set_rules(player: int, multiworld: MultiWorld):
    stage_select = multiworld.get_region("Stage Select", player)

    for stage in STAGES:
        def entrance_cond(state, stage):
            return state.has(stage.name + STAGE_UNLOCK_SUFFIX, player)

        stage_select.connect(
            multiworld.get_region(stage.name, player),
            rule=lambda state, st=stage: entrance_cond(state, st),
        )
    
    multiworld.completion_condition[player] = lambda state: state.has("Defeat Tabuu", player=player)
