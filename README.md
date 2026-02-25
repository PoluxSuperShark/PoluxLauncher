# PoluxLauncher

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
- `dist\\PoluxLauncher-Tactical-Setup-1.2.0.exe`
- `dist\\PoluxLauncher-Friendly-Setup-1.2.0.exe`
