from dataclasses import dataclass

from Options import OptionSet, PerGameCommonOptions
from .Common import STAGES


class StageDisables(OptionSet):
    """Disables some stages from being played.
    Note that The Ruins is currently unstable due to the logic surrounding Pokemon Trainer.
    Levels with the same name are referred to with I and II suffixes (e.g. The Wilds I, The Wilds II)
    """

    display_name = "Disabled Stages"
    valid_keys = [
        stage.name
        for stage in STAGES
        if stage not in ["Midair Stadium", "The Great Maze"]
    ]
    default = ["The Ruins"]


@dataclass
class SSEOptions(PerGameCommonOptions):
    stage_disable: StageDisables
