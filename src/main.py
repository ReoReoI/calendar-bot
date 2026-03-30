"""
Calendar Bot - メインエントリーポイント。
GitHub Actions から毎朝 8:00 JST に実行される。
当日の Google Calendar 予定を取得し、LINE に通知する。
"""

import logging
import os
import sys
from datetime import datetime, timedelta, timezone

from src.calendar_client import get_all_events_today
from src.line_notifier import LineNotifier

JST = timezone(timedelta(hours=9))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# 丸数字（最大10件。それ以上は数字 + ドット）
CIRCLE_NUMBERS = "①②③④⑤⑥⑦⑧⑨⑩"


def format_schedule_message(events: list[dict]) -> str:
    """
    当日の全予定を1通のテキストメッセージに整形する。

    例:
        📅 本日のスケジュール（3月24日）

        ① 10:00 〜 11:00　チームミーティング（会議室A）
        ② 14:00 〜 15:30　クライアント打ち合わせ
        ③ 17:00 〜 17:30　1on1
    """
    today = datetime.now(JST)
    # Windows では %-m が使えないため %m と lstrip("0") で対応
    month = str(today.month)
    day = str(today.day)
    today_str = f"{month}月{day}日"

    header = f"📅 本日のスケジュール（{today_str}）"

    if not events:
        return f"{header}\n\n今日は予定がありません"

    lines = [header, ""]
    for i, event in enumerate(events):
        start_jst = event["start_dt"].astimezone(JST)
        start_str = start_jst.strftime("%H:%M")

        end_dt = event.get("end_dt")
        if end_dt:
            end_jst = end_dt.astimezone(JST)
            time_str = f"{start_str} 〜 {end_jst.strftime('%H:%M')}"
        else:
            time_str = start_str

        location = event.get("location")
        loc_str = f"（{location}）" if location else ""

        num = CIRCLE_NUMBERS[i] if i < len(CIRCLE_NUMBERS) else f"{i + 1}."
        lines.append(f"{num} {time_str}　{event['summary']}{loc_str}")

    return "\n".join(lines)


def main() -> None:
    calendar_id = os.environ.get("CALENDAR_ID", "primary")
    logger.info("カレンダーID: %s", calendar_id)

    events = get_all_events_today(calendar_id)
    logger.info("取得した予定数: %d", len(events))

    message = format_schedule_message(events)
    logger.info("送信メッセージ:\n%s", message)

    notifier = LineNotifier()
    group_id = os.environ.get("LINE_GROUP_ID")
    if group_id:
        notifier.send_to_group(message, group_id)
        logger.info("LINE グループに通知を送信しました（1通消費）")
    else:
        notifier.send_text(message)
        logger.info("LINE Broadcast で通知を送信しました")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logger.exception("致命的エラー: %s", exc)
        sys.exit(1)
