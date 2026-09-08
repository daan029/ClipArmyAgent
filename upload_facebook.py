"""Publish a video to a Facebook Page via Graph API, pointing at an
already-hosted video URL (no local upload needed - same pattern as
publish_instagram.py).

Usage:
    python upload_facebook.py --account-name triphunters --video-url <URL> --caption "..."
"""
import argparse
import json
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import HTTPError

SECRETS_DIR = Path(__file__).parent / "secrets"
API_VERSION = "v21.0"


def post(url, data):
    req = Request(url, data=urlencode(data).encode(), method="POST")
    with urlopen(req) as resp:
        return json.load(resp)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account-name", required=True)
    parser.add_argument("--video-url", required=True)
    parser.add_argument("--caption", required=True)
    args = parser.parse_args()

    token_data = json.loads((SECRETS_DIR / f"facebook_token_{args.account_name}.json").read_text())
    access_token = token_data["access_token"]
    page_id = token_data["page_id"]

    try:
        resp = post(
            f"https://graph-video.facebook.com/{API_VERSION}/{page_id}/videos",
            {
                "file_url": args.video_url,
                "description": args.caption,
                "access_token": access_token,
            },
        )
    except HTTPError as e:
        print("ERROR publishing:", e.read().decode())
        raise

    video_id = resp["id"]
    print(f"Published. Video ID: {video_id}")
    print(f"URL: https://www.facebook.com/{page_id}/videos/{video_id}")


if __name__ == "__main__":
    main()
