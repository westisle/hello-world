# プロジェクト概要

Yahoo!ニュース の JNN チャンネルページから記事タイトルと関連記事を収集し、CSV に保存するスクレイパー。

## 目標

- `scraper.py` を実行すると `output.csv` が生成される
- CSV には「記事URL・タイトル・関連記事5件（タイトル＋URL）」が入る
- 将来的にはメディアを JNN 以外にも拡張したい（`MEDIA_URL` を差し替えるだけで動く設計が望ましい）

## 技術スタック

- Python 3.11
- Playwright（ブラウザ自動操作）
- BeautifulSoup4（HTML パース）
- 非同期処理（asyncio）

## 実行方法

```bash
pip install -r requirements.txt
playwright install chromium
python scraper.py
```

## 既知の注意点

- Yahoo!ニュースは読み込み後もネットワーク通信が続くため `wait_until="networkidle"` はタイムアウトする。`domcontentloaded` または `load` を使うこと。
- リクエスト間に `asyncio.sleep()` を入れてサーバー負荷を抑えること（現在 `REQUEST_DELAY = 1.5` 秒）。
- `output.csv` は UTF-8 BOM 付きで保存（Excel で文字化けしないよう `utf-8-sig`）。

## ファイル構成

```
scraper.py        # メインスクリプト
requirements.txt  # 依存パッケージ
output.csv        # 実行結果（git 管理外）
```

## 開発ルール

- `output.csv` は `.gitignore` に追加して commit しない。
- 動作確認は `python scraper.py` を直接実行して行う。
- ブランチは `claude/` プレフィックスで作成し、作業後は push する。
