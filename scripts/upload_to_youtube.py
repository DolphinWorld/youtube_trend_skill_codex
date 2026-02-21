#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CLIENT_SECRET = ROOT / "config" / "youtube_client_secret.json"
DEFAULT_TOKEN_FILE = ROOT / "config" / "youtube_token.json"


def get_youtube_service(client_secret_path: Path, token_path: Path):
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), SCOPES)
            flow.redirect_uri = "http://127.0.0.1:8080/"
            print("OAuth redirect_uri:", flow.redirect_uri)
            creds = flow.run_local_server(host="127.0.0.1", port=8080, open_browser=False, authorization_prompt_message="Please visit this URL to authorize this application: {url}")

        token_path.write_text(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def upload_video(
    service,
    video_path: Path,
    title: str,
    description: str,
    tags: list[str],
    category_id: str,
    privacy_status: str,
):
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
    request = service.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        _status, response = request.next_chunk()

    return response["id"]


def main():
    parser = argparse.ArgumentParser(description="Upload MP4 to YouTube")
    parser.add_argument("--video", default=str(ROOT / "outputs" / "internet_users_top_countries_history.mp4"))
    parser.add_argument("--title", default="Top Countries by Internet Users (1990-2021) | History Animation")
    parser.add_argument(
        "--description",
        default=(
            "Historical comparison of top countries by number of Internet users (1990-2021).\\n"
            "Data source: Our World in Data historical internet users dataset.\\n"
            "Music: YouTube Audio Library track used under license terms."
        ),
    )
    parser.add_argument("--tags", default="internet,history,data visualization,countries,technology")
    parser.add_argument("--category-id", default="27", help="27=Education, 28=Science & Technology")
    parser.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    parser.add_argument("--client-secret", default=str(DEFAULT_CLIENT_SECRET))
    parser.add_argument("--token", default=str(DEFAULT_TOKEN_FILE))

    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    client_secret_path = Path(args.client_secret)
    if not client_secret_path.exists():
        raise FileNotFoundError(
            f"Missing OAuth client secret JSON at {client_secret_path}. "
            f"Download from Google Cloud Console and place it there."
        )

    token_path = Path(args.token)
    token_path.parent.mkdir(parents=True, exist_ok=True)

    service = get_youtube_service(client_secret_path, token_path)
    video_id = upload_video(
        service=service,
        video_path=video_path,
        title=args.title,
        description=args.description,
        tags=[t.strip() for t in args.tags.split(",") if t.strip()],
        category_id=args.category_id,
        privacy_status=args.privacy,
    )

    result = {
        "video_id": video_id,
        "watch_url": f"https://www.youtube.com/watch?v={video_id}",
        "privacy": args.privacy,
        "video": str(video_path),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
