# PoluxLauncher

Current release:
- Public version: `V4`
- Technical version: `1.2.1`

## Python launcher (original)

```bash
pip install -r requirements.txt
python main.py
```

## Desktop UI variants

### Tactical UI (current)

```bash
pip install -r requirements.txt
npm install
npm run start:tactical
```

### Friendly UI

```bash
pip install -r requirements.txt
npm install
npm run start:friendly
```

Optional: set a custom Python executable for Electron dev mode.

```bash
set POLUX_PYTHON=C:\\Path\\To\\python.exe
npm run start:friendly
```

## Build Windows installers (.exe)

```bash
pip install -r requirements.txt
pip install pyinstaller
npm install
npm run dist:all
```

Build outputs:
- `dist\\PoluxLauncher-Tactical-Setup-1.2.1.exe`
- `dist\\PoluxLauncher-Friendly-Setup-1.2.1.exe`

## Optional custom mods manifest

Create `config\\mods_manifest.json` to override the built-in mod list.

Supported sources:
- Direct HTTP/HTTPS `.jar` links
- Modrinth project/version links
- CurseForge project/file links
- CurseForge modpack `.zip` links (project/file)
- Google Drive shared file links
- Google Drive shared folder links (downloads all `.jar` files in folder)

Accepted JSON formats:

```json
{
  "example-mod.jar": "https://modrinth.com/mod/example/version/abc123",
  "__curseforge_modpack__": "https://www.curseforge.com/minecraft/modpacks/example-pack/files/1234567"
}
```

```json
[
  {
    "name": "example-mod.jar",
    "url": "https://drive.google.com/file/d/FILE_ID/view"
  },
  {
    "type": "curseforge_modpack",
    "url": "https://www.curseforge.com/minecraft/modpacks/example-pack/files/1234567"
  }
]
```

Notes:
- CurseForge exported modpack zips may require downloading file IDs from the CurseForge API.
- To enable that path, define `CURSEFORGE_API_KEY` in your environment before running install.

## Optional Microsoft premium login

The launcher now supports two account modes:
- `offline` (default)
- `microsoft` (premium)

In UI:
1. Select account mode `Microsoft (Premium)`.
2. Click `Connexion Microsoft` / `Connect Microsoft`.
3. Complete login in browser and paste the redirect URL when prompted.

Session tokens are stored in `%APPDATA%\\PoluxLauncher\\auth.json`.

Optional environment overrides:
- `POLUX_MS_CLIENT_ID`
- `POLUX_MS_REDIRECT_URI`
