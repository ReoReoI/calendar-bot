# Calendar Bot

Google カレンダーの予定を毎朝 8:00 JST に LINE グループへ通知する Bot。
GitHub Actions で自動実行。**ランニングコスト 0 円**。

> 📖 **初めてセットアップする方へ**
> プログラミング経験がない方でも手順通りに進められる詳細ガイドを用意しています。
> 👉 **[SETUP_GUIDE.md](./SETUP_GUIDE.md) を参照してください。**

## 通知イメージ

```
📅 本日のスケジュール（3月24日）

① 10:00 〜 11:00　チームミーティング（会議室A）
② 14:00 〜 15:30　クライアント打ち合わせ
③ 17:00 〜 17:30　1on1
```

予定がない日は「今日は予定がありません」と送信されます。

---

## アーキテクチャ

```
GitHub Actions (毎朝 8:00 JST)
    ↓
Google Calendar API（サービスアカウント認証）
    ↓
LINE Messaging API Push（グループ宛・1通消費）
    ↓
LINE グループ（メンバー全員が受信）
```

### 送信方式と月間消費数

| 方式 | 消費数（10人・毎日） | 採用 |
|------|-------------------|------|
| Broadcast（全員送信） | 10人 × 30日 = **300通** | — |
| グループ Push | 1グループ × 30日 = **30通** | ✅ |

`LINE_GROUP_ID` が設定されている場合はグループ Push、未設定の場合は Broadcast にフォールバックします。

---

## セットアップ手順

### 1. Google Cloud — サービスアカウント作成

1. [Google Cloud Console](https://console.cloud.google.com/) で新しいプロジェクト（例：`calendar-bot`）を作成
2. **「APIとサービス」>「APIの有効化」** で **Google Calendar API** を有効化
3. **「IAM と管理」>「サービスアカウント」** でサービスアカウントを作成
   - 名前: `calendar-bot`（任意）
   - ロール: なし（カレンダーの共有設定で制御するため不要）
4. 作成したサービスアカウントを選択 → **「キー」タブ > 「鍵を追加」> 「新しい鍵を作成」> JSON**
5. ダウンロードした JSON ファイルを保管（後で GitHub Secrets に貼り付けます）

### 2. Google カレンダー — サービスアカウントと共有

1. [Google カレンダー](https://calendar.google.com/) を開く
2. 通知したいカレンダーの **「⋮」>「設定と共有」** を開く
3. **「特定のユーザーまたはグループと共有する」** にサービスアカウントのメールを追加
   - メールアドレス: `calendar-bot@YOUR_PROJECT.iam.gserviceaccount.com`
   - 権限: **「予定の表示（すべての予定の詳細）」**
4. 同じ設定ページの **「カレンダーの統合」** セクションから **カレンダー ID** をコピー
   - 例: `yourname@gmail.com` または `xxxxxxxx@group.calendar.google.com`

### 3. LINE Developers — チャンネル作成とグループ ID 取得

#### チャンネル作成とトークン発行

1. [LINE Developers Console](https://developers.line.biz/) でプロバイダーとチャンネル（Messaging API）を作成
2. **「Messaging API 設定」タブ** の一番下にある **「チャンネルアクセストークン（長期）」** を発行 → コピー

#### グループ ID の取得（webhook.site を使う方法）

グループへのPush送信には `groupId` が必要です。以下の手順で取得します。

1. [webhook.site](https://webhook.site) にアクセスし、発行された一時 URL をコピー
2. [LINE Developers Console](https://developers.line.biz/) の **「Messaging API 設定」** タブで:
   - **Webhook URL** に webhook.site の URL を貼り付けて保存
   - **「Webhookの利用」** をオン
   - **「グループ・複数人トークへの参加を許可する」** をオン
3. ボットを LINE グループに招待（またはグループで `ID教えて` と送信）
4. webhook.site に届いた JSON の中から `groupId` をコピー:
   ```json
   "source": {
       "type": "group",
       "groupId": "Cxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
   }
   ```
5. グループ ID 取得後は Webhook URL を空欄にし **「Webhookの利用」をオフ** にする

#### LINE Official Account Manager の設定

1. [LINE Official Account Manager](https://manager.line.biz/) の **「設定」>「応答設定」** を開く
2. 以下をすべて **オフ** にする:
   - あいさつメッセージ
   - 応答メッセージ

> これをしないと、グループでメッセージを送るたびにボットが自動返信してしまいます。

### 4. GitHub — Secrets の設定

リポジトリの **「Settings」>「Secrets and variables」>「Actions」>「New repository secret」** に以下を登録:

| Secret 名 | 値 |
|-----------|-----|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | ダウンロードした JSON ファイルの内容をそのまま貼り付け |
| `CALENDAR_ID` | 手順 2 でコピーしたカレンダー ID |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE チャンネルアクセストークン（長期） |
| `LINE_GROUP_ID` | 取得した LINE グループ ID（`C` から始まる文字列） |
| `LINE_USER_ID` | （任意）個人通知用。グループ通知のみなら不要 |

### 5. 動作確認

GitHub の **「Actions」タブ > 「朝のLINE通知（8:00 JST）」> 「Run workflow」** で手動実行し、LINE グループに通知が届けば設定完了！

---

## ローカル実行

```bash
cd calendar-bot
pip install -r requirements.txt
cp .env.example .env
# .env を編集して環境変数を設定
python -m src.main
```

---

## ファイル構成

```
calendar-bot/
├── .github/workflows/
│   └── morning_notify.yml  # 毎朝 8:00 JST（UTC 23:00）に実行
├── src/
│   ├── main.py             # エントリーポイント・メッセージ整形
│   ├── calendar_client.py  # Google Calendar API（サービスアカウント認証）
│   └── line_notifier.py    # LINE Messaging API（Push / Broadcast）
├── webhook.py              # グループID取得用の一時 Webhook サーバー
├── Procfile                # Render デプロイ用（webhook.py 起動コマンド）
├── .env.example            # 環境変数テンプレート
├── requirements.txt        # 依存パッケージ
├── SETUP_GUIDE.md          # 初心者向け完全セットアップガイド
└── README.md               # このファイル
```

---

## 注意事項

- 全日予定（「誕生日」「祝日」など）は通知に含まれません（開始時刻がないためスキップ）
- GitHub Actions の cron は最大 15 分程度遅延する場合があります
- `CALENDAR_ID` に `primary` は使用しないでください（サービスアカウント自身の空のカレンダーを参照してしまいます）
- LINE フリープランは月 200 通まで。グループ Push なら 1 日 1 通消費のため 30 通/月で余裕を持って運用できます
- グループメンバーへの通知はボットが参加しているグループに入ることで受け取れます（友達追加だけでは届きません）

---

## 友人環境への移行

コードの変更は**一切不要**です。以下の手順だけで別の人の環境にも使えます。

| 変更が必要なもの | 説明 |
|----------------|------|
| `CALENDAR_ID` | 移行先のカレンダー ID |
| `LINE_CHANNEL_ACCESS_TOKEN` | 移行先の LINE チャンネルアクセストークン |
| `LINE_GROUP_ID` | 移行先のグループ ID |
| カレンダーの共有設定 | 移行先の Google カレンダーをサービスアカウントと共有 |

> **`GOOGLE_SERVICE_ACCOUNT_JSON` は変更不要です。**
> 同じサービスアカウントを複数人で共有できます。
