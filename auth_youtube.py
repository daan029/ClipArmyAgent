"""One-time setup: obtains a YouTube refresh token via browser login.

Run this once per channel. It opens a browser window for you to log in and
approve access, then saves a refresh token to secrets/youtube_token.json.
"""
import argparse
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRET_FILE = Path(__file__).parent / "secrets" / "youtube_client_secret.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--account-name",
        required=True,
        help="Label for this channel's token file, e.g. 'klipje-nl'",
    )
    args = parser.parse_args()

    token_path = Path(__file__).parent / "secrets" / f"youtube_token_{args.account_name}.json"

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_FILE), SCOPES)
    credentials = flow.run_local_server(port=0)

    token_path.write_text(credentials.to_json())
    print(f"Saved token for '{args.account_name}' to {token_path}")


if __name__ == "__main__":
    main()
