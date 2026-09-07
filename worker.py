"""Poll the creator-dashboard queue for 'requested' jobs and process the ones we can
handle fully locally (Path A: one long source video - livestream VOD, podcast episode,
etc). See docs in creator-dashboard/README.md ("Campagne -> video -> juiste account")
for the full picture; this script is the "local worker" referenced there.

Path A (this script): brief links a single video (YouTube/Twitch VOD) -> transcribe,
score viral moments, cut+caption the best one, upload the preview, done.

Path B (B-roll campaigns, e.g. Moco Museum): the brief links a Google Drive *folder* of
short clips instead of one long video. Picking which clips are good is a visual
judgement call that needs Higgsfield's video_analysis_create (only available inside a
Claude session) - this script just downloads the folder and marks the job
'awaiting_analysis'; a Claude Code session finishes those by hand (see build_fast_montage.py).

Jobs whose brief doesn't yield a clear source at all (e.g. "tonight's livestream" before
it has happened) are marked 'needs_source' - paste the real URL into source_url via the
dashboard's queue page once it exists, and the next poll picks it up.

Usage:
    python worker.py            # poll forever
    python worker.py --once     # single pass (good for Task Scheduler / manual runs)

Config (env vars, or a local .env file - see .env.example):
    DASHBOARD_URL              e.g. http://localhost:3000 (or the deployed URL)
    WORKER_API_TOKEN           must match creator-dashboard's WORKER_API_TOKEN - the only
                                credential this script needs against the dashboard; video
                                uploads go through /api/worker/jobs/[id]/upload, which holds
                                the real Supabase key server-side.
    ANTHROPIC_API_KEY          or secrets/anthropic_api_key.txt (see clipper/find_moments.py)
"""
import argparse
import json
import os
import re
import shutil
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

# This machine's Python doesn't trust the local SSL cert chain that plain
# requests/certifi accept fine elsewhere (same root cause as
# download_drive_folder.py's truststore use) - affects yt-dlp, the dashboard
# API calls, and the Google Docs brief fetch below. Fix once, globally, before
# any network call.
import truststore

truststore.inject_into_ssl()

REPO_ROOT = Path(__file__).resolve().parent
POLL_INTERVAL_SECONDS = 60

# Long-form single-video sources we know how to hand to yt-dlp. Deliberately does NOT
# include tiktok.com/instagram.com links - in real campaign briefs those are short
# reference/example clips, not the raw footage to cut from (see campaign.example_video_urls
# in creator-dashboard - those are "style examples", the actual source is in the brief).
# Scheme is optional - real briefs sometimes write "youtu.be/xyz" with no "https://".
SOURCE_URL_PATTERNS = [
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+"),
    re.compile(r"(?:https?://)?youtu\.be/[\w-]+"),
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/shorts/[\w-]+"),
    re.compile(r"(?:https?://)?(?:www\.)?twitch\.tv/videos/\d+"),
]
DRIVE_FOLDER_PATTERN = re.compile(r"(?:https?://)?drive\.google\.com/drive/folders/[\w-]+")
GDOC_ID_PATTERN = re.compile(r"docs\.google\.com/document/d/([\w-]+)")


def normalize_url(url: str) -> str:
    return url if url.startswith("http") else f"https://{url}"


def load_dotenv() -> None:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug or "campaign"


