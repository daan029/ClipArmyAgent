"""Upload a video to YouTube, optionally scheduled for future publish.

Usage:
    python upload_youtube.py --account-name klipje-nl --video-file clips/supergaande/clip_01.mp4 \
        --title "..." --description "..." --publish-at 2026-08-21T17:00:00Z
"""
import argparse
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SECRETS_DIR = Path(__file__).parent / "secrets"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account-name", required=True)
    parser.add_argument("--video-file", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--publish-at", help="RFC3339 UTC timestamp, e.g. 2026-08-21T17:00:00Z. Omit to publish immediately as public.")
    parser.add_argument("--category-id", default="24")
    parser.add_argument("--tags", nargs="*", default=[])
    args = parser.parse_args()

    token_path = SECRETS_DIR / f"youtube_token_{args.account_name}.json"
    creds = Credentials.from_authorized_user_file(str(token_path))
    youtube = build("youtube", "v3", credentials=creds)

    status = {"selfDeclaredMadeForKids": False}
    if args.publish_at:
        status["privacyStatus"] = "private"
        status["publishAt"] = args.publish_at
    else:
        status["privacyStatus"] = "public"

    body = {
        "snippet": {
            "title": args.title,
            "description": args.description,
            "tags": args.tags,
            "categoryId": args.category_id,
        },
        "status": status,
    }

    media = MediaFileUpload(args.video_file, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()
    print(f"Uploaded. Video ID: {response['id']}")
    print(f"URL: https://youtube.com/shorts/{response['id']}")
    if args.publish_at:
        print(f"Scheduled to publish at: {args.publish_at}")


if __name__ == "__main__":
    main()
