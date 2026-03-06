import os
import html
import json
import re
import subprocess
import shutil
import tempfile
import time
import zipfile
from typing import Callable
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from minecraft_launcher_lib import command, forge, microsoft_account

# ================= CONFIG =================
LAUNCHER_NAME = "PoluxLauncher"
MC_VERSION = "1.20.1"
DEFAULT_SERVER = "poluxcity.falixsrv.me"
APP_ICON = "icon.ico"
BG_IMAGE = "background.png"

MODS = {
    "DerexMaceMod-Balanced-1.20.1-8.1.7.2.jar": "https://poluxsupershark.net/mods/DerexMaceMod-Balanced-1.20.1-8.1.7.2.jar",
    "Dynmap-3.7-beta-6-forge-1.20.jar": "https://poluxsupershark.net/mods/Dynmap-3.7-beta-6-forge-1.20.jar",
    "FramedBlocks-9.4.2.jar": "https://poluxsupershark.net/assets/FramedBlocks-9.4.2.jar",
    "MTR-forge-4.0.2-hotfix-1+1.20.1.jar": "https://poluxsupershark.net/mods/MTR-forge-4.0.2-hotfix-1+1.20.1.jar",
    "Steam_Rails-1.6.14-beta+forge-mc1.20.1.jar": "https://poluxsupershark.net/mods/Steam_Rails-1.6.14-beta+forge-mc1.20.1.jar",
    "TerraBlender-forge-1.20.1-3.0.1.10.jar": "https://poluxsupershark.net/mods/TerraBlender-forge-1.20.1-3.0.1.10.jar",
    "architectury-9.2.14-forge.jar": "https://poluxsupershark.net/mods/architectury-9.2.14-forge.jar",
    "balm-forge-1.20.1-7.3.37-all.jar": "https://poluxsupershark.net/mods/balm-forge-1.20.1-7.3.37-all.jar",
    "cfm-forge-1.20.1-7.0.0-pre36.jar": "https://poluxsupershark.net/mods/cfm-forge-1.20.1-7.0.0-pre36.jar",
    "create-1.20.1-6.0.8.jar": "https://poluxsupershark.net/mods/create-1.20.1-6.0.8.jar",
    "journeymap-1.20.1-5.10.3-forge.jar": "https://poluxsupershark.net/mods/journeymap-1.20.1-5.10.3-forge.jar",
    "lithostitched-forge-1.20.1-1.4.11.jar": "https://poluxsupershark.net/mods/lithostitched-forge-1.20.1-1.4.11.jar",
    "mcef-forge-2.1.6-1.20.1.jar": "https://poluxsupershark.net/mods/mcef-forge-2.1.6-1.20.1.jar",
    "tacz-1.20.1-1.1.7-release.jar": "https://poluxsupershark.net/mods/tacz-1.20.1-1.1.7-release.jar",
    "tectonic-3.0.17-forge-1.20.1.jar": "https://poluxsupershark.net/mods/tectonic-3.0.17-forge-1.20.1.jar",
    "tfmg-1.0.2e.jar": "https://poluxsupershark.net/assets/tfmg-1.0.2e.jar",
    "voicechat-forge-1.20.1-2.6.11.jar": "https://poluxsupershark.net/mods/voicechat-forge-1.20.1-2.6.11.jar",
    "waystones-forge-1.20.1-14.1.17.jar": "https://poluxsupershark.net/mods/waystones-forge-1.20.1-14.1.17.jar",
    "webdisplays-2.0.2-1.20.1.jar": "https://poluxsupershark.net/mods/webdisplays-2.0.2-1.20.1.jar",
    "worldedit-mod-7.2.15.jar": "https://poluxsupershark.net/mods/worldedit-mod-7.2.15.jar",
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
AUTH_FILE_PATH = os.path.join(LAUNCHER_DIR, "auth.json")
MICROSOFT_CLIENT_ID = os.getenv("POLUX_MS_CLIENT_ID", "00000000402b5328")
# Redirect URI expected by the default public Microsoft client used by minecraft_launcher_lib.
MICROSOFT_REDIRECT_URI = os.getenv("POLUX_MS_REDIRECT_URI", "https://login.live.com/oauth20_desktop.srf")


def ensure_directories() -> None:
    os.makedirs(MODS_DIR, exist_ok=True)
    os.makedirs(VERSIONS_DIR, exist_ok=True)


def _noop(_: str) -> None:
    return


def _noop_crash(_: str) -> None:
    return


def _read_auth_file() -> dict:
    if not os.path.exists(AUTH_FILE_PATH):
        return {}
    try:
        with open(AUTH_FILE_PATH, "r", encoding="utf8") as auth_file:
            loaded = json.load(auth_file)
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _write_auth_file(data: dict) -> None:
    os.makedirs(LAUNCHER_DIR, exist_ok=True)
    with open(AUTH_FILE_PATH, "w", encoding="utf8") as auth_file:
        json.dump(data, auth_file, indent=2)


def _get_auth_record() -> dict:
    storage = _read_auth_file()
    record = storage.get("microsoft")
    return record if isinstance(record, dict) else {}


def _set_auth_record(record: dict | None) -> None:
    storage = _read_auth_file()
    if record:
        storage["microsoft"] = record
    else:
        storage.pop("microsoft", None)
    _write_auth_file(storage)


def _set_auth_pending(pending: dict | None) -> None:
    storage = _read_auth_file()
    if pending:
        storage["pending"] = pending
    else:
        storage.pop("pending", None)
    _write_auth_file(storage)


def _get_auth_pending() -> dict:
    storage = _read_auth_file()
    pending = storage.get("pending")
    return pending if isinstance(pending, dict) else {}


def get_auth_status() -> dict:
    record = _get_auth_record()
    refresh_token = str(record.get("refresh_token") or "").strip()
    if refresh_token:
        return {
            "connected": True,
            "provider": "microsoft",
            "name": str(record.get("name") or ""),
            "id": str(record.get("id") or ""),
        }

    return {
        "connected": False,
        "provider": "offline",
        "name": "",
        "id": "",
    }


def start_microsoft_login() -> dict:
    if not MICROSOFT_CLIENT_ID.strip():
        raise RuntimeError("POLUX_MS_CLIENT_ID manquant pour la connexion Microsoft.")

    login_url, state, code_verifier = microsoft_account.get_secure_login_data(
        MICROSOFT_CLIENT_ID,
        MICROSOFT_REDIRECT_URI,
    )
    _set_auth_pending(
        {
            "state": state,
            "code_verifier": code_verifier,
            "created_at": int(time.time()),
        }
    )
    return {
        "login_url": login_url,
        "redirect_uri": MICROSOFT_REDIRECT_URI,
    }


def complete_microsoft_login(redirect_url: str) -> dict:
    pending = _get_auth_pending()
    state = str(pending.get("state") or "").strip()
    code_verifier = str(pending.get("code_verifier") or "").strip()
    if not state or not code_verifier:
        raise RuntimeError("Aucune connexion Microsoft en attente. Lancez d'abord auth-start.")

    try:
        auth_code = microsoft_account.parse_auth_code_url(redirect_url, state)
    except Exception as exc:
        raise RuntimeError("URL de redirection Microsoft invalide.") from exc

    try:
        profile = microsoft_account.complete_login(
            MICROSOFT_CLIENT_ID,
            None,
            MICROSOFT_REDIRECT_URI,
            auth_code,
            code_verifier=code_verifier,
        )
    except microsoft_account.AccountNotOwnMinecraft as exc:
        raise RuntimeError("Ce compte Microsoft ne possede pas Minecraft Java Edition.") from exc
    except microsoft_account.AzureAppNotPermitted as exc:
        raise RuntimeError(
            "Application OAuth Microsoft non autorisee. Configurez POLUX_MS_CLIENT_ID/POLUX_MS_REDIRECT_URI."
        ) from exc

    _set_auth_record(
        {
            "refresh_token": str(profile.get("refresh_token") or ""),
            "name": str(profile.get("name") or ""),
            "id": str(profile.get("id") or ""),
            "updated_at": int(time.time()),
        }
    )
    _set_auth_pending(None)
    return get_auth_status()


def logout_microsoft() -> dict:
    _set_auth_pending(None)
    _set_auth_record(None)
    return get_auth_status()


def _refresh_microsoft_session() -> dict:
    record = _get_auth_record()
    refresh_token = str(record.get("refresh_token") or "").strip()
    if not refresh_token:
        raise RuntimeError("Aucun refresh token Microsoft enregistre. Connectez-vous d'abord.")

    try:
        profile = microsoft_account.complete_refresh(
            MICROSOFT_CLIENT_ID,
            None,
            MICROSOFT_REDIRECT_URI,
            refresh_token,
        )
    except microsoft_account.InvalidRefreshToken as exc:
        logout_microsoft()
        raise RuntimeError("Session Microsoft expiree. Reconnectez-vous.") from exc
    except microsoft_account.AccountNotOwnMinecraft as exc:
        raise RuntimeError("Ce compte Microsoft ne possede pas Minecraft Java Edition.") from exc

    access_token = str(profile.get("access_token") or "").strip()
    name = str(profile.get("name") or "").strip()
    profile_id = str(profile.get("id") or "").strip()
    next_refresh = str(profile.get("refresh_token") or refresh_token).strip()
    if not access_token or not name or not profile_id:
        raise RuntimeError("Reponse Microsoft incomplete, impossible de lancer le jeu.")

    _set_auth_record(
        {
            "refresh_token": next_refresh,
            "name": name,
            "id": profile_id,
            "updated_at": int(time.time()),
        }
    )
    return {
        "name": name,
        "uuid": profile_id.replace("-", ""),
        "access_token": access_token,
    }


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


def _split_server_address(address: str) -> tuple[str, int | None]:
    raw = (address or "").strip()
    if not raw:
        return "", None

    if ":" in raw:
        host, port_text = raw.rsplit(":", 1)
        host = host.strip()
        try:
            port = int(port_text)
        except (TypeError, ValueError):
            return host or raw, None
        if port <= 0 or port > 65535:
            return host or raw, None
        return host or raw, port

    return raw, None


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

    file_match = re.search(r"/minecraft/(mc-mods|modpacks)/([^/]+)/files/(\d+)", parsed.path)
    if file_match:
        _category, slug, file_id = file_match.groups()
        download_url = f"https://www.curseforge.com/api/v1/mods/{slug}/files/{file_id}/download"
        response = requests.get(download_url, allow_redirects=False, timeout=30)
        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("Location")
            if location:
                return urljoin(download_url, location)

    project_match = re.search(r"/minecraft/(mc-mods|modpacks)/([^/?#]+)", parsed.path)
    if not project_match:
        return None

    category, slug = project_match.groups()
    response = requests.get(f"https://api.cfwidget.com/minecraft/{category}/{slug}", timeout=30)
    response.raise_for_status()
    payload = response.json() or {}
    files = payload.get("files") or []

    if not files:
        return None

    if category == "mc-mods":
        for file_data in files:
            versions = [str(item).lower() for item in file_data.get("versions") or []]
            has_mc_version = MC_VERSION.lower() in versions
            has_forge = "forge" in versions
            if has_mc_version and has_forge and file_data.get("downloadUrl"):
                return file_data.get("downloadUrl")
    else:
        for file_data in files:
            versions = [str(item).lower() for item in file_data.get("versions") or []]
            if MC_VERSION.lower() in versions and file_data.get("downloadUrl"):
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


def _manifest_key_is_modpack(key: str) -> bool:
    normalized = key.strip().lower()
    if normalized in {"__curseforge_modpack__", "__modpack_zip__", "__modpack__"}:
        return True
    if normalized.startswith("__curseforge_modpack_") or normalized.startswith("__modpack_zip_"):
        return True
    return False


def _manifest_item_is_modpack(item: dict) -> bool:
    source_type = str(item.get("type") or item.get("source") or "").strip().lower()
    return source_type in {"curseforge_modpack", "modpack_zip", "modpack", "curseforge-zip"}


def load_install_sources(
    on_log: Callable[[str], None] = _noop,
) -> tuple[dict[str, str], list[str]]:
    if not os.path.exists(MODS_MANIFEST_PATH):
        return MODS, []

    try:
        with open(MODS_MANIFEST_PATH, "r", encoding="utf8") as manifest_file:
            manifest = json.load(manifest_file)
    except Exception as exc:
        raise RuntimeError(f"Manifest mods invalide ({MODS_MANIFEST_PATH}): {exc}") from exc

    mods: dict[str, str] = {}
    modpacks: list[str] = []

    if isinstance(manifest, dict):
        for raw_name, raw_url in manifest.items():
            if raw_url is None:
                continue
            name = str(raw_name).strip()
            url = str(raw_url).strip()
            if not name or not url:
                continue
            if _manifest_key_is_modpack(name):
                modpacks.append(url)
            else:
                mods[name] = url
    elif isinstance(manifest, list):
        for item in manifest:
            if not isinstance(item, dict):
                continue
            raw_url = item.get("url")
            if raw_url is None:
                continue
            url = str(raw_url).strip()
            if not url:
                continue
            if _manifest_item_is_modpack(item):
                modpacks.append(url)
                continue
            raw_name = item.get("name")
            if raw_name:
                name = str(raw_name).strip()
                if name:
                    mods[name] = url
    else:
        raise RuntimeError(f"Format non supporte dans {MODS_MANIFEST_PATH}.")

    if not mods and not modpacks:
        raise RuntimeError(f"Aucun mod trouve dans {MODS_MANIFEST_PATH}.")

    mods = _expand_google_drive_folders(mods, on_log=on_log)

    on_log(f"Manifest mods charge: {len(mods)} entree(s)")
    if modpacks:
        on_log(f"Manifest modpack charge: {len(modpacks)} archive(s)")
    return mods, modpacks


def load_mods(
    on_log: Callable[[str], None] = _noop,
) -> dict[str, str]:
    mods, _modpacks = load_install_sources(on_log=on_log)
    return mods


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


def _safe_extract_zip(zip_path: str, destination_dir: str) -> None:
    base_dir = os.path.realpath(destination_dir)
    with zipfile.ZipFile(zip_path, "r") as archive:
        for member in archive.infolist():
            normalized_name = member.filename.replace("\\", "/")
            if normalized_name.startswith("/") or normalized_name.startswith("../") or "/../" in normalized_name:
                continue
            if re.match(r"^[a-zA-Z]:", normalized_name):
                continue

            target_path = os.path.realpath(os.path.join(destination_dir, member.filename))
            if target_path != base_dir and not target_path.startswith(base_dir + os.sep):
                continue
            archive.extract(member, destination_dir)


def _copy_tree(source_dir: str, destination_dir: str) -> int:
    if not os.path.isdir(source_dir):
        return 0

    copied_files = 0
    for root, _dirs, files in os.walk(source_dir):
        rel = os.path.relpath(root, source_dir)
        target_root = destination_dir if rel == "." else os.path.join(destination_dir, rel)
        os.makedirs(target_root, exist_ok=True)
        for file_name in files:
            source_path = os.path.join(root, file_name)
            target_path = os.path.join(target_root, file_name)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            shutil.copy2(source_path, target_path)
            copied_files += 1

    return copied_files


def _resolve_curseforge_manifest_download_url(project_id: int, file_id: int, api_key: str) -> str | None:
    headers = {
        "Accept": "application/json",
        "x-api-key": api_key,
    }
    endpoints = [
        f"https://api.curseforge.com/v1/mods/{project_id}/files/{file_id}/download-url",
        f"https://api.curseforge.com/v1/mods/files/{file_id}/download-url",
    ]

    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, headers=headers, timeout=30)
        except requests.RequestException:
            continue

        if response.status_code != 200:
            continue

        try:
            payload = response.json() or {}
        except ValueError:
            continue

        data = payload.get("data")
        if isinstance(data, str) and data:
            return data

    return None


