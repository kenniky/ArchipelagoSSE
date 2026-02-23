from typing import ClassVar, FrozenSet
from BaseClasses import Tutorial
from worlds.AutoWorld import World, WebWorld
from .Common import GAME_NAME
from .Items import ITEM_TABLE, ITEM_DATA_TABLE, STAGE_UNLOCK_DATA_TABLE, SSEItem
from .Locations import LOCATION_TABLE
from .Regions import create_regions
from .Rules import set_rules
from worlds.LauncherComponents import components, Component, Type, launch

def run_client(*args: str) -> None:
    """
    Launch the Subspace Emissary client.

    :param *args: Variable length argument list passed to the client.
    """
    print("Running Subspace Emissary Client")
    from .Client import main

    launch(main, name="SubspaceEmissaryClient", args=args)


components.append(
    Component(
        display_name="Subspace Emissary Client",
        func=run_client,
        component_type=Type.CLIENT,
    )
)


class SubspaceWeb(WebWorld):
    tutorials = [
        Tutorial(
            "Subspace Archipelago Setup Guide",
            "A guide to setting up the Super Smash Bros. Brawl Subspace Emissary randomizer for Archipelago",
            "English",
            "en_SubspaceEmissary_Setup.md",
            link="placeholder",
            authors=["kenniky"],
        )
    ]


class SubspaceWorld(World):
    """the subspace emissary"""

    game: ClassVar[str] = GAME_NAME
    topology_present = False  # Allows for location guides. implement when doors
    web: ClassVar[SubspaceWeb] = SubspaceWeb()

    item_name_to_id: ClassVar[dict[str, int]] = ITEM_TABLE
    location_name_to_id: ClassVar[dict[str, int]] = LOCATION_TABLE

    origin_region_name: str = "Stage Select"
    hint_blacklist: ClassVar[FrozenSet[str]] = frozenset(["Filler Placeholder"])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def generate_early(self):
        # placeholder
        return super().generate_early()

    def create_regions(self) -> None:
        create_regions(self.player, self.multiworld)

    def create_items(self) -> None:
        self.multiworld.itempool += [
            self.create_item(level_unlock)
            for level_unlock in STAGE_UNLOCK_DATA_TABLE.keys()
            if level_unlock != "Midair Stadium Unlock"
        ]

        # Start with a stage
        self.push_precollected(self.create_item("Midair Stadium Unlock"))

    def set_rules(self) -> None:
        set_rules(self.player, self.multiworld)

    def create_item(self, name: str):
        data = ITEM_DATA_TABLE[name]
        item = SSEItem(name, self.player, data)

        return item

    def get_filler_item_name(self):
        return "Filler Placeholder"
