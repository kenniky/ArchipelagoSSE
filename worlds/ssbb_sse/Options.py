from dataclasses import dataclass

from Options import PerGameCommonOptions, Range


class TabuuTrophiesNeeded(Range):
    """Sets the percentage of trophies needed to unlock Tabuu's door."""

    display_name = "Tabuu Door Trophies Completion"
    range_start = 0
    range_end = 100
    default = 40


@dataclass
class SSEOptions(PerGameCommonOptions):
    tabuu_trophies_needed: TabuuTrophiesNeeded
