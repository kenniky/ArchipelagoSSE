from dataclasses import dataclass

from Options import OptionSet, PerGameCommonOptions
from .Common import STAGES


class StageDisables(OptionSet):
    """Disables some stages from being played.
    Levels with the same name are referred to with I and II suffixes (e.g. The Wilds I, The Wilds II)
    """

    display_name = "Disabled Stages"
    valid_keys = [
        stage.name
        for stage in STAGES
        if stage not in ["Midair Stadium", "The Great Maze"]
    ]
    default = []


@dataclass
class SSEOptions(PerGameCommonOptions):
    stage_disable: StageDisables