def _install_curseforge_manifest_files(
    manifest: dict,
    on_log: Callable[[str], None] = _noop,
    on_status: Callable[[str], None] = _noop,
) -> int:
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        return 0

    api_key = (os.getenv("CURSEFORGE_API_KEY") or "").strip()
    if not api_key:
        on_log(
            "Le modpack reference des fichiers CurseForge externes, mais CURSEFORGE_API_KEY est absent. "
            "Tentative sans telechargement API."
        )
        return 0

    downloaded = 0
    total = len(files)
    for index, item in enumerate(files, start=1):
        if not isinstance(item, dict):
            continue
        project_id = item.get("projectID")
        file_id = item.get("fileID")
        if project_id is None or file_id is None:
            continue

        try:
            project_id_int = int(project_id)
            file_id_int = int(file_id)
        except (TypeError, ValueError):
            continue

        download_url = _resolve_curseforge_manifest_download_url(project_id_int, file_id_int, api_key)
        if not download_url:
            on_log(f"Impossible de resoudre CurseForge projectID={project_id_int}, fileID={file_id_int}")
            continue

        destination = os.path.join(MODS_DIR, f"curseforge-{project_id_int}-{file_id_int}.jar")
        if os.path.exists(destination):
            continue

        on_status(f"Modpack CurseForge {index}/{total}")
        on_log(f"Telechargement CurseForge fileID={file_id_int}")
        download(download_url, destination, on_status=on_status)
        downloaded += 1

    return downloaded


