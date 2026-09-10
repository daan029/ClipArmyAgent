"""
Bulk-download every file in a public (anyone-with-the-link) Google Drive
folder — no Drive API/OAuth credentials needed. Built to replace the
"ask Daan to download the B-roll and drop it locally" step for campaign
briefs that link a Drive folder.

Requires: pip install gdown truststore
truststore is used because this machine's Python doesn't trust the local
SSL cert chain that plain `requests`/certifi accepts fine for other hosts.

gdown's own download_folder() aborts the whole batch on the first file
that fails Google's confirm-token dance (seen in practice on ~1 file out
of ~66 for a real campaign folder, not tied to any one specific file).
This script instead fetches the manifest once (skip_download=True) and
downloads file-by-file with try/except + retries, so one flaky file
doesn't block the rest.

Usage:
    python download_drive_folder.py --url "https://drive.google.com/drive/folders/<ID>" --out clips/moco_london/source
"""
import argparse
import time
from pathlib import Path

import truststore

truststore.inject_into_ssl()

import gdown  # noqa: E402


def download_drive_folder(url: str, out_dir: str, retries: int = 3, retry_delay: float = 5.0) -> tuple[list[str], list[str]]:
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    manifest = gdown.download_folder(url=url, output=out_dir, quiet=False, use_cookies=False, skip_download=True)
    print(f"Folder manifest: {len(manifest)} files")

    succeeded, failed = [], []
    pending = list(manifest)

    for attempt in range(1, retries + 1):
        if not pending:
            break
        still_pending = []
        for item in pending:
            local_path = item.local_path
            if Path(local_path).exists() and Path(local_path).stat().st_size > 0:
                succeeded.append(local_path)
                continue
            try:
                gdown.download(id=item.id, output=local_path, quiet=False, use_cookies=False, resume=True)
                succeeded.append(local_path)
            except Exception as e:
                print(f"[attempt {attempt}] FAILED {item.path}: {e}")
                still_pending.append(item)
        pending = still_pending
        if pending and attempt < retries:
            print(f"Retrying {len(pending)} failed file(s) in {retry_delay:.0f}s...")
            time.sleep(retry_delay)

    failed = [item.path for item in pending]
    return succeeded, failed


def main():
    ap = argparse.ArgumentParser(description="Bulk-download a public Google Drive folder file-by-file, tolerating individual failures.")
    ap.add_argument("--url", required=True, help="Google Drive folder URL (must be 'anyone with the link' shared)")
    ap.add_argument("--out", required=True, help="Local output directory")
    ap.add_argument("--retries", type=int, default=3)
    args = ap.parse_args()

    succeeded, failed = download_drive_folder(args.url, args.out, retries=args.retries)

    print(f"\nDone: {len(succeeded)} downloaded, {len(failed)} failed.")
    if failed:
        print("Failed files:")
        for f in failed:
            print(f"  - {f}")


if __name__ == "__main__":
    main()
