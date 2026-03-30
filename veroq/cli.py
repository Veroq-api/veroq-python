"""VEROQ CLI — authenticate via GitHub and manage credentials."""

import argparse
import json
import os
import socket
import stat
import sys
import time
import webbrowser

import requests

GITHUB_CLIENT_ID = "Ov23ligfgbZkJDvu8JwO"
GITHUB_DEVICE_CODE_URL = "https://github.com/login/device/code"
GITHUB_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
VEROQ_API_URL = "https://api.thepolarisreport.com"
CREDENTIALS_DIR = os.path.expanduser("~/.veroq")
CREDENTIALS_FILE = os.path.join(CREDENTIALS_DIR, "credentials")
# Backwards compatibility: also check legacy path
LEGACY_CREDENTIALS_DIR = os.path.expanduser("~/.polaris")
LEGACY_CREDENTIALS_FILE = os.path.join(LEGACY_CREDENTIALS_DIR, "credentials")


def _read_credentials():
    """Read API key from ~/.veroq/credentials or ~/.polaris/credentials. Returns key string or None."""
    for cred_file in [CREDENTIALS_FILE, LEGACY_CREDENTIALS_FILE]:
        try:
            with open(cred_file, "r") as f:
                key = f.read().strip()
                if key:
                    return key
        except (OSError, IOError):
            continue
    return None


def login():
    """Authenticate via GitHub device flow and save a VEROQ API key."""
    # Step 1: Request device code
    resp = requests.post(
        GITHUB_DEVICE_CODE_URL,
        data={"client_id": GITHUB_CLIENT_ID, "scope": "user:email"},
        headers={"Accept": "application/json"},
    )
    if resp.status_code != 200:
        print("Failed to initiate GitHub device flow.", file=sys.stderr)
        sys.exit(1)

    data = resp.json()
    device_code = data["device_code"]
    user_code = data["user_code"]
    verification_uri = data["verification_uri"]
    interval = data.get("interval", 5)
    expires_in = data.get("expires_in", 900)

    print()
    print("  Go to: {}".format(verification_uri))
    print("  Enter code: {}".format(user_code))
    print()

    # Try to open browser
    try:
        webbrowser.open(verification_uri)
    except Exception:
        pass

    print("Waiting for authorization...", end="", flush=True)

    # Step 2: Poll for access token
    deadline = time.time() + expires_in
    gh_access_token = None

    while time.time() < deadline:
        time.sleep(interval)
        print(".", end="", flush=True)

        token_resp = requests.post(
            GITHUB_ACCESS_TOKEN_URL,
            data={
                "client_id": GITHUB_CLIENT_ID,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_resp.json()

        error = token_data.get("error")
        if error == "authorization_pending":
            continue
        elif error == "slow_down":
            interval = token_data.get("interval", interval + 5)
            continue
        elif error == "expired_token":
            print("\nDevice code expired. Please try again.", file=sys.stderr)
            sys.exit(1)
        elif error == "access_denied":
            print("\nAuthorization denied.", file=sys.stderr)
            sys.exit(1)
        elif error:
            print("\nGitHub error: {}".format(error), file=sys.stderr)
            sys.exit(1)

        gh_access_token = token_data.get("access_token")
        if gh_access_token:
            break

    if not gh_access_token:
        print("\nTimed out waiting for authorization.", file=sys.stderr)
        sys.exit(1)

    print(" authorized!")

    # Step 3: Exchange GitHub token for API JWT
    auth_resp = requests.post(
        "{}/api/v1/auth/github/device".format(VEROQ_API_URL),
        json={"access_token": gh_access_token},
    )
    if auth_resp.status_code != 200:
        msg = auth_resp.json().get("message", "Authentication failed")
        print("Auth error: {}".format(msg), file=sys.stderr)
        sys.exit(1)

    auth_data = auth_resp.json()
    jwt_token = auth_data["token"]
    email = auth_data.get("email", "")

    # Step 4: Create an API key
    hostname = socket.gethostname()
    key_resp = requests.post(
        "{}/api/v1/keys/create".format(VEROQ_API_URL),
        json={"name": "CLI ({})".format(hostname)},
        headers={"Authorization": "Bearer {}".format(jwt_token)},
    )
    if key_resp.status_code != 200:
        msg = key_resp.json().get("message", "Failed to create API key")
        print("Key creation error: {}".format(msg), file=sys.stderr)
        sys.exit(1)

    api_key = key_resp.json()["key"]

    # Step 5: Save credentials
    os.makedirs(CREDENTIALS_DIR, mode=0o700, exist_ok=True)
    with open(CREDENTIALS_FILE, "w") as f:
        f.write(api_key)
    os.chmod(CREDENTIALS_FILE, stat.S_IRUSR | stat.S_IWUSR)

    print()
    print("Authenticated as {} — API key saved to ~/.veroq/credentials".format(email))


def whoami():
    """Show the currently authenticated user."""
    api_key = os.environ.get("VEROQ_API_KEY") or os.environ.get("POLARIS_API_KEY") or _read_credentials()
    if not api_key:
        print("Not logged in. Run `veroq login` to authenticate.", file=sys.stderr)
        sys.exit(1)

    resp = requests.get(
        "{}/api/v1/user/api-keys".format(VEROQ_API_URL),
        headers={"Authorization": "Bearer {}".format(api_key)},
    )
    if resp.status_code == 401:
        print("Invalid or expired API key. Run `veroq login` to re-authenticate.", file=sys.stderr)
        sys.exit(1)
    if resp.status_code != 200:
        print("Error checking credentials (HTTP {}).".format(resp.status_code), file=sys.stderr)
        sys.exit(1)

    data = resp.json()
    print("Logged in — key prefix: {}".format(api_key[:12]))
    keys = data.get("keys", [])
    if keys:
        print("Active keys: {}".format(len(keys)))


def logout():
    """Remove stored credentials."""
    removed = False
    for cred_file in [CREDENTIALS_FILE, LEGACY_CREDENTIALS_FILE]:
        if os.path.exists(cred_file):
            os.remove(cred_file)
            removed = True
    if removed:
        print("Logged out — credentials removed.")
    else:
        print("No credentials found.")


def main():
    parser = argparse.ArgumentParser(prog="veroq", description="VEROQ CLI — verified intelligence for AI agents")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("login", help="Authenticate via GitHub")
    sub.add_parser("whoami", help="Show current authentication status")
    sub.add_parser("logout", help="Remove stored credentials")

    args = parser.parse_args()

    if args.command == "login":
        login()
    elif args.command == "whoami":
        whoami()
    elif args.command == "logout":
        logout()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
