"""Publish a Reel to a Facebook Page via Graph API's Reels resumable-upload
flow (start -> binary upload -> finish). Not the classic /{page-id}/videos
endpoint - that publishes as a regular Page video post, which ClipArmy's
submission form can't read a post time from (it specifically wants a public
Reel URL/link). Supports a local file or an already-hosted URL.

Usage:
    python upload_facebook.py --account-name triphunters --video-file clip.mp4 --caption "..."
    python upload_facebook.py --account-name triphunters --video-url <URL> --caption "..."
"""
import argparse
import json
import time
from pathlib import Path

import requests

SECRETS_DIR = Path(__file__).parent / "secrets"
API_VERSION = "v21.0"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account-name", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--video-file", help="Local video file to upload directly.")
    group.add_argument("--video-url", help="Publicly reachable URL Facebook will fetch server-side.")
    parser.add_argument("--caption", required=True)
    args = parser.parse_args()

    token_data = json.loads((SECRETS_DIR / f"facebook_token_{args.account_name}.json").read_text())
    access_token = token_data["access_token"]
    page_id = token_data["page_id"]

    # Step 1: start an upload session
    start = requests.post(
        f"https://graph.facebook.com/{API_VERSION}/{page_id}/video_reels",
        data={"upload_phase": "start", "access_token": access_token},
    ).json()
    if "video_id" not in start:
        raise SystemExit(f"start failed: {start}")
    video_id = start["video_id"]
    upload_url = start["upload_url"]
    print(f"Upload session started, video_id={video_id}")

    # Step 2: upload the video bytes
    if args.video_file:
        video_path = Path(args.video_file)
        file_size = video_path.stat().st_size
        with open(video_path, "rb") as f:
            video_bytes = f.read()
        upload_resp = requests.post(
            upload_url,
            headers={
                "Authorization": f"OAuth {access_token}",
                "offset": "0",
                "file_size": str(file_size),
            },
            data=video_bytes,
        )
    else:
        upload_resp = requests.post(
            upload_url,
            headers={
                "Authorization": f"OAuth {access_token}",
                "offset": "0",
                "file_url": args.video_url,
            },
        )
    if not upload_resp.ok:
        raise SystemExit(f"upload failed: {upload_resp.text}")
    print("Upload complete:", upload_resp.json())

    # Step 3: finish - actually publish it
    finish = requests.post(
        f"https://graph.facebook.com/{API_VERSION}/{page_id}/video_reels",
        data={
            "upload_phase": "finish",
            "video_id": video_id,
            "video_state": "PUBLISHED",
            "description": args.caption,
            "access_token": access_token,
        },
    ).json()
    if not finish.get("success"):
        raise SystemExit(f"finish failed: {finish}")

    # Step 4: poll until Facebook has finished processing it
    for _ in range(30):
        status = requests.get(
            f"https://graph.facebook.com/{API_VERSION}/{video_id}",
            params={"fields": "status", "access_token": access_token},
        ).json()
        video_status = status.get("status", {}).get("video_status")
        print("Processing status:", video_status)
        if video_status == "ready":
            break
        time.sleep(5)

    print(f"Published. Video ID: {video_id}")
    print(f"URL: https://www.facebook.com/reel/{video_id}")


if __name__ == "__main__":
    main()
