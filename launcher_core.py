import os
import html
import json
import re
import subprocess
import time
from typing import Callable
from urllib.parse import parse_qs, urljoin, urlparse

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

MIN_RAM_GB = 2
MAX_RAM_GB = 16
DEFAULT_RAM_GB = 4
MODS_MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "config", "mods_manifest.json")


def ensure_directories() -> None:
    os.makedirs(MODS_DIR, exist_ok=True)
    os.makedirs(VERSIONS_DIR, exist_ok=True)


def _noop(_: str) -> None:
    return


def _noop_crash(_: str) -> None:
    return


def normalize_ram_gb(ram_gb: int | str) -> int:
    try:
        value = int(ram_gb)
    except (TypeError, ValueError):
        value = DEFAULT_RAM_GB

    if value < MIN_RAM_GB:
        return MIN_RAM_GB
    if value > MAX_RAM_GB:
        return MAX_RAM_GB
    return value


def _extract_google_drive_file_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = parsed.netloc.lower()

    if "drive.google.com" not in host and "docs.google.com" not in host:
        return None

    file_match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", parsed.path)
    if file_match:
        return file_match.group(1)

    query_id = parse_qs(parsed.query).get("id")
    if query_id:
        return query_id[0]

    return None


def _extract_google_drive_folder_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = parsed.netloc.lower()

    if "drive.google.com" not in host and "docs.google.com" not in host:
        return None

    folder_match = re.search(r"/folders/([a-zA-Z0-9_-]+)", parsed.path)
    if folder_match:
        return folder_match.group(1)

    query_id = parse_qs(parsed.query).get("id")
    if query_id:
        return query_id[0]

    return None


def _list_google_drive_folder_files(folder_id: str) -> dict[str, str]:
    view_url = f"https://drive.google.com/embeddedfolderview?id={folder_id}#list"
    response = requests.get(view_url, timeout=30)
    response.raise_for_status()

    # embeddedfolderview exposes entries as anchor tags containing /file/d/<id>/view links.
    pattern = re.compile(
        r'href="[^"]*/file/d/([a-zA-Z0-9_-]+)/view[^"]*"[^>]*>([^<]+)<',
        re.IGNORECASE,
    )
    entries = pattern.findall(response.text)

    files: dict[str, str] = {}
    for file_id, raw_name in entries:
        name = html.unescape(raw_name).strip()
        if not name:
            continue
        if not name.lower().endswith(".jar"):
            continue
        files[name] = f"https://drive.google.com/file/d/{file_id}/view"

    return files


def _expand_google_drive_folders(
    mods: dict[str, str],
    on_log: Callable[[str], None] = _noop,
) -> dict[str, str]:
    expanded: dict[str, str] = {}

    for name, url in mods.items():
        folder_id = _extract_google_drive_folder_id(url)
        if not folder_id or "/folders/" not in url:
            expanded[name] = url
            continue

        folder_files = _list_google_drive_folder_files(folder_id)
        if not folder_files:
            raise RuntimeError(f"Aucun fichier .jar trouve dans le dossier Google Drive: {url}")

        on_log(f"Dossier Google Drive charge: {len(folder_files)} mod(s)")
        expanded.update(folder_files)

    return expanded


def _stream_download(
    response: requests.Response,
    path: str,
    on_status: Callable[[str], None] = _noop,
) -> None:
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


def _download_google_drive(file_id: str, path: str, on_status: Callable[[str], None] = _noop) -> None:
    with requests.Session() as session:
        base_url = "https://drive.google.com/uc"
        params = {"export": "download", "id": file_id}
        response = session.get(base_url, params=params, stream=True, timeout=120)
        response.raise_for_status()

        token = None
        for key, value in response.cookies.items():
            if key.startswith("download_warning"):
                token = value
                break

        if token:
            params["confirm"] = token
            response = session.get(base_url, params=params, stream=True, timeout=120)
            response.raise_for_status()

        _stream_download(response, path, on_status=on_status)


