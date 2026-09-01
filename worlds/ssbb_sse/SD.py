import hashlib
import importlib
import subprocess
import tempfile
from pathlib import Path

import bsdiff4

from CommonClient import CommonContext, logger
from settings import get_settings

SDCARD_ANCHOR = "worlds.ssbb_sse.sdcard"


def create_sd(ctx: CommonContext):
    dolphin_tool = get_settings().sse_settings.dolphin_tool
    brawl_iso = get_settings().sse_settings.brawl_iso

    logger.info("Checking your ROM file...")

    with open(brawl_iso, mode="rb") as f:
        md5_hash = hashlib.file_digest(f, "md5").hexdigest()
        if md5_hash not in brawl_iso.md5_hashes:
            logger.error(
                "Provided Brawl ISO did not hash correctly. "
                "Please ensure that you are using an unmodified NTSC USA ROM "
                "(both v1.01 and v1.02 are fine)"
            )
            return

    logger.info("Creating SD card")

    brawl_dir = Path(brawl_iso).parent
    sd_dir = brawl_dir / "sd_card"
    try:
        sd_dir.mkdir()
    except FileExistsError:
        logger.error("SD card directory " + str(sd_dir) + " already exists - please remove it first")
        return

    logger.info("Created SD card folder")

    # necessary codes
    codes_dir = sd_dir / "codes"
    codes_dir.mkdir()
    with importlib.resources.open_binary(SDCARD_ANCHOR, "RSBE01.gct") as rsbe_bytes:
        rsbe01_gct = codes_dir / "RSBE01.gct"
        rsbe01_gct.write_bytes(rsbe_bytes.read())
    with importlib.resources.open_text(SDCARD_ANCHOR, "RSBE01.txt") as rsbe_txt:
        rsbe01_txt = codes_dir / "RSBE01.txt"
        rsbe01_txt.write_text(rsbe_txt.read())

    logger.info("Wrote mod codes")

    adventure_pac_folder = sd_dir / "private/wii/app/RSBE/pf/stage/adventure"
    adventure_pac_folder.mkdir(parents=True)

    menu2_folder = sd_dir / "private/wii/app/RSBE/pfmenu2"
    menu2_folder.mkdir(parents=True)

    # extract pac files from rom
    with tempfile.TemporaryDirectory() as tmpdirname:
        temp_dir = Path(tmpdirname)

        # Patch Tabuu door room
        subprocess.run(
            [
                dolphin_tool,
                "extract",
                "-i",
                brawl_iso,
                "-s",
                "stage/adventure/420037a.pac",
                "-o",
                temp_dir,
                "-q",
            ],
            check=True,
        )
        pac_420037a_o = temp_dir / "DATA/files/stage/adventure/420037a.pac"
        pac_420037a = adventure_pac_folder / "420037a.pac"

        patch_file(pac_420037a_o, "420037a.patch", pac_420037a)

        # Patch title screen
        subprocess.run(
            [
                dolphin_tool,
                "extract",
                "-i",
                brawl_iso,
                "-s",
                "menu2/sc_title_en.pac",
                "-o",
                temp_dir,
                "-q",
            ],
            check=True,
        )
        sc_title_o = temp_dir / "DATA/files/menu2/sc_title_en.pac"
        sc_title = menu2_folder / "sc_title.pac"

        patch_file(sc_title_o, "sc_title.patch", sc_title)

    logger.info("Created SD card directory at " + str(sd_dir))
    logger.info("Please use Dolphin to convert the directory into a usable SD card!")


def patch_file(origin_file, patch_path, target_file=None):
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Copy patch file to temporary directory
        temp_dir = Path(tmpdirname)
        with importlib.resources.open_binary(SDCARD_ANCHOR, patch_path) as patch_data:
            patchfile = temp_dir / "patch.patch"
            patchfile.write_bytes(patch_data.read())

            if target_file is None:
                # Patch in place
                bsdiff4.file_patch_inplace(origin_file, patchfile)
            else:
                # Patch to target file
                bsdiff4.file_patch(origin_file, target_file, patchfile)
