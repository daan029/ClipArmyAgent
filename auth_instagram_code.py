"""One-time setup: exchanges an OAuth authorization code for a short-lived
Instagram token, then a long-lived token, and saves it + the IG user id.

Usage:
    python auth_instagram_code.py --account-name klipje-nl --code <CODE> \
        --ig-app-id <INSTAGRAM_APP_ID> --ig-app-secret <INSTAGRAM_APP_SECRET> \
        --redirect-uri https://daan029.github.io/ClipArmyAgent/
"""
import argparse
import json
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import urlencode

SECRETS_DIR = Path(__file__).parent / "secrets"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account-name", required=True)
    parser.add_argument("--code", required=True)
    parser.add_argument("--ig-app-id", required=True)
    parser.add_argument("--ig-app-secret", required=True)
    parser.add_argument("--redirect-uri", required=True)
    args = parser.parse_args()

    code = args.code.split("#")[0]

    # Step 1: exchange the authorization code for a short-lived token
    data = urlencode(
        {
            "client_id": args.ig_app_id,
            "client_secret": args.ig_app_secret,
            "grant_type": "authorization_code",
            "redirect_uri": args.redirect_uri,
            "code": code,
        }
    ).encode()
    req = Request("https://api.instagram.com/oauth/access_token", data=data, method="POST")
    with urlopen(req) as resp:
        short_data = json.load(resp)

    short_token = short_data["access_token"]

    # Step 2: exchange the short-lived token for a long-lived one
    exchange_url = "https://graph.instagram.com/access_token?" + urlencode(
        {
            "grant_type": "ig_exchange_token",
            "client_secret": args.ig_app_secret,
            "access_token": short_token,
        }
    )
    with urlopen(exchange_url) as resp:
        long_data = json.load(resp)

    long_lived_token = long_data["access_token"]

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
                "expires_in_seconds": long_data.get("expires_in"),
                "instagram_user_id": me_data["id"],
                "username": me_data.get("username"),
            },
            indent=2,
        )
    )
    print(f"Saved long-lived token for '{me_data.get('username')}' to {out_path}")
    print(f"Expires in ~{long_data.get('expires_in', 0) // 86400} days")


if __name__ == "__main__":
    main()
