import argparse
import sys


def emit(kind: str, message: str) -> None:
    lines = str(message).split("\n")
    if not lines:
        lines = [""]
    for line in lines:
        print(f"[{kind}] {line}", flush=True)


def load_backend():
    try:
        from launcher_core import install, launch

        return install, launch
    except ModuleNotFoundError as exc:
        missing = exc.name or "unknown"
        emit("ERROR", f"Dependance Python manquante: {missing}. Lancez `pip install -r requirements.txt`.")
        return None, None


def run_install() -> int:
    install, _launch = load_backend()
    if install is None:
        return 1

    try:
        install(on_log=lambda text: emit("LOG", text), on_status=lambda text: emit("STATUS", text))
        emit("STATUS", "Installation terminee")
        return 0
    except Exception as exc:  # pragma: no cover
        emit("ERROR", str(exc))
        return 1


def run_launch(username: str, ram_gb: int) -> int:
    _install, launch = load_backend()
    if launch is None:
        return 1

    try:
        launch(
            username=username,
            ram_gb=ram_gb,
            on_log=lambda text: emit("LOG", text),
            on_status=lambda text: emit("STATUS", text),
            on_crash=lambda text: emit("CRASH", text),
        )
        return 0
    except Exception as exc:  # pragma: no cover
        emit("ERROR", str(exc))
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="PoluxLauncher CLI backend")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("install", help="Install Forge and mods")

    launch_parser = subparsers.add_parser("launch", help="Launch Minecraft")
    launch_parser.add_argument("--username", default="Player", help="In-game username")
    launch_parser.add_argument("--ram-gb", type=int, default=4, help="Allocated RAM in GB")

    args = parser.parse_args()
    if args.command == "install":
        return run_install()
    if args.command == "launch":
        return run_launch(args.username, args.ram_gb)

    emit("ERROR", f"Commande non geree: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
