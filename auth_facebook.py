"""One-time setup: exchanges an OAuth authorization code for a short-lived
user token, then a long-lived user token, then looks up the Page(s) that
user manages and saves the matching Page's own (long-lived, effectively
non-expiring) access token + page id to secrets/.

Usage:
    python auth_facebook.py --account-name triphunters --code <CODE> \
        --app-id <FACEBOOK_APP_ID> --app-secret <FACEBOOK_APP_SECRET> \
        --redirect-uri https://daan029.github.io/ClipArmyAgent/ \
        --page-name "TripHunters"
"""
import argparse
import json
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import urlencode

SECRETS_DIR = Path(__file__).parent / "secrets"
API_VERSION = "v21.0"


def get(url):
    with urlopen(url) as resp:
        return json.load(resp)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account-name", required=True, help="e.g. 'triphunters'")
    parser.add_argument("--code", required=True)
    parser.add_argument("--app-id", required=True)
    parser.add_argument("--app-secret", required=True)
    parser.add_argument("--redirect-uri", required=True)
    parser.add_argument(
        "--page-name",
        help="Which Page to save if the user manages more than one. "
        "Omit if the user only manages a single Page.",
    )
    args = parser.parse_args()

    code = args.code.split("#")[0]

    # Step 1: exchange the authorization code for a short-lived user token
    short_data = get(
        f"https://graph.facebook.com/{API_VERSION}/oauth/access_token?"
        + urlencode(
            {
                "client_id": args.app_id,
                "client_secret": args.app_secret,
                "redirect_uri": args.redirect_uri,
                "code": code,
            }
        )
    )
    short_token = short_data["access_token"]

    # Step 2: exchange the short-lived user token for a long-lived one (~60 days)
    long_data = get(
        f"https://graph.facebook.com/{API_VERSION}/oauth/access_token?"
        + urlencode(
            {
                "grant_type": "fb_exchange_token",
                "client_id": args.app_id,
                "client_secret": args.app_secret,
                "fb_exchange_token": short_token,
            }
        )
    )
    long_lived_user_token = long_data["access_token"]

    # Step 3: list the Pages this user manages. Each Page's own access_token
    # here is derived from a long-lived user token, so it does NOT expire on
    # its own (only if the user token itself is revoked/the user's FB
    # password changes) - no refresh dance needed after this, unlike YouTube.
    accounts = get(
        f"https://graph.facebook.com/{API_VERSION}/me/accounts?"
        + urlencode({"access_token": long_lived_user_token})
    )["data"]

    if not accounts:
        raise SystemExit(
            "No Pages found for this user. Make sure the app has the "
            "pages_show_list, pages_read_engagement and pages_manage_posts "
            "permissions granted, and that this Facebook account is an admin "
            "of the Page."
        )

    if args.page_name:
        matches = [p for p in accounts if p["name"] == args.page_name]
        if not matches:
            names = ", ".join(p["name"] for p in accounts)
            raise SystemExit(f"Page '{args.page_name}' not found. Available: {names}")
        page = matches[0]
    elif len(accounts) == 1:
        page = accounts[0]
    else:
        names = ", ".join(p["name"] for p in accounts)
        raise SystemExit(f"Multiple Pages found, pass --page-name to pick one: {names}")

    SECRETS_DIR.mkdir(exist_ok=True)
    out_path = SECRETS_DIR / f"facebook_token_{args.account_name}.json"
    out_path.write_text(
        json.dumps(
            {
                "page_id": page["id"],
                "page_name": page["name"],
                "access_token": page["access_token"],
            },
            indent=2,
        )
    )
    print(f"Saved Page access token for '{page['name']}' (id {page['id']}) to {out_path}")


if __name__ == "__main__":
    main()
