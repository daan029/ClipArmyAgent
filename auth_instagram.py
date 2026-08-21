"""One-time setup: exchanges a short-lived Instagram token for a long-lived one
and saves it, together with the Instagram user id, to secrets/.

Usage:
    python auth_instagram.py --account-name klipje-nl --short-token <TOKEN> --app-secret <SECRET>
"""
import argparse
import json
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlencode

SECRETS_DIR = Path(__file__).parent / "secrets"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account-name", required=True, help="e.g. 'klipje-nl'")
    parser.add_argument("--short-token", required=True)
    parser.add_argument("--app-secret", required=True)
    args = parser.parse_args()

    exchange_url = "https://graph.instagram.com/access_token?" + urlencode(
        {
            "grant_type": "ig_exchange_token",
            "client_secret": args.app_secret,
            "access_token": args.short_token,
        }
    )
    with urlopen(exchange_url) as resp:
        exchange_data = json.load(resp)

    long_lived_token = exchange_data["access_token"]

    me_url = "https://graph.instagram.com/me?" + urlencode(
        {"fields": "id,username", "access_token": long_lived_token}
    )
    with urlopen(me_url) as resp:
        me_data = json.load(resp)

    SECRETS_DIR.mkdir(exist_ok=True)
    out_path = SECRETS_DIR / f"instagram_token_{args.account_name}.json"
    out_path.write_text(
        json.dumps(
            {
                "access_token": long_lived_token,
                "expires_in_seconds": exchange_data.get("expires_in"),
                "instagram_user_id": me_data["id"],
                "username": me_data.get("username"),
            },
            indent=2,
        )
    )
    print(f"Saved long-lived token for '{me_data.get('username')}' to {out_path}")
    print(f"Expires in ~{exchange_data.get('expires_in', 0) // 86400} days")


if __name__ == "__main__":
    main()
