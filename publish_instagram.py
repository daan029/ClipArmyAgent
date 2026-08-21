"""Publish a Reel to Instagram via Graph API (container + publish flow).

Usage:
    python publish_instagram.py --account-name klipje-nl --video-url <URL> --caption "..."
"""
import argparse
import json
import time
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


def get(url):
    with urlopen(url) as resp:
        return json.load(resp)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account-name", required=True)
    parser.add_argument("--video-url", required=True)
    parser.add_argument("--caption", required=True)
    args = parser.parse_args()

    token_data = json.loads((SECRETS_DIR / f"instagram_token_{args.account_name}.json").read_text())
    access_token = token_data["access_token"]
    ig_id = token_data["instagram_user_id"]

    try:
        create_resp = post(
            f"https://graph.instagram.com/{API_VERSION}/{ig_id}/media",
            {
                "video_url": args.video_url,
                "media_type": "REELS",
                "caption": args.caption,
                "access_token": access_token,
            },
        )
    except HTTPError as e:
        print("ERROR creating container:", e.read().decode())
        raise

    container_id = create_resp["id"]
    print(f"Container created: {container_id}, waiting for processing...")

    for _ in range(30):
        status = get(
            f"https://graph.instagram.com/{API_VERSION}/{container_id}?"
            + urlencode({"fields": "status_code,status", "access_token": access_token})
        )
        code = status.get("status_code")
        print("Status:", code)
        if code == "FINISHED":
            break
        if code == "ERROR":
            print("Container failed:", status)
            return
        time.sleep(10)
    else:
        print("Timed out waiting for container to finish processing.")
        return

    try:
        publish_resp = post(
            f"https://graph.instagram.com/{API_VERSION}/{ig_id}/media_publish",
            {"creation_id": container_id, "access_token": access_token},
        )
    except HTTPError as e:
        print("ERROR publishing:", e.read().decode())
        raise

    print("Published. Media ID:", publish_resp.get("id"))


if __name__ == "__main__":
    main()