def _install_modpack_zip(
    source_url: str,
    on_log: Callable[[str], None] = _noop,
    on_status: Callable[[str], None] = _noop,
) -> None:
    with tempfile.TemporaryDirectory(prefix="polux_modpack_") as temp_dir:
        zip_path = os.path.join(temp_dir, "modpack.zip")
        unpack_dir = os.path.join(temp_dir, "unzipped")

        on_log(f"Telechargement du modpack: {source_url}")
        download(source_url, zip_path, on_status=on_status)

        if not zipfile.is_zipfile(zip_path):
            raise RuntimeError(f"Le fichier telecharge n'est pas un zip valide: {source_url}")

        os.makedirs(unpack_dir, exist_ok=True)
        _safe_extract_zip(zip_path, unpack_dir)

        manifest_path = os.path.join(unpack_dir, "manifest.json")
        manifest: dict = {}
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf8") as manifest_file:
                    manifest = json.load(manifest_file) or {}
            except Exception as exc:
                on_log(f"manifest.json illisible ({exc}), installation en mode extraction simple.")

        mc_version_in_pack = (
            str((manifest.get("minecraft") or {}).get("version") or "").strip()
            if isinstance(manifest, dict)
            else ""
        )
        if mc_version_in_pack and mc_version_in_pack != MC_VERSION:
            on_log(f"Attention: modpack pour Minecraft {mc_version_in_pack}, launcher configure en {MC_VERSION}.")

        copied_files = 0

        overrides_name = "overrides"
        if isinstance(manifest, dict):
            raw_overrides = manifest.get("overrides")
            if isinstance(raw_overrides, str) and raw_overrides.strip():
                overrides_name = raw_overrides.strip()

        overrides_dir = os.path.join(unpack_dir, overrides_name)
        copied_files += _copy_tree(overrides_dir, MC_DIR)

        # Server packs are often flat zips (mods/config at root) without overrides.
        copied_files += _copy_tree(os.path.join(unpack_dir, "mods"), MODS_DIR)
        copied_files += _copy_tree(os.path.join(unpack_dir, "config"), os.path.join(MC_DIR, "config"))

        downloaded_from_manifest = 0
        if isinstance(manifest, dict):
            downloaded_from_manifest = _install_curseforge_manifest_files(
                manifest,
                on_log=on_log,
                on_status=on_status,
            )

        if copied_files == 0 and downloaded_from_manifest == 0:
            raise RuntimeError(
                "Aucun contenu de modpack installe. "
                "Le zip ne contient pas d'overrides/mods exploitables ou les fichiers CurseForge n'ont pas pu etre resolves "
                "(essayez avec CURSEFORGE_API_KEY)."
            )

        on_log(
            f"Modpack installe: {copied_files} fichier(s) copie(s), "
            f"{downloaded_from_manifest} fichier(s) CurseForge telecharge(s)."
        )