def _resolve_modrinth_url(url: str) -> str | None:
    parsed = urlparse(url)
    if "modrinth.com" not in parsed.netloc.lower():
        return None

    version_match = re.search(r"/version/([^/?#]+)", parsed.path)
    if version_match:
        version_id = version_match.group(1)
        response = requests.get(f"https://api.modrinth.com/v2/version/{version_id}", timeout=30)
        response.raise_for_status()
        payload = response.json()
        files = payload.get("files") or []
        if not files:
            return None
        primary = next((item for item in files if item.get("primary")), files[0])
        return primary.get("url")

    project_match = re.search(r"/mod/([^/?#]+)", parsed.path)
    if not project_match:
        return None

    slug = project_match.group(1)
    response = requests.get(
        f"https://api.modrinth.com/v2/project/{slug}/version",
        params={
            "loaders": json.dumps(["forge"]),
            "game_versions": json.dumps([MC_VERSION]),
        },
        timeout=30,
    )
    response.raise_for_status()
    versions = response.json() or []
    if not versions:
        return None

    first_version = versions[0]
    files = first_version.get("files") or []
    if not files:
        return None

    primary = next((item for item in files if item.get("primary")), files[0])
    return primary.get("url")


def _resolve_curseforge_url(url: str) -> str | None:
    parsed = urlparse(url)
    if "curseforge.com" not in parsed.netloc.lower():
        return None

    file_match = re.search(r"/minecraft/mc-mods/([^/]+)/files/(\d+)", parsed.path)
    if file_match:
        slug, file_id = file_match.groups()
        download_url = f"https://www.curseforge.com/api/v1/mods/{slug}/files/{file_id}/download"
        response = requests.get(download_url, allow_redirects=False, timeout=30)
        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("Location")
            if location:
                return urljoin(download_url, location)

    project_match = re.search(r"/minecraft/mc-mods/([^/?#]+)", parsed.path)
    if not project_match:
        return None

    slug = project_match.group(1)
    response = requests.get(f"https://api.cfwidget.com/minecraft/mc-mods/{slug}", timeout=30)
    response.raise_for_status()
    payload = response.json() or {}
    files = payload.get("files") or []

    if not files:
        return None

    for file_data in files:
        versions = [str(item).lower() for item in file_data.get("versions") or []]
        has_mc_version = MC_VERSION.lower() in versions
        has_forge = "forge" in versions
        if has_mc_version and has_forge and file_data.get("downloadUrl"):
            return file_data.get("downloadUrl")

    return files[0].get("downloadUrl")


def _resolve_download_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()

    if "modrinth.com" in host:
        resolved = _resolve_modrinth_url(url)
        if resolved:
            return resolved
        raise RuntimeError(f"Impossible de resoudre le lien Modrinth: {url}")

    if "curseforge.com" in host:
        resolved = _resolve_curseforge_url(url)
        if resolved:
            return resolved
        raise RuntimeError(f"Impossible de resoudre le lien CurseForge: {url}")

    return url


def load_mods(
    on_log: Callable[[str], None] = _noop,
) -> dict[str, str]:
    if not os.path.exists(MODS_MANIFEST_PATH):
        return MODS

    try:
        with open(MODS_MANIFEST_PATH, "r", encoding="utf8") as manifest_file:
            manifest = json.load(manifest_file)
    except Exception as exc:
        raise RuntimeError(f"Manifest mods invalide ({MODS_MANIFEST_PATH}): {exc}") from exc

    if isinstance(manifest, dict):
        result = {str(name): str(url) for name, url in manifest.items()}
    elif isinstance(manifest, list):
        result = {}
        for item in manifest:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            url = item.get("url")
            if name and url:
                result[str(name)] = str(url)
    else:
        raise RuntimeError(f"Format non supporte dans {MODS_MANIFEST_PATH}.")

    if not result:
        raise RuntimeError(f"Aucun mod trouve dans {MODS_MANIFEST_PATH}.")

    result = _expand_google_drive_folders(result, on_log=on_log)

    on_log(f"Manifest mods charge: {len(result)} entree(s)")
    return result


