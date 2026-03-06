import argparse
import json
import sys


def emit(kind: str, message: str) -> None:
    lines = str(message).split("\n")
    if not lines:
        lines = [""]
    for line in lines:
        print(f"[{kind}] {line}", flush=True)


def emit_data(payload: dict) -> None:
    emit("DATA", json.dumps(payload, ensure_ascii=False))


def load_backend():
    try:
        from launcher_core import (
            complete_microsoft_login,
            get_auth_status,
            install,
            launch,
            logout_microsoft,
            start_microsoft_login,
        )

        return install, launch, get_auth_status, start_microsoft_login, complete_microsoft_login, logout_microsoft
    except ModuleNotFoundError as exc:
        missing = exc.name or "unknown"
        emit("ERROR", f"Dependance Python manquante: {missing}. Lancez `pip install -r requirements.txt`.")
        return None, None, None, None, None, None


def run_install() -> int:
    install, _launch, _auth_status, _auth_start, _auth_complete, _auth_logout = load_backend()
    if install is None:
        return 1

    try:
        install(on_log=lambda text: emit("LOG", text), on_status=lambda text: emit("STATUS", text))
        emit("STATUS", "Installation terminee")
        return 0
    except Exception as exc:  # pragma: no cover
        emit("ERROR", str(exc))
        return 1


def run_launch(username: str, ram_gb: int, account_mode: str) -> int:
    _install, launch, _auth_status, _auth_start, _auth_complete, _auth_logout = load_backend()
    if launch is None:
        return 1

    try:
        launch(
            username=username,
            ram_gb=ram_gb,
            account_mode=account_mode,
            on_log=lambda text: emit("LOG", text),
            on_status=lambda text: emit("STATUS", text),
            on_crash=lambda text: emit("CRASH", text),
        )
        return 0
    except Exception as exc:  # pragma: no cover
        emit("ERROR", str(exc))
        return 1


def run_auth_status() -> int:
    _install, _launch, auth_status, _auth_start, _auth_complete, _auth_logout = load_backend()
    if auth_status is None:
        return 1

    try:
        emit_data(auth_status())
        return 0
    except Exception as exc:  # pragma: no cover
        emit("ERROR", str(exc))
        return 1


def run_auth_start() -> int:
    _install, _launch, _auth_status, auth_start, _auth_complete, _auth_logout = load_backend()
    if auth_start is None:
        return 1

    try:
        emit_data(auth_start())
        return 0
    except Exception as exc:  # pragma: no cover
        emit("ERROR", str(exc))
        return 1


def run_auth_complete(redirect_url: str) -> int:
    _install, _launch, _auth_status, _auth_start, auth_complete, _auth_logout = load_backend()
    if auth_complete is None:
        return 1

    try:
        emit_data(auth_complete(redirect_url))
        return 0
    except Exception as exc:  # pragma: no cover
        emit("ERROR", str(exc))
        return 1


def run_auth_logout() -> int:
    _install, _launch, _auth_status, _auth_start, _auth_complete, auth_logout = load_backend()
    if auth_logout is None:
        return 1

    try:
        emit_data(auth_logout())
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
    launch_parser.add_argument("--account-mode", choices=["offline", "microsoft"], default="offline")

    subparsers.add_parser("auth-status", help="Get Microsoft auth status")
    subparsers.add_parser("auth-start", help="Start Microsoft auth flow")
    auth_complete_parser = subparsers.add_parser("auth-complete", help="Complete Microsoft auth flow")
    auth_complete_parser.add_argument("--redirect-url", required=True, help="OAuth redirect URL to parse")
    subparsers.add_parser("auth-logout", help="Forget Microsoft session")

    args = parser.parse_args()
    if args.command == "install":
        return run_install()
    if args.command == "launch":
        return run_launch(args.username, args.ram_gb, args.account_mode)
    if args.command == "auth-status":
        return run_auth_status()
    if args.command == "auth-start":
        return run_auth_start()
    if args.command == "auth-complete":
        return run_auth_complete(args.redirect_url)
    if args.command == "auth-logout":
        return run_auth_logout()

    emit("ERROR", f"Commande non geree: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
