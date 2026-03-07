"""
Yahoo!ニュース JNN 記事スクレイパー

取得内容:
  - 記事タイトル
  - 関連記事（最大5本）のタイトルと URL

保存形式: CSV (output.csv)

使い方:
  pip install playwright beautifulsoup4
  playwright install chromium
  python scraper.py
"""

import asyncio
import csv
import time
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

MEDIA_URL = "https://news.yahoo.co.jp/media/jnn"
OUTPUT_FILE = "output.csv"
REQUEST_DELAY = 1.5  # リクエスト間隔（秒）


async def get_article_links(page) -> list[str]:
    """JNN 一覧ページから記事URLを全件取得する（ページネーション対応）"""
    links = []

    while True:
        await page.wait_for_selector("a[href*='/articles/']", timeout=10000)
        await asyncio.sleep(1)

        hrefs = await page.eval_on_selector_all(
            "a[href*='/articles/']",
            "els => [...new Set(els.map(el => el.href))]"
        )
        new_links = [h for h in hrefs if h not in links]
        links.extend(new_links)
        print(f"  記事リンク取得数: {len(links)}")

        # 「次へ」ボタンがあればクリック、なければ終了
        next_btn = await page.query_selector("a[href*='page=']:last-of-type, a:has-text('次へ')")
        if not next_btn:
            break
        await next_btn.click()
        await page.wait_for_load_state("networkidle")

    return links


async def scrape_article(page, url: str) -> dict | None:
    """記事ページからタイトルと関連記事を取得する"""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(REQUEST_DELAY)

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        # --- 記事タイトル ---
        title_tag = (
            soup.find("h1")
            or soup.find("meta", property="og:title")
        )
        if title_tag:
            title = (
                title_tag.get("content", "")
                if title_tag.name == "meta"
                else title_tag.get_text(strip=True)
            )
        else:
            title = ""

        # --- 関連記事（最大5件）---
        related = []

        # 「関連記事」セクションを探す（複数のセレクタ候補）
        related_section = (
            soup.find("section", {"data-ual-widget-type": "related"})
            or soup.find("ul", class_=lambda c: c and "relatedArticle" in c)
            or soup.find("div", class_=lambda c: c and "related" in (c or "").lower())
        )

        if related_section:
            for a in related_section.find_all("a", href=True)[:5]:
                text = a.get_text(strip=True)
                href = a["href"]
                if text:
                    related.append({"title": text, "url": href})
        else:
            # フォールバック: ページ下部の記事リンクを取得
            all_links = soup.find_all("a", href=lambda h: h and "/articles/" in h)
            seen = set()
            for a in all_links:
                href = a["href"]
                text = a.get_text(strip=True)
                if text and href not in seen and href != url:
                    related.append({"title": text, "url": href})
                    seen.add(href)
                if len(related) >= 5:
                    break

        return {"url": url, "title": title, "related": related}

    except Exception as e:
        print(f"  [ERROR] {url}: {e}")
        return None


def save_to_csv(records: list[dict], filepath: str):
    """結果をCSVファイルに保存する"""
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "記事URL", "記事タイトル",
            "関連1タイトル", "関連1URL",
            "関連2タイトル", "関連2URL",
            "関連3タイトル", "関連3URL",
            "関連4タイトル", "関連4URL",
            "関連5タイトル", "関連5URL",
        ])
        for rec in records:
            row = [rec["url"], rec["title"]]
            for i in range(5):
                if i < len(rec["related"]):
                    row += [rec["related"][i]["title"], rec["related"][i]["url"]]
                else:
                    row += ["", ""]
            writer.writerow(row)


async def main():
    print("=== Yahoo!ニュース JNN スクレイパー 開始 ===")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
            locale="ja-JP",
        )
        page = await context.new_page()

        # 1. 一覧ページから記事リンク収集
        print(f"\n[1/2] 一覧ページを取得中: {MEDIA_URL}")
        await page.goto(MEDIA_URL, wait_until="networkidle", timeout=30000)
        article_links = await get_article_links(page)
        print(f"  合計 {len(article_links)} 件の記事を検出\n")

        # 2. 各記事をスクレイピング
        print(f"[2/2] 各記事を取得中...")
        records = []
        for i, url in enumerate(article_links, 1):
            print(f"  ({i}/{len(article_links)}) {url}")
            result = await scrape_article(page, url)
            if result:
                records.append(result)

        await browser.close()

    # 3. CSV保存
    save_to_csv(records, OUTPUT_FILE)
    print(f"\n完了: {len(records)} 件を '{OUTPUT_FILE}' に保存しました")


if __name__ == "__main__":
    asyncio.run(main())
