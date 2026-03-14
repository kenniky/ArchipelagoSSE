from typing import ClassVar, FrozenSet
from BaseClasses import Tutorial
from worlds.AutoWorld import World, WebWorld
from .Common import GAME_NAME, STICKERS
from .Items import (
    ITEM_TABLE,
    ITEM_DATA_TABLE,
    SSEItem,
    populate_item_groups,
    populate_items,
    build_sticker_name,
)
from .Locations import LOCATION_TABLE
from .Regions import create_regions
from .Rules import set_rules
from .Options import SSEOptions
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

    options_dataclass = SSEOptions
    options: SSEOptions

    item_name_to_id: ClassVar[dict[str, int]] = ITEM_TABLE
    location_name_to_id: ClassVar[dict[str, int]] = LOCATION_TABLE

    origin_region_name: str = "Stage Select"
    hint_blacklist: ClassVar[FrozenSet[str]] = frozenset(["Filler Placeholder"])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        populate_item_groups(self)

    def generate_early(self):
        # placeholder
        return super().generate_early()

    def create_regions(self) -> None:
        # Specific enabled/disabled logic goes here
        create_regions(self.player, self, self.options)

    def create_items(self) -> None:
        populate_items(self)

    def set_rules(self) -> None:
        set_rules(self.player, self.multiworld, self.options)

    def create_item(self, name: str):
        data = ITEM_DATA_TABLE[name]
        item = SSEItem(name, self.player, data)

        return item

    def get_filler_item_name(self):
        sticker_idx = self.random.randrange(len(STICKERS))
        sticker_data = STICKERS[sticker_idx]
        return build_sticker_name(sticker_data)
