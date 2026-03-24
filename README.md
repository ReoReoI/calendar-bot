# Calendar Bot

Google カレンダーの予定を毎朝 8:00 JST に LINE へ通知する Bot。
GitHub Actions で自動実行。**ランニングコスト 0 円**。

## 通知イメージ

```
📅 本日のスケジュール（3月24日）

① 10:00 〜 11:00　チームミーティング（会議室A）
② 14:00 〜 15:30　クライアント打ち合わせ
③ 17:00 〜 17:30　1on1
```

予定がない日は「今日は予定がありません」と送信されます。

---

## セットアップ手順

### 1. Google Cloud - サービスアカウント作成

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成（または既存を選択）
2. **APIs & Services > Enable APIs & Services** で **Google Calendar API** を有効化
3. **IAM & Admin > Service Accounts** でサービスアカウントを作成
   - 名前: `calendar-bot`（任意）
   - ロール: なし（カレンダーの共有設定で制御するため不要）
4. 作成したサービスアカウントを選択 → **Keys タブ > Add Key > Create new key > JSON**
5. ダウンロードした JSON ファイルを保管（後で GitHub Secrets に貼り付けます）

### 2. Google カレンダーをサービスアカウントと共有

1. [Google カレンダー](https://calendar.google.com/) を開く
2. 通知したいカレンダーの **「⋮」> 設定と共有** を開く
3. **「特定のユーザーまたはグループと共有する」** にサービスアカウントのメールを追加
   - メールアドレス: `calendar-bot@YOUR_PROJECT.iam.gserviceaccount.com`
   - 権限: **閲覧のみ（詳細を表示）**
4. 同じ設定ページの **「カレンダーの統合」** セクションからカレンダー ID をコピー
   - 例: `yourname@gmail.com` または `xxxxxxxx@group.calendar.google.com`

### 3. GitHub リポジトリを作成して Secrets を設定

1. このリポジトリを GitHub に push（または fork）
2. **Settings > Secrets and variables > Actions > New repository secret** で以下を追加:

| Secret 名 | 値 |
|-----------|-----|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | ダウンロードした JSON ファイルの内容をそのまま貼り付け |
| `CALENDAR_ID` | 手順 2 でコピーしたカレンダー ID |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Developers のチャンネルアクセストークン（長期） |
| `LINE_USER_ID` | 通知先の LINE ユーザー ID |

#### LINE の設定方法

1. [LINE Developers Console](https://developers.line.biz/) でプロバイダーとチャンネル（Messaging API）を作成
2. **Messaging API 設定 > チャンネルアクセストークン（長期）** を発行 → `LINE_CHANNEL_ACCESS_TOKEN`
3. **LINE_USER_ID** の確認方法:
   - 作成したボットを LINE で友達追加
   - Webhook を受信できるサーバーを一時的に用意するか、[LINE API のユーザー ID 確認ツール](https://developers.line.biz/ja/docs/messaging-api/getting-user-ids/) を使用

### 4. 動作確認

- GitHub の **Actions タブ > 朝のLINE通知（8:00 JST） > Run workflow** で手動実行
- LINE に通知が届けば設定完了！

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

## 友人環境への移行（Migration）

コードの変更は**一切不要**です。以下の手順だけで別の人の環境にも使えます。

### 移行コスト: 約 15 分

| 変更が必要なもの | 説明 |
|----------------|------|
| `CALENDAR_ID` | 移行先のカレンダー ID |
| `LINE_CHANNEL_ACCESS_TOKEN` | 移行先の LINE チャンネルアクセストークン |
| `LINE_USER_ID` | 移行先の LINE ユーザー ID |
| カレンダーの共有設定 | 移行先の Google カレンダーをサービスアカウントと共有 |

> **`GOOGLE_SERVICE_ACCOUNT_JSON` は変更不要です。**
> 同じサービスアカウントを複数人で共有できます。

### 移行手順

1. このリポジトリを**Fork**（または **Use this template**）して新しいリポジトリを作成
2. 移行先の Google カレンダーをサービスアカウントのメールと「閲覧のみ」で共有
3. Fork したリポジトリの Secrets に移行先の値を設定（上記の表を参照）
4. **Actions タブ > Run workflow** で動作確認

---

## ファイル構成

```
calendar-bot/
├── .github/workflows/
│   └── morning_notify.yml  # 毎朝 8:00 JST（UTC 23:00）に実行
├── src/
│   ├── main.py             # エントリーポイント・メッセージ整形
│   ├── calendar_client.py  # Google Calendar API (Service Account 認証)
│   └── line_notifier.py    # LINE Messaging API push 送信
├── .env.example            # 環境変数テンプレート
├── requirements.txt        # 依存パッケージ
└── README.md               # このファイル
```

## 注意事項

- 全日予定（「誕生日」「祝日」など）は通知に含まれません（開始時刻がないためスキップ）
- GitHub Actions の cron は最大 15 分程度遅延する場合があります
- `CALENDAR_ID` に `primary` は使用しないでください（サービスアカウント自身の空のカレンダーを参照してしまいます）