def dashboard_request(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{os.environ['DASHBOARD_URL'].rstrip('/')}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {os.environ['WORKER_API_TOKEN']}")
    req.add_header("Content-Type", "application/json")
    with urlopen(req) as resp:
        return json.loads(resp.read())


def get_requested_jobs() -> list[dict]:
    return dashboard_request("GET", "/api/worker/jobs?status=requested")["jobs"]


def patch_job(job_id: str, patch: dict) -> None:
    dashboard_request("PATCH", f"/api/worker/jobs/{job_id}", patch)


def fetch_brief_text(brief_url: str) -> str | None:
    match = GDOC_ID_PATTERN.search(brief_url)
    if not match:
        return None
    export_url = f"https://docs.google.com/document/d/{match.group(1)}/export?format=txt"
    try:
        with urlopen(export_url) as resp:
            return resp.read().decode("utf-8")
    except HTTPError as e:
        print(f"  brief fetch failed ({e.code}) - doc may not be link-shared")
        return None


def find_source_url(text: str) -> str | None:
    for pattern in SOURCE_URL_PATTERNS:
        m = pattern.search(text)
        if m:
            return normalize_url(m.group(0))
    return None


def find_drive_folder_url(text: str) -> str | None:
    m = DRIVE_FOLDER_PATTERN.search(text)
    return normalize_url(m.group(0)) if m else None


def upload_preview(job_id: str, local_path: Path) -> str:
    # Goes through the dashboard's own worker API (POST /api/worker/jobs/[id]/upload)
    # rather than talking to Supabase Storage directly - the worker only ever needs
    # WORKER_API_TOKEN, never a key that can touch the rest of the database.
    url = f"{os.environ['DASHBOARD_URL'].rstrip('/')}/api/worker/jobs/{job_id}/upload"
    req = Request(url, data=local_path.read_bytes(), method="POST")
    req.add_header("Authorization", f"Bearer {os.environ['WORKER_API_TOKEN']}")
    req.add_header("Content-Type", "video/mp4")
    with urlopen(req) as resp:
        return json.loads(resp.read())["url"]


def process_path_a(job: dict, source_url: str, brief_text: str) -> None:
    from make_viral_clips import run as make_viral_clips_run

    print(f"  [Path A] source={source_url}")
    patch_job(job["id"], {"status": "generating", "source_url": source_url, "brief_text": brief_text})

    campaign_slug = slugify(job["campaign_title"])
    out_dir = make_viral_clips_run(source=source_url, campaign=campaign_slug, n=3, language=job["language"])

    report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    top = report[0]
    clip_path = out_dir / top["clip"]

    print(f"  uploading {clip_path.name} (score={top['virality_score']})...")
    public_url = upload_preview(job["id"], clip_path)

    patch_job(
        job["id"],
        {
            "status": "ready_for_review",
            "video_asset_url": public_url,
            "caption": top.get("hook_text") or job["campaign_title"],
        },
    )
    print(f"  done -> {public_url}")

    # The downloaded source (often hundreds of MB) has done its job once the
    # preview is uploaded - don't let it pile up locally across campaigns.
    # The short generated clips (a few MB each, useful as alternates) stay.
    download_dir = out_dir / "download"
    if download_dir.exists():
        shutil.rmtree(download_dir, ignore_errors=True)
        print(f"  cleaned up {download_dir}")


def process_path_b(job: dict, drive_folder_url: str, brief_text: str) -> None:
    from download_drive_folder import download_drive_folder

    print(f"  [Path B] B-roll folder={drive_folder_url}")
    campaign_slug = slugify(job["campaign_title"])
    out_dir = REPO_ROOT / "clips" / campaign_slug / "source"

    succeeded, failed = download_drive_folder(drive_folder_url, str(out_dir))
    print(f"  downloaded {len(succeeded)} file(s), {len(failed)} failed -> {out_dir}")

    patch_job(
        job["id"],
        {"status": "awaiting_analysis", "source_url": drive_folder_url, "brief_text": brief_text},
    )
    print("  needs a Claude session to pick highlights (video_analysis_create) - see build_fast_montage.py")


def process_job(job: dict) -> None:
    print(f"Job {job['id']} - {job['campaign_title']}")
    try:
        brief_text = fetch_brief_text(job["brief_url"]) if job.get("brief_url") else None
        search_text = " ".join(filter(None, [brief_text, job.get("description"), job.get("rules")]))

        drive_folder_url = find_drive_folder_url(search_text)
        source_url = find_source_url(search_text)

        if source_url:
            process_path_a(job, source_url, brief_text or "")
        elif drive_folder_url:
            process_path_b(job, drive_folder_url, brief_text or "")
        else:
            print("  no usable source found in brief - marking needs_source")
            patch_job(job["id"], {"status": "needs_source", "brief_text": brief_text or ""})
    except Exception as e:
        print(f"  FAILED: {e}")
        patch_job(job["id"], {"status": "failed", "error_message": str(e)})


def main():
    load_dotenv()
    ap = argparse.ArgumentParser(description="Local worker for the creator-dashboard video queue.")
    ap.add_argument("--once", action="store_true", help="Process the current queue once and exit.")
    args = ap.parse_args()

    while True:
        jobs = get_requested_jobs()
        if not jobs:
            print("No requested jobs.")
        for job in jobs:
            process_job(job)

        if args.once:
            break
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
