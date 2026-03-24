"""
LINE Webhook サーバー（グループID取得用）
- join イベント: グループに招待されたとき、グループIDを返信
- message イベント: 「ID教えて」と送ったとき、グループIDを返信

グループIDが取得できたら Render からデプロイを停止して構いません。
"""

import hashlib
import hmac
import json
import logging
import os
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")
REPLY_URL = "https://api.line.me/v2/bot/message/reply"


def verify_signature(body: bytes, signature: str) -> bool:
    """LINE からのリクエストを署名で検証する"""
    if not CHANNEL_SECRET:
        logger.warning("LINE_CHANNEL_SECRET が未設定のため署名検証をスキップします")
        return True
    digest = hmac.new(
        CHANNEL_SECRET.encode("utf-8"), body, hashlib.sha256
    ).digest()
    import base64
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def reply(reply_token: str, text: str) -> None:
    """LINE Reply API でメッセージを返信する"""
    payload = json.dumps({
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}],
    }).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}",
    }
    req = urllib.request.Request(REPLY_URL, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info("返信成功: HTTP %s", resp.status)
    except urllib.error.HTTPError as e:
        logger.error("返信失敗: HTTP %d - %s", e.code, e.read().decode())


def handle_events(events: list) -> None:
    """LINE イベントを処理する"""
    for event in events:
        event_type = event.get("type")
        reply_token = event.get("replyToken")
        source = event.get("source", {})
        group_id = source.get("groupId") or source.get("roomId")

        # ── グループに招待されたとき ──
        if event_type == "join":
            logger.info("join イベント: group_id=%s", group_id)
            if group_id and reply_token:
                reply(
                    reply_token,
                    f"招待ありがとうございます！\n"
                    f"このグループのIDは:\n{group_id}\n\n"
                    f"この値を GitHub Secrets の LINE_GROUP_ID に設定してください。",
                )

        # ── テキストメッセージ「ID教えて」に反応 ──
        elif event_type == "message" and event.get("message", {}).get("type") == "text":
            text = event["message"].get("text", "").strip()
            if text == "ID教えて":
                target_id = group_id or source.get("userId", "不明")
                logger.info("ID教えてリクエスト: id=%s", target_id)
                if reply_token:
                    reply(
                        reply_token,
                        f"現在のIDは:\n{target_id}\n\n"
                        f"GitHub Secrets の LINE_GROUP_ID に設定してください。",
                    )


class WebhookHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        """Render のヘルスチェック用"""
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"LINE Webhook server is running.")

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        signature = self.headers.get("X-Line-Signature", "")

        if not verify_signature(body, signature):
            logger.warning("署名検証失敗")
            self.send_response(400)
            self.end_headers()
            return

        try:
            data = json.loads(body.decode("utf-8"))
            handle_events(data.get("events", []))
        except Exception as exc:
            logger.error("イベント処理エラー: %s", exc)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):  # noqa: A002
        logger.info("%s - %s", self.address_string(), format % args)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), WebhookHandler)
    logger.info("Webhook サーバー起動: port=%d", port)
    server.serve_forever()