def _read_text_file(path: str, max_chars: int = 200000) -> str:
    with open(path, "r", encoding="utf8", errors="replace") as file:
        data = file.read()
    if len(data) <= max_chars:
        return data
    return data[-max_chars:]


def _find_latest_file(directory: str, extensions: tuple[str, ...], min_mtime: float | None = None) -> str | None:
    if not os.path.isdir(directory):
        return None

    candidates: list[tuple[float, str]] = []
    for entry in os.listdir(directory):
        lower = entry.lower()
        if not any(lower.endswith(ext) for ext in extensions):
            continue
        full_path = os.path.join(directory, entry)
        if not os.path.isfile(full_path):
            continue
        mtime = os.path.getmtime(full_path)
        if min_mtime is not None and mtime + 2 < min_mtime:
            continue
        candidates.append((mtime, full_path))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def get_latest_crash_report(min_mtime: float | None = None) -> tuple[str, str] | None:
    crash_reports_dir = os.path.join(MC_DIR, "crash-reports")
    latest = _find_latest_file(crash_reports_dir, (".txt",), min_mtime=min_mtime)
    if not latest:
        return None
    return latest, _read_text_file(latest)


def download(url: str, path: str, on_status: Callable[[str], None] = _noop) -> None:
    google_file_id = _extract_google_drive_file_id(url)
    if google_file_id:
        _download_google_drive(google_file_id, path, on_status=on_status)
        return

    resolved_url = _resolve_download_url(url)
    response = requests.get(resolved_url, stream=True, timeout=120)
    response.raise_for_status()
    _stream_download(response, path, on_status=on_status)


def install(
    on_log: Callable[[str], None] = _noop,
    on_status: Callable[[str], None] = _noop,
) -> None:
    ensure_directories()
    mods = load_mods(on_log=on_log)

    on_status("Recherche Forge...")
    forge_version = forge.find_forge_version(MC_VERSION)
    if not forge_version:
        raise RuntimeError(f"Aucune version Forge trouvee pour {MC_VERSION}.")

    forge.install_forge_version(forge_version, MC_DIR)
    on_log(f"Forge installe : {forge_version}")

    on_status("Installation des mods...")
    for name, url in mods.items():
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
    ram_gb: int = DEFAULT_RAM_GB,
    on_log: Callable[[str], None] = _noop,
    on_status: Callable[[str], None] = _noop,
    on_crash: Callable[[str], None] = _noop_crash,
) -> None:
    ensure_directories()
    version = find_forge()
    if not version:
        raise RuntimeError("Forge manquant. Lancez d'abord l'installation.")

    normalized_ram_gb = normalize_ram_gb(ram_gb)

    options = {
        "username": username.strip() or "Player",
        "uuid": "00000000000000000000000000000000",
        "token": "",
        "jvmArguments": [f"-Xmx{normalized_ram_gb}G"],
    }

    minecraft_command = command.get_minecraft_command(version, MC_DIR, options)
    minecraft_command += ["--server", DEFAULT_SERVER]
    launch_started_at = time.time()

    creation_flags = 0
    if os.name == "nt":
        creation_flags = subprocess.CREATE_NO_WINDOW

    process = subprocess.Popen(minecraft_command, creationflags=creation_flags)
    on_log(f"Lancement avec {options['username']} ({normalized_ram_gb}G RAM)")
    on_status("Minecraft lance")

    exit_code = process.wait()
    if exit_code == 0:
        on_status("Minecraft ferme")
        return

    on_status("Crash detecte")
    crash = get_latest_crash_report(min_mtime=launch_started_at)
    if crash:
        crash_path, crash_content = crash
        on_crash(f"Crash report: {crash_path}\n\n{crash_content}")
    else:
        on_crash("Crash detecte, mais aucun fichier dans crash-reports n'a ete trouve.")

    raise RuntimeError(f"Minecraft s'est arrete avec le code {exit_code}.")
