"""Publish a 2-item (image + video) carousel to Instagram via Graph API.

Usage:
    python publish_instagram_carousel.py --account-name klipje-nl \
        --image-url <URL> --video-url <URL> --caption "..."
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


def wait_for_container(container_id, access_token):
    for _ in range(30):
        status = get(
            f"https://graph.instagram.com/{API_VERSION}/{container_id}?"
            + urlencode({"fields": "status_code,status", "access_token": access_token})
        )
        code = status.get("status_code")
        print(f"  {container_id} status:", code)
        if code == "FINISHED":
            return
        if code == "ERROR":
            raise RuntimeError(f"Container {container_id} failed: {status}")
        time.sleep(10)
    raise TimeoutError(f"Timed out waiting for container {container_id}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account-name", required=True)
    parser.add_argument("--image-url", required=True)
    parser.add_argument("--video-url", required=True)
    parser.add_argument("--caption", required=True)
    parser.add_argument("--dry-run", action="store_true", help="Create+wait on child containers but stop before media_publish.")
    args = parser.parse_args()

    token_data = json.loads((SECRETS_DIR / f"instagram_token_{args.account_name}.json").read_text())
    access_token = token_data["access_token"]
    ig_id = token_data["instagram_user_id"]

    print("Creating image child container...")
    image_resp = post(
        f"https://graph.instagram.com/{API_VERSION}/{ig_id}/media",
        {"image_url": args.image_url, "is_carousel_item": "true", "access_token": access_token},
    )
    image_container_id = image_resp["id"]
    print("  ->", image_container_id)

    print("Creating video child container...")
    video_resp = post(
        f"https://graph.instagram.com/{API_VERSION}/{ig_id}/media",
        {
            "video_url": args.video_url,
            "media_type": "VIDEO",
            "is_carousel_item": "true",
            "access_token": access_token,
        },
    )
    video_container_id = video_resp["id"]
    print("  ->", video_container_id)

    print("Waiting for child containers to process...")
    wait_for_container(image_container_id, access_token)
    wait_for_container(video_container_id, access_token)

    print("Creating carousel parent container...")
    carousel_resp = post(
        f"https://graph.instagram.com/{API_VERSION}/{ig_id}/media",
        {
            "media_type": "CAROUSEL",
            "children": f"{image_container_id},{video_container_id}",
            "caption": args.caption,
            "access_token": access_token,
        },
    )
    carousel_container_id = carousel_resp["id"]
    print("  ->", carousel_container_id)
    wait_for_container(carousel_container_id, access_token)

    if args.dry_run:
        print(f"DRY RUN: carousel container {carousel_container_id} is ready but NOT published.")
        return

    print("Publishing carousel...")
    publish_resp = post(
        f"https://graph.instagram.com/{API_VERSION}/{ig_id}/media_publish",
        {"creation_id": carousel_container_id, "access_token": access_token},
    )
    print("Published. Media ID:", publish_resp.get("id"))


if __name__ == "__main__":
    main()
