from typing import NamedTuple

GAME_NAME: str = "Super Smash Bros. Brawl - The Subspace Emissary"


class StageData(NamedTuple):
    name: str
    map_order: int


def get_map_order(stage_name: str) -> int:
    for data in STAGES:
        if stage_name == data.name:
            return data.map_order
    return -1


STAGES: list[StageData] = [
    StageData("Midair Stadium", 0),
    StageData("Skyworld", 1),
    StageData("Sea of Clouds", 2),
    StageData("The Jungle", 3),
    StageData("The Plain", 4),
    StageData("The Lake", 5),
    StageData("The Ruined Zoo", 6),
    StageData("The Battlefield Fortress", 7),
    StageData("The Forest", 8),
    StageData("The Research Facility I", 9),
    StageData("The Lake Shore", 10),
    StageData("The Path to the Ruins", 11),
    StageData("The Cave", 12),
    StageData("The Ruins", 13),
    StageData("The Wilds I", 14),
    StageData("The Ruined Hall", 15),
    StageData("The Wilds II", 16),
    StageData("The Swamp", 17),
    StageData("The Research Facility II", 18),
    StageData("Outside the Ancient Ruins", 19),
    StageData("The Glacial Peak", 20),
    StageData("The Canyon", 21),
    StageData("Battleship Halberd Interior", 22),
    StageData("Battleship Halberd Exterior", 23),
    StageData("Battleship Halberd Bridge", 24),
    StageData("The Subspace Bomb Factory I", 25),
    StageData("The Subspace Bomb Factory II", 26),
    StageData("Entrance to Subspace", 27),
    StageData("Subspace I", 28),
    StageData("Subspace II", 29),
    StageData("The Great Maze", 30),
]
