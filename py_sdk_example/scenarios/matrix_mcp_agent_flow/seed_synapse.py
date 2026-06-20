"""seed_synapse.py prepares a local Matrix environment for the Phase 5 demo.

It:
1. Generates Synapse configuration under ``synapse-data/``.
2. Enables open registration for local testing.
3. Starts Synapse via docker compose.
4. Registers ``@admin:localhost`` and ``@openagentio-bot:localhost``.
5. Sets the ``@admin:localhost`` display name to ``Boyle Gu``.
6. Creates or reuses a demo room as ``@admin``.
7. Invites ``@openagentio-bot`` and makes it join the room.
8. Writes ``.env`` with the bot credentials and room id.

The script is idempotent where possible: existing users are logged in rather
than re-registered, and an existing room alias is reused.

Run:

    cd /Users/gubaoer/boyle_lab/learning/openagentio_example
    py_sdk_example/.venv/bin/python \
        py_sdk_example/scenarios/matrix_mcp_agent_flow/seed_synapse.py
"""

from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

import httpx


SCENARIO_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCENARIO_DIR.parents[2]
SYNAPSE_DATA = SCENARIO_DIR / "synapse-data"
HOMESERVER_URL = "http://localhost:8008"
SERVER_NAME = "localhost"
ADMIN_USER = "admin"
ADMIN_DISPLAY_NAME = "Boyle Gu"
BOT_USER = "openagentio-bot"
PASSWORD = "OpenAgentIO-Demo-2026"
ROOM_ALIAS = "#demo:localhost"
ENV_FILE = SCENARIO_DIR / ".env"


def run(cmd: list[str], *, check: bool = True, cwd: Path | None = None) -> str:
    print(f"[seed] {' '.join(cmd)}", flush=True)
    result = subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.stdout:
        print(result.stdout.strip(), flush=True)
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr, flush=True)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"command failed with exit code {result.returncode}: {' '.join(cmd)}"
        )
    return result.stdout.strip() if result.stdout else ""


def generate_synapse_config() -> None:
    """Run the Synapse Docker image to generate a homeserver.yaml."""
    if (SYNAPSE_DATA / "homeserver.yaml").exists():
        print("[seed] homeserver.yaml already exists, skipping generation")
        return

    SYNAPSE_DATA.mkdir(parents=True, exist_ok=True)
    run(
        [
            "docker",
            "run",
            "--rm",
            f"-v={SYNAPSE_DATA}:/data",
            "-e=SYNAPSE_SERVER_NAME=localhost",
            "-e=SYNAPSE_REPORT_STATS=no",
            "matrixdotorg/synapse:latest",
            "generate",
        ]
    )


def patch_homeserver_yaml() -> None:
    """Enable open registration for the local demo environment."""
    path = SYNAPSE_DATA / "homeserver.yaml"
    text = path.read_text(encoding="utf-8")

    def set_or_replace(pattern: str, replacement: str) -> None:
        nonlocal text
        if re.search(pattern, text, flags=re.MULTILINE):
            text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
        else:
            text += f"\n{replacement}\n"

    set_or_replace(r"^enable_registration:\s*\S+", "enable_registration: true")
    set_or_replace(
        r"^enable_registration_without_verification:\s*\S+",
        "enable_registration_without_verification: true",
    )

    path.write_text(text, encoding="utf-8")
    print("[seed] patched homeserver.yaml")


def docker_compose_up() -> None:
    """Start the docker compose services."""
    run(
        [
            "docker",
            "compose",
            "-f",
            str(SCENARIO_DIR / "docker-compose.yml"),
            "up",
            "-d",
        ]
    )


def wait_for_synapse(timeout: float = 60.0) -> None:
    """Wait until Synapse responds to health checks."""
    deadline = time.time() + timeout
    with httpx.Client(timeout=5.0) as client:
        while time.time() < deadline:
            try:
                resp = client.get(f"{HOMESERVER_URL}/_matrix/client/versions")
                if resp.status_code == 200:
                    print("[seed] synapse is ready")
                    return
            except httpx.RequestError:
                pass
            time.sleep(1)
    raise RuntimeError("synapse did not become ready in time")


def login(username: str, client: httpx.Client) -> str:
    """Log in an existing demo user and return an access token."""
    resp = client.post(
        f"{HOMESERVER_URL}/_matrix/client/r0/login",
        json={
            "type": "m.login.password",
            "identifier": {
                "type": "m.id.user",
                "user": username,
            },
            "password": PASSWORD,
        },
    )
    resp.raise_for_status()
    print(f"[seed] logged in @{username}:{SERVER_NAME}")
    return str(resp.json()["access_token"])


def response_errcode(resp: httpx.Response) -> str:
    """Return a Matrix errcode from an error response, if present."""
    try:
        body = resp.json()
    except ValueError:
        return ""
    if not isinstance(body, dict):
        return ""
    errcode = body.get("errcode")
    return errcode if isinstance(errcode, str) else ""


