"""
LINE Messaging API でプッシュ通知を送るモジュール。
menu-bot の notify/line.py を参考に、push 専用でシンプル化。
"""

import json
import logging
import os
import time
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

PUSH_URL = "https://api.line.me/v2/bot/message/push"
MAX_RETRIES = 3
BACKOFF_BASE = 2  # 指数バックオフ: 2s, 4s, 8s


class LineNotifier:
    def __init__(self):
        self.token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
        if not self.token:
            raise EnvironmentError(
                "LINE_CHANNEL_ACCESS_TOKEN 環境変数が設定されていません"
            )
        self.user_id = os.environ.get("LINE_USER_ID")
        if not self.user_id:
            raise EnvironmentError(
                "LINE_USER_ID 環境変数が設定されていません"
            )

    def _send_with_retry(self, payload: dict) -> None:
        """指数バックオフ付きリトライで LINE Push API にリクエストを送る"""
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }

        for attempt in range(MAX_RETRIES + 1):
            try:
                req = urllib.request.Request(
                    PUSH_URL, data=data, headers=headers, method="POST"
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    request_id = resp.headers.get("x-line-request-id", "N/A")
                    logger.info(
                        "LINE 送信成功 (HTTP %s, request-id: %s)",
                        resp.status, request_id,
                    )
                    return
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8")
                request_id = e.headers.get("x-line-request-id", "N/A")
                logger.warning(
                    "LINE 送信失敗 (attempt %d/%d): HTTP %d (request-id: %s) - %s",
                    attempt + 1, MAX_RETRIES + 1, e.code, request_id, body,
                )
                # 400, 401 等はリトライしない
                if e.code not in (429, 500, 502, 503):
                    raise RuntimeError(
                        f"LINE API エラー: HTTP {e.code} - {body}"
                    )
                if attempt < MAX_RETRIES:
                    time.sleep(BACKOFF_BASE ** (attempt + 1))
            except Exception as exc:
                logger.warning(
                    "LINE 送信エラー (attempt %d/%d): %s",
                    attempt + 1, MAX_RETRIES + 1, exc,
                )
                if attempt < MAX_RETRIES:
                    time.sleep(BACKOFF_BASE ** (attempt + 1))

        raise RuntimeError("LINE 通知に失敗しました（最大リトライ回数超過）")

    def send_text(self, text: str) -> None:
        """テキストメッセージを LINE_USER_ID に Push 送信する"""
        payload = {
            "to": self.user_id,
            "messages": [{"type": "text", "text": text}],
        }
        self._send_with_retry(payload)
