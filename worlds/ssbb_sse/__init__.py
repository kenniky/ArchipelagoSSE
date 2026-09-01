from typing import Any, ClassVar

import settings
from BaseClasses import Tutorial
from worlds.AutoWorld import WebWorld, World
from worlds.LauncherComponents import Component, Type, components, launch

from .Common import GAME_NAME, STICKERS
from .Items import (
    ITEM_DATA_TABLE,
    ITEM_TABLE,
    SSEItem,
    build_sticker_name,
    populate_item_groups,
    populate_items,
)
from .Locations import LOCATION_TABLE
from .Options import SSEOptions
from .Regions import create_regions
from .Rules import set_rules


def run_client(*args: str) -> None:
    """
    Launch the Subspace Emissary client.

    :param *args: Variable length argument list passed to the client.
    """
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
    tutorials: ClassVar = [
        Tutorial(
            "Subspace Archipelago Setup Guide",
            "A guide to setting up the Super Smash Bros. Brawl Subspace Emissary randomizer for Archipelago",
            "English",
            "en_SubspaceEmissary_Setup.md",
            link="placeholder",
            authors=["kenniky"],
        )
    ]


class SubspaceSettings(settings.Group):
    class DolphinTool(settings.UserFilePath):
        required = True
        is_exe = True
        description = "Dolphin tool exe"

    class BrawlIso(settings.UserFilePath):
        required = True
        description = "SSBB NTSC USA iso file"
        md5_hashes: ClassVar = ["52ce7160ced2505ad5e397477d0ea4fe", "d18726e6dfdc8bdbdad540b561051087"]

    dolphin_tool: DolphinTool = DolphinTool("DolphinTool.exe")
    brawl_iso: BrawlIso = BrawlIso("Super Smash Bros. Brawl (USA).iso")


class SubspaceWorld(World):
    """the subspace emissary"""

    game: ClassVar[str] = GAME_NAME
    topology_present = False  # Allows for location guides. implement when doors
    web: ClassVar[SubspaceWeb] = SubspaceWeb()

    options_dataclass = SSEOptions
    options: SSEOptions

    item_name_to_id: ClassVar[dict[str, int]] = ITEM_TABLE
    location_name_to_id: ClassVar[dict[str, int]] = LOCATION_TABLE

    origin_region_name: ClassVar[str] = "Stage Select"
    hint_blacklist: ClassVar[frozenset[str]] = frozenset(["Filler Placeholder"])

    settings_key = "sse_settings"
    settings: ClassVar[SubspaceSettings]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        populate_item_groups(self)

    def generate_early(self) -> None:
        # placeholder
        return super().generate_early()

    def create_regions(self) -> None:
        # Specific enabled/disabled logic goes here
        create_regions(self.player, self, self.options)

    def create_items(self) -> None:
        populate_items(self)

    def set_rules(self) -> None:
        set_rules(self.player, self, self.options)

    def create_item(self, name: str) -> SSEItem:
        data = ITEM_DATA_TABLE[name]

        return SSEItem(name, self.player, data)

    def get_filler_item_name(self) -> str:
        sticker_idx = self.random.randrange(len(STICKERS))
        sticker_data = STICKERS[sticker_idx]
        return build_sticker_name(sticker_data)

    def generate_output(self, output_directory) -> None:
        # can i make this an executable
        pass

    def fill_slot_data(self) -> dict[str, Any]:
        return self.options.as_dict("tabuu_trophies_needed")