def register_or_login(username: str) -> str:
    """Register a new user or log in an existing one. Returns access token."""
    with httpx.Client(timeout=10.0) as client:
        # Synapse registration uses user-interactive auth. With local open
        # registration enabled, m.login.dummy is sufficient for this demo.
        try:
            resp = client.post(
                f"{HOMESERVER_URL}/_matrix/client/r0/register",
                json={
                    "username": username,
                    "password": PASSWORD,
                    "auth": {"type": "m.login.dummy"},
                },
            )
            if resp.status_code == 200:
                print(f"[seed] registered @{username}:{SERVER_NAME}")
                return str(resp.json()["access_token"])
            if resp.status_code in (400, 401, 403):
                error = response_errcode(resp)
                if error in {
                    "M_USER_IN_USE",
                    "M_FORBIDDEN",
                    "M_UNAUTHORIZED",
                    "M_MISSING_PARAM",
                }:
                    return login(username, client)
        except httpx.RequestError as exc:
            print(f"[seed] registration request failed: {exc}")

        return login(username, client)


def create_room(access_token: str) -> str:
    """Create the demo room with a local alias, or return existing room id."""
    with httpx.Client(timeout=10.0) as client:
        # Resolve existing alias first.
        resp = client.get(
            f"{HOMESERVER_URL}/_matrix/client/r0/directory/room/{ROOM_ALIAS}",
        )
        if resp.status_code == 200:
            room_id = resp.json().get("room_id")
            print(f"[seed] using existing room {room_id}")
            return str(room_id)

        resp = client.post(
            f"{HOMESERVER_URL}/_matrix/client/r0/createRoom",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "name": "OpenAgentIO Demo",
                "topic": "Matrix -> MCP -> SSE demo",
                "preset": "public_chat",
                "room_alias_name": "demo",
            },
        )
        resp.raise_for_status()
        room_id = resp.json()["room_id"]
        print(f"[seed] created room {room_id}")
        return str(room_id)


def join_room(access_token: str, room_id: str, username: str) -> None:
    """Ensure a demo user has joined the room."""
    user_id = f"@{username}:{SERVER_NAME}"
    with httpx.Client(timeout=10.0) as client:
        resp = client.post(
            f"{HOMESERVER_URL}/_matrix/client/r0/rooms/{room_id}/join",
            headers={"Authorization": f"Bearer {access_token}"},
            json={},
        )
        if resp.status_code not in (200, 400, 403):
            resp.raise_for_status()
    print(f"[seed] ensured {user_id} joined room")


def set_display_name(username: str, access_token: str, display_name: str) -> None:
    """Set the Matrix display name used in Element Web."""
    user_id = f"@{username}:{SERVER_NAME}"
    with httpx.Client(timeout=10.0) as client:
        resp = client.put(
            f"{HOMESERVER_URL}/_matrix/client/r0/profile/{user_id}/displayname",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"displayname": display_name},
        )
        resp.raise_for_status()
    print(f"[seed] set display name for {user_id} to {display_name!r}")


def invite_and_join(
    admin_token: str, bot_token: str, room_id: str
) -> None:
    """Invite the bot and make it join the demo room."""
    bot_user_id = f"@{BOT_USER}:{SERVER_NAME}"
    with httpx.Client(timeout=10.0) as client:
        # Invite bot.
        resp = client.post(
            f"{HOMESERVER_URL}/_matrix/client/r0/rooms/{room_id}/invite",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"user_id": bot_user_id},
        )
        if resp.status_code == 200 or resp.status_code == 403:
            # 403 may mean already invited/joined.
            pass
        else:
            resp.raise_for_status()
        print(f"[seed] invited {bot_user_id}")

        # Bot joins.
        resp = client.post(
            f"{HOMESERVER_URL}/_matrix/client/r0/rooms/{room_id}/join",
            headers={"Authorization": f"Bearer {bot_token}"},
            json={},
        )
        if resp.status_code not in (200, 400):
            resp.raise_for_status()
        print(f"[seed] {bot_user_id} joined room")


def write_env(room_id: str, bot_token: str) -> None:
    """Write the .env file used by the MatrixEventBridge config."""
    env = f"""# Auto-generated by seed_synapse.py
MATRIX_HOMESERVER_URL={HOMESERVER_URL}
MATRIX_ROOM_ID={room_id}
MATRIX_BOT_USER_ID=@{BOT_USER}:{SERVER_NAME}
MATRIX_ACCESS_TOKEN={bot_token}
"""
    ENV_FILE.write_text(env, encoding="utf-8")
    print(f"[seed] wrote {ENV_FILE}")


def main() -> None:
    print("[seed] preparing local Matrix environment")

    generate_synapse_config()
    patch_homeserver_yaml()
    docker_compose_up()
    wait_for_synapse()

    admin_token = register_or_login(ADMIN_USER)
    set_display_name(ADMIN_USER, admin_token, ADMIN_DISPLAY_NAME)
    bot_token = register_or_login(BOT_USER)

    room_id = create_room(admin_token)
    join_room(admin_token, room_id, ADMIN_USER)
    invite_and_join(admin_token, bot_token, room_id)

    write_env(room_id, bot_token)

    print("\n[seed] done. Next steps:")
    print(f"  1. Open Element Web at http://localhost:8080")
    print(f"  2. Log in as @{ADMIN_USER}:{SERVER_NAME} / password: {PASSWORD}")
    print(f"  3. Open the '#demo:localhost' room")
    print(f"  4. Run the demo agents (see README.md Phase 5)")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[seed] failed: {exc}", file=sys.stderr)
        sys.exit(1)
