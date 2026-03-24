"""
Google Calendar API wrapper。
Service Account 認証で当日の予定を取得する。
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone

from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def _load_credentials() -> service_account.Credentials:
    """
    環境変数 GOOGLE_SERVICE_ACCOUNT_JSON から Service Account 認証情報を読み込む。
    ファイルパスではなく JSON 文字列をそのまま環境変数に設定する。
    """
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not raw:
        raise EnvironmentError(
            "GOOGLE_SERVICE_ACCOUNT_JSON 環境変数が設定されていません"
        )
    try:
        info = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "GOOGLE_SERVICE_ACCOUNT_JSON が正しい JSON ではありません"
        ) from exc

    return service_account.Credentials.from_service_account_info(
        info, scopes=SCOPES
    )


def get_all_events_today(calendar_id: str | None = None) -> list[dict]:
    """
    当日（JST）の全予定を時刻順で返す。
    全日予定（start.dateTime がないもの）はスキップする。

    戻り値:
        [
            {
                "summary":  イベントタイトル（str）,
                "start_dt": 開始時刻（timezone-aware datetime）,
                "end_dt":   終了時刻（timezone-aware datetime | None）,
                "location": 場所（str | None）,
            },
            ...
        ]
    """
    if calendar_id is None:
        calendar_id = os.environ.get("CALENDAR_ID", "primary")

    creds = _load_credentials()
    service = build("calendar", "v3", credentials=creds)

    # 当日の JST 0:00 〜 23:59:59 を UTC に変換
    now_jst = datetime.now(JST)
    day_start = now_jst.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = now_jst.replace(hour=23, minute=59, second=59, microsecond=0)

    time_min = day_start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    time_max = day_end.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,   # 繰り返し予定を個別に展開
            orderBy="startTime",
        )
        .execute()
    )

    events = []
    for item in result.get("items", []):
        start = item.get("start", {})
        end = item.get("end", {})

        # 全日予定（dateTime がない）はスキップ
        if "dateTime" not in start:
            logger.info("全日予定をスキップ: %s", item.get("summary", "(タイトルなし)"))
            continue

        start_dt = datetime.fromisoformat(start["dateTime"])
        end_dt_raw = end.get("dateTime")
        end_dt = datetime.fromisoformat(end_dt_raw) if end_dt_raw else None

        events.append(
            {
                "summary": item.get("summary") or "(タイトルなし)",
                "start_dt": start_dt,
                "end_dt": end_dt,
                "location": item.get("location"),
            }
        )

    logger.info("当日の予定: %d 件", len(events))
    return events
