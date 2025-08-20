from playwright.sync_api import sync_playwright
import json

URL = "https://www.rewe.de/angebote/nationale-angebote/"

def scrape_rewe_playwright():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # 실제 브라우저 창을 안 띄움
        page = browser.new_page()
        page.goto(URL)
        page.wait_for_selector("h3[data-testid='product-card-title']", timeout=60000)  # 상품 카드 로딩 대기

        products = []
        cards = page.query_selector_all("div[data-testid='product-card']")
        for card in cards:
            name_el = card.query_selector("h3[data-testid='product-card-title']")
            price_el = card.query_selector("div[data-testid='product-card-price']")
            img_el = card.query_selector("img")

            name = name_el.inner_text().strip() if name_el else ""
            price = price_el.inner_text().strip() if price_el else ""
            image = img_el.get_attribute("src") if img_el else ""

            products.append({
                "name": name,
                "price": price,
                "image": image
            })

        browser.close()
        return products

if __name__ == "__main__":
    data = scrape_rewe_playwright()
    print(json.dumps(data, indent=2, ensure_ascii=False))