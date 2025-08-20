# server.py (최적화 버전)
import time
from typing import Any, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from webproject import current_temp_openmeteo, investing_price

app = FastAPI(title="Dashboard API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_CACHE: Dict[str, Any] = {"ts": 0, "data": None}
TTL = 120  # 캐시 유지 시간(초)

def collect_live() -> Dict[str, Any]:
    """한 번에 모든 데이터를 가져오고 compact 문자열도 함께 생성"""
    temp_c = current_temp_openmeteo()
    tsla   = investing_price("https://uk.investing.com/equities/tesla-motors")
    gbpeur = investing_price("https://uk.investing.com/currencies/gbp-eur")

    # compact 문자열 생성 (재호출 없이)
    compact_line = f"🌤 {temp_c or '…'}°C | TSLA {tsla or '…'} | £/€ {gbpeur or '…'}"

    now = int(time.time())
    return {
        "temperature_c": temp_c,
        "tesla_usd": tsla,
        "gbp_eur": gbpeur,
        "compact": compact_line,
        "updated": now,
    }

def get_data() -> Dict[str, Any]:
    """캐시에서 데이터 반환 또는 새로 수집"""
    now = time.time()
    if _CACHE["data"] and now - _CACHE["ts"] < TTL:
        return _CACHE["data"]
    data = collect_live()
    _CACHE.update({"ts": now, "data": data})
    return data

@app.get("/api/data")
def api_data():
    return get_data()

@app.get("/api/compact")
def api_compact():
    return {"line": get_data()["compact"]}

@app.get("/healthz")
def health():
    return {"ok": True, "ts": int(time.time())}