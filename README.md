# PoluxLauncher

## Python launcher (original)

```bash
pip install -r requirements.txt
python main.py
```

## JavaScript UI (Electron)

The JavaScript UI uses the same launcher logic and files through `launcher_cli.py` and `launcher_core.py`.

```bash
pip install -r requirements.txt
npm install
npm start
```

Optional: set a custom Python executable for Electron dev mode.

```bash
set POLUX_PYTHON=C:\\Path\\To\\python.exe
npm start
```

## Build Windows installer (.exe)

```bash
pip install -r requirements.txt
pip install pyinstaller
npm install
npm run dist
```

Build output:
- `dist\\PoluxLauncher Setup 1.1.0.exe`
