import os
import subprocess
from typing import Callable

import requests
from minecraft_launcher_lib import command, forge

# ================= CONFIG =================
LAUNCHER_NAME = "PoluxLauncher"
MC_VERSION = "1.20.1"
DEFAULT_SERVER = "poluxcity.falixsrv.me"
APP_ICON = "icon.ico"
BG_IMAGE = "background.png"

MODS = {
    "DerexMaceMod-Balanced-1.20.1-8.1.7.2.jar": "https://poluxsupershark.net/assets/mods/DerexMaceMod-Balanced-1.20.1-8.1.7.2.jar",
    "Dynmap-3.7-beta-6-forge-1.20.jar": "https://poluxsupershark.net/assets/mods/Dynmap-3.7-beta-6-forge-1.20.jar",
    "FramedBlocks-9.4.2.jar": "https://poluxsupershark.net/mods/assets/FramedBlocks-9.4.2.jar",
    "MTR-forge-4.0.2-hotfix-1+1.20.1.jar": "https://poluxsupershark.net/assets/mods/MTR-forge-4.0.2-hotfix-1+1.20.1.jar",
    "Steam_Rails-1.6.14-beta+forge-mc1.20.1.jar": "https://poluxsupershark.net/assets/mods/Steam_Rails-1.6.14-beta+forge-mc1.20.1.jar",
    "TerraBlender-forge-1.20.1-3.0.1.10.jar": "https://poluxsupershark.net/assets/mods/TerraBlender-forge-1.20.1-3.0.1.10.jar",
    "architectury-9.2.14-forge.jar": "https://poluxsupershark.net/assets/mods/architectury-9.2.14-forge.jar",
    "balm-forge-1.20.1-7.3.37-all.jar": "https://poluxsupershark.net/assets/mods/balm-forge-1.20.1-7.3.37-all.jar",
    "cfm-forge-1.20.1-7.0.0-pre36.jar": "https://poluxsupershark.net/assets/mods/cfm-forge-1.20.1-7.0.0-pre36.jar",
    "create-1.20.1-6.0.8.jar": "https://poluxsupershark.net/mods/assets/create-1.20.1-6.0.8.jar",
    "journeymap-1.20.1-5.10.3-forge.jar": "https://poluxsupershark.net/assets/mods/journeymap-1.20.1-5.10.3-forge.jar",
    "lithostitched-forge-1.20.1-1.4.11.jar": "https://poluxsupershark.net/assets/mods/lithostitched-forge-1.20.1-1.4.11.jar",
    "mcef-forge-2.1.6-1.20.1.jar": "https://poluxsupershark.net/assets/mods/mcef-forge-2.1.6-1.20.1.jar",
    "tacz-1.20.1-1.1.7-release.jar": "https://poluxsupershark.net/assets/mods/tacz-1.20.1-1.1.7-release.jar",
    "tectonic-3.0.17-forge-1.20.1.jar": "https://poluxsupershark.net/assets/mods/tectonic-3.0.17-forge-1.20.1.jar",
    "tfmg-1.0.2e.jar": "https://poluxsupershark.net/assets/mods/tfmg-1.0.2e.jar",
    "voicechat-forge-1.20.1-2.6.11.jar": "https://poluxsupershark.net/assets/mods/voicechat-forge-1.20.1-2.6.11.jar",
    "waystones-forge-1.20.1-14.1.17.jar": "https://poluxsupershark.net/assets/mods/waystones-forge-1.20.1-14.1.17.jar",
    "webdisplays-2.0.2-1.20.1.jar": "https://poluxsupershark.net/assets/mods/webdisplays-2.0.2-1.20.1.jar",
    "worldedit-mod-7.2.15.jar": "https://poluxsupershark.net/assets/mods/worldedit-mod-7.2.15.jar",
}

# ================= PATHS =================
APPDATA = os.getenv("APPDATA") or os.path.expanduser("~")
LAUNCHER_DIR = os.path.join(APPDATA, LAUNCHER_NAME)
MC_DIR = os.path.join(LAUNCHER_DIR, "minecraft")
MODS_DIR = os.path.join(MC_DIR, "mods")
VERSIONS_DIR = os.path.join(MC_DIR, "versions")


def ensure_directories() -> None:
    os.makedirs(MODS_DIR, exist_ok=True)
    os.makedirs(VERSIONS_DIR, exist_ok=True)


def _noop(_: str) -> None:
    return


def download(url: str, path: str, on_status: Callable[[str], None] = _noop) -> None:
    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()
    total = int(response.headers.get("content-length", 0))
    done = 0

    with open(path, "wb") as file:
        for chunk in response.iter_content(8192):
            if not chunk:
                continue
            file.write(chunk)
            done += len(chunk)
            if total:
                percent = done / total * 100
                on_status(f"Telechargement {percent:.1f}%")


def install(
    on_log: Callable[[str], None] = _noop,
    on_status: Callable[[str], None] = _noop,
) -> None:
    ensure_directories()

    on_status("Recherche Forge...")
    forge_version = forge.find_forge_version(MC_VERSION)
    if not forge_version:
        raise RuntimeError(f"Aucune version Forge trouvee pour {MC_VERSION}.")

    forge.install_forge_version(forge_version, MC_DIR)
    on_log(f"Forge installe : {forge_version}")

    on_status("Installation des mods...")
    for name, url in MODS.items():
        destination = os.path.join(MODS_DIR, name)
        if os.path.exists(destination):
            continue
        on_log(f"Telechargement de {name}")
        download(url, destination, on_status=on_status)

    on_status("Installation terminee")


def find_forge() -> str | None:
    ensure_directories()
    for version in os.listdir(VERSIONS_DIR):
        if version.startswith(f"{MC_VERSION}-forge"):
            return version
    return None


def launch(
    username: str = "Player",
    on_log: Callable[[str], None] = _noop,
    on_status: Callable[[str], None] = _noop,
) -> None:
    ensure_directories()
    version = find_forge()
    if not version:
        raise RuntimeError("Forge manquant. Lancez d'abord l'installation.")

    options = {
        "username": username.strip() or "Player",
        "uuid": "00000000000000000000000000000000",
        "token": "",
    }

    minecraft_command = command.get_minecraft_command(version, MC_DIR, options)
    minecraft_command += ["--server", DEFAULT_SERVER]

    creation_flags = 0
    if os.name == "nt":
        creation_flags = subprocess.CREATE_NO_WINDOW

    subprocess.Popen(minecraft_command, creationflags=creation_flags)
    on_log(f"Lancement avec {options['username']}")
    on_status("Minecraft lance")
