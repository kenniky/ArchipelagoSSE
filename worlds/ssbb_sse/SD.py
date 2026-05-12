import hashlib

import importlib
from settings import get_settings
import subprocess
from pathlib import Path
from CommonClient import CommonContext, logger
import tempfile
import bsdiff4


async def create_sd(ctx: CommonContext):
    dolphin_tool = get_settings().sse_settings.dolphin_tool
    brawl_iso = get_settings().sse_settings.brawl_iso

    with open(brawl_iso, mode="rb") as f:
        md5_hash = hashlib.file_digest(f, "md5").hexdigest()
        if md5_hash not in brawl_iso.md5s:
            logger.error(
                (
                    "Provided Brawl ISO did not hash correctly. "
                    "Please ensure that you are using an unmodified NTSC USA ROM "
                    "(both v1.01 and v1.02 are fine)"
                )
            )
            return

    brawl_dir = Path(brawl_iso).parent
    sd_dir = brawl_dir / "sd_card"
    try:
        sd_dir.mkdir()
    except FileExistsError:
        logger.error(
            "SD card directory "
            + sd_dir
            + " already exists - please remove it first"
        )
        return

    # necessary codes
    codes_dir = sd_dir / "codes"
    codes_dir.mkdir()
    with importlib.resources.open_binary(__name__, "sdcard/RSBE01.gct") as rsbe_bytes:
        rsbe01_gct = codes_dir / "RSBE01.gct"
        rsbe01_gct.write_bytes(rsbe_bytes.read())
    with importlib.resources.open_text(__name__, "sdcard/RSBE01.txt") as rsbe_txt:
        rsbe01_txt = codes_dir / "RSBE01.txt"
        rsbe01_txt.write_text(rsbe_txt.read())
    
    logger.info("Wrote mod codes")

    adventure_pac_folder = sd_dir / "private/wii/app/RSBE/pf/stage/adventure"
    adventure_pac_folder.mkdir(parents=True)
    # extract pac files from rom
    with tempfile.TemporaryDirectory() as tmpdirname:
        temp_dir = Path(tmpdirname)
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
            ]
        )
        pac_420037a_o = temp_dir / "DATA/files/stage/adventure/420037a.pac"
        pac_420037a = adventure_pac_folder / "420037a.pac"

        patch_file(pac_420037a_o, "sdcard/420037a.patch", pac_420037a)

    logger.info("Created SD card directory at ", sd_dir)
    logger.info("Please use Dolphin to convert the directory into a usable SD card!")


async def patch_file(origin_file, patch_path, target_file=None):
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Copy patch file to temporary directory
        temp_dir = Path(tmpdirname)
        with importlib.resources.open_binary(__name__, patch_path) as patch_data:
            patchfile = temp_dir / "patch.patch"
            patchfile.write_bytes(patch_data.read())

            if target_file is None:
                # Patch in place
                bsdiff4.file_patch_inplace(origin_file, patchfile)
            else:
                # Patch to target file
                bsdiff4.file_patch(origin_file, target_file, patchfile)
