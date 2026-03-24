"""
LINE Messaging API で通知を送るモジュール。
- デフォルトは Broadcast（友達全員に一斉送信）
- 特定ユーザーへの送信は send_to_user() を使用
"""

import json
import logging
import os
import time
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

BROADCAST_URL = "https://api.line.me/v2/bot/message/broadcast"
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
        # LINE_USER_ID は send_to_user() 使用時のみ必要（Broadcast では不要）
        self.user_id = os.environ.get("LINE_USER_ID")

    def _send_with_retry(self, url: str, payload: dict) -> None:
        """指数バックオフ付きリトライで LINE API にリクエストを送る"""
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }

        for attempt in range(MAX_RETRIES + 1):
            try:
                req = urllib.request.Request(
                    url, data=data, headers=headers, method="POST"
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

    def _broadcast_messages(self, messages: list[dict]) -> None:
        """友達全員に Broadcast 送信する（"to" フィールド不要）"""
        payload = {"messages": messages}
        self._send_with_retry(BROADCAST_URL, payload)

    def _push_messages(self, user_id: str, messages: list[dict]) -> None:
        """特定ユーザーに Push 送信する"""
        payload = {"to": user_id, "messages": messages}
        self._send_with_retry(PUSH_URL, payload)

    def send_text(self, text: str) -> None:
        """テキストメッセージを友達全員に Broadcast 送信する"""
        self._broadcast_messages([{"type": "text", "text": text}])

    def send_to_user(self, text: str, user_id: str | None = None) -> None:
        """テキストメッセージを特定ユーザーに Push 送信する"""
        target = user_id or self.user_id
        if not target:
            raise EnvironmentError(
                "LINE_USER_ID 環境変数が設定されていません"
            )
        self._push_messages(target, [{"type": "text", "text": text}])
