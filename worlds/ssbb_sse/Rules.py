# Handles logic
from BaseClasses import MultiWorld
from .Items import STAGE_UNLOCK_SUFFIX
from .Common import STAGES
from .Options import SSEOptions


def set_rules(player: int, multiworld: MultiWorld, options: SSEOptions):
    stage_select = multiworld.get_region("Stage Select", player)

    for stage in STAGES:
        if stage.name in options.stage_disable.value:
            continue
        def entrance_cond(state, stage):
            return state.has(stage.name + STAGE_UNLOCK_SUFFIX, player)

        stage_select.connect(
            multiworld.get_region(stage.name, player),
            rule=lambda state, st=stage: entrance_cond(state, st),
        )
    
    multiworld.completion_condition[player] = lambda state: state.has("Defeat Tabuu", player=player)