def install(
    on_log: Callable[[str], None] = _noop,
    on_status: Callable[[str], None] = _noop,
) -> None:
    ensure_directories()
    mods, modpacks = load_install_sources(on_log=on_log)

    on_status("Recherche Forge...")
    forge_version = forge.find_forge_version(MC_VERSION)
    if not forge_version:
        raise RuntimeError(f"Aucune version Forge trouvee pour {MC_VERSION}.")

    forge.install_forge_version(forge_version, MC_DIR)
    on_log(f"Forge installe : {forge_version}")

    if modpacks:
        on_status("Installation du modpack...")
        for modpack_url in modpacks:
            _install_modpack_zip(
                modpack_url,
                on_log=on_log,
                on_status=on_status,
            )

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
    account_mode: str = "offline",
    on_log: Callable[[str], None] = _noop,
    on_status: Callable[[str], None] = _noop,
    on_crash: Callable[[str], None] = _noop_crash,
) -> None:
    ensure_directories()
    version = find_forge()
    if not version:
        raise RuntimeError("Forge manquant. Lancez d'abord l'installation.")

    normalized_ram_gb = normalize_ram_gb(ram_gb)

    normalized_mode = str(account_mode or "offline").strip().lower()
    if normalized_mode == "microsoft":
        session = _refresh_microsoft_session()
        options = {
            "username": session["name"],
            "uuid": session["uuid"],
            "token": session["access_token"],
            "jvmArguments": [f"-Xmx{normalized_ram_gb}G"],
        }
        on_log(f"Session Microsoft activee: {session['name']}")
    else:
        options = {
            "username": username.strip() or "Player",
            "uuid": "00000000000000000000000000000000",
            "token": "",
            "jvmArguments": [f"-Xmx{normalized_ram_gb}G"],
        }

    minecraft_command = command.get_minecraft_command(version, MC_DIR, options)
    server_host, server_port = _split_server_address(DEFAULT_SERVER)
    if server_host:
        minecraft_command += ["--server", server_host]
        if server_port is not None:
            minecraft_command += ["--port", str(server_port)]
        # Newer Minecraft versions rely on Quick Play for auto-join behavior.
        quick_play_target = f"{server_host}:{server_port or 25565}"
        minecraft_command += ["--quickPlayMultiplayer", quick_play_target]
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
