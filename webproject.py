import re
import argparse
import requests
from typing import Optional

# ===============================
# 출력 유틸
# ===============================
def show_line(title: str, value: Optional[str]):
    print(f"{title}: {value if value is not None else '데이터 없음'}")

# ===============================
# 날씨 (Open-Meteo 현재만)
# ===============================
def current_temp_openmeteo(lat=50.1109, lon=8.6821, tz="Europe/Berlin") -> Optional[float]:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m"
        f"&timezone={tz}"
    )
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    js = r.json()
    return js.get("current", {}).get("temperature_2m")

# ===============================
# BBC 날씨 (현재만, Selenium)
# ===============================
def _extract_celsius_number(text: str) -> Optional[int]:
    if not text:
        return None
    m = re.search(r"(-?\d+)\s*°?\s*C", text, flags=re.IGNORECASE)
    return int(m.group(1)) if m else None

def current_temp_bbc(url="https://www.bbc.com/weather/2925533", lang="en-GB") -> Optional[int]:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import NoSuchElementException, TimeoutException

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,2000")
    opts.add_argument(f"--accept-lang={lang},en;q=0.9")
    opts.add_argument("--user-agent=Mozilla/5.0")

    with webdriver.Chrome(options=opts) as driver:
        driver.get(url)
        try:
            WebDriverWait(driver, 12).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='summary-temperature']")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".wr-c-observations__temperature")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".wr-value--temperature--c"))
                )
            )
        except TimeoutException:
            return None

        selectors = [
            "[data-testid='summary-temperature'] .wr-value--temperature--c",
            "[data-testid='summary-temperature']",
            ".wr-c-observations__temperature .wr-value--temperature--c",
            ".wr-value--temperature--c",
        ]
        for sel in selectors:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                txt = el.text.strip()
                if txt:
                    return _extract_celsius_number(txt)
            except NoSuchElementException:
                continue
    return None

# ===============================
# Investing.com 가격 (Selenium)
# ===============================
def investing_price(url: str) -> Optional[str]:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,1600")
    opts.add_argument("--user-agent=Mozilla/5.0")

    with webdriver.Chrome(options=opts) as driver:
        driver.get(url)

        # 1) 쿠키 배너 자동 수락 시도
        try:
            WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            ).click()
        except TimeoutException:
            pass  # 쿠키 배너 없으면 넘어감

        # 2) 가격 요소 셀렉터 후보
        selectors = [
            "div[data-test='instrument-price-last']",  # 기본
            ".text-2xl",                               # 일부 페이지 fallback
            ".instrument-price_instrument-price__3uw25 .text-2xl"  # 새로운 레이아웃 fallback
        ]

        for sel in selectors:
            try:
                elem = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                )
                txt = elem.text.strip()
                if txt:
                    return txt
            except (TimeoutException, NoSuchElementException):
                continue

    return None

# ===============================
# 모든 데이터 한 줄로 출력
# ===============================
def line_all_compact(lat=50.1109, lon=8.6821, tz="Europe/Berlin") -> str:
    try:
        url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
               f"&current=temperature_2m&timezone={tz}")
        js = requests.get(url, timeout=10).json()
        w_val = js.get("current", {}).get("temperature_2m")
    except Exception:
        w_val = None

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ModuleNotFoundError:
        return f"🌤 {w_val or '…'}°C | TSLA … | £/€ …"

    def grab(url: str) -> str | None:
        opts = Options()
        opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1280,1600")
        opts.add_argument("--user-agent=Mozilla/5.0")
        with webdriver.Chrome(options=opts) as d:
            d.get(url)
            try:
                el = WebDriverWait(d, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-test='instrument-price-last']"))
                )
                return el.text.strip()
            except Exception:
                return None

    t_val = grab("https://uk.investing.com/equities/tesla-motors") or "…"
    x_val = grab("https://uk.investing.com/currencies/gbp-eur") or "…"

    return f"🌤 {w_val or '…'}°C | TSLA {t_val} | £/€ {x_val}"

# ===============================
# CLI
# ===============================
def main():
    parser = argparse.ArgumentParser(description="현재 날씨/가격 조회 통합")
    parser.add_argument("--mode", choices=["openmeteo", "bbc", "tesla", "gbpeur", "all", "all-compact"],
                        default="all", help="데이터 선택")
    parser.add_argument("--lat", type=float, default=50.1109)
    parser.add_argument("--lon", type=float, default=8.6821)
    parser.add_argument("--tz", type=str, default="Europe/Berlin")
    args = parser.parse_args()

    if args.mode == "openmeteo":
        temp = current_temp_openmeteo(lat=args.lat, lon=args.lon, tz=args.tz)
        show_line("현재 기온(°C, Open-Meteo)", temp)
    elif args.mode == "bbc":
        temp = current_temp_bbc()
        show_line("현재 기온(°C, BBC)", temp)
    
    elif args.mode == "tesla":
        price = investing_price("https://uk.investing.com/equities/tesla-motors")
        show_line("테슬라 주가 (USD)", price)
    elif args.mode == "gbpeur":
        price = investing_price("https://uk.investing.com/currencies/gbp-eur")
        show_line("GBP/EUR 환율", price)
    elif args.mode == "all":
        temp = current_temp_openmeteo(lat=args.lat, lon=args.lon, tz=args.tz)
        show_line("현재 기온(°C)", temp)
        price_tsla = investing_price("https://uk.investing.com/equities/tesla-motors")
        show_line("테슬라 주가 (USD)", price_tsla)
        price_gbp = investing_price("https://uk.investing.com/currencies/gbp-eur")
        show_line("GBP/EUR 환율", price_gbp)
    elif args.mode == "all-compact":
        print(line_all_compact(lat=args.lat, lon=args.lon, tz=args.tz))

if __name__ == "__main__":
    main()