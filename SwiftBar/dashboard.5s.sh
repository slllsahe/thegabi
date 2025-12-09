#!/bin/zsh
# SwiftBar: 한 줄 요약 회전 (Temp/TSLA/FX)

export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

# 맨 위쪽 변수들
PY="$HOME/Sung/thegabi/venv/bin/python3"
WD="$HOME/Sung/thegabi"
LOG="$HOME/Library/Logs/SwiftBar-dashboard.log"

cd "$WD" 2>/dev/null || { echo "경로 오류"; exit 0; }
[[ -x "$PY" ]] || { echo "가상환경 점검 필요"; exit 0; }

# 데이터 수집: 1) 로컬 API 우선, 2) 실패 시 개별 호출
API_JSON=$(curl -s --max-time 2 http://127.0.0.1:8000/api/data)
if [[ -n "$API_JSON" ]]; then
  read -r w_val t_val x_val <<EOF
$(printf '%s' "$API_JSON" | "$PY" - <<'PY'
import sys,json,re
js=sys.stdin.read()
try:
    d=json.loads(js)
except Exception:
    d={}
def out(v):
    s='' if v is None else str(v)
    print(re.sub(r'[ ,]','',s))
out(d.get('temperature_c'))
out(d.get('tesla_usd'))
out(d.get('gbp_eur'))
PY
)
EOF
else
  # API가 없으면 빠른 날씨만 조회하고, TSLA/FX는 네트워크로 직접 조회 시도
  w_val=$("$PY" webproject.py --mode openmeteo 2>>"$LOG" | awk -F': ' '{print $2}')
  t_val=""
  x_val=""
fi

# 초기화 (BTC 값)
b_val=""

# TSLA/GBP→EUR 보조 소스: stooq.com / frankfurter.app
fetch_tsla() {
  curl -s --connect-timeout 1 --max-time 2 'https://stooq.com/q/l/?s=tsla.us&f=sd2t2ohlcv&h&e=csv' | "$PY" -c 'import sys,csv; r=list(csv.DictReader(sys.stdin)); print(r[0].get("Close","") if r else "")'
}

fetch_gbp_eur() {
  curl -s --connect-timeout 1 --max-time 2 'https://api.frankfurter.app/latest?from=GBP&to=EUR' | "$PY" -c 'import sys,json; d=json.load(sys.stdin); print(d.get("rates",{}).get("EUR",""))'
}

# BTC USD 보조 소스: CoinGecko (가볍고 빠름)
fetch_btc() {
  curl -s --connect-timeout 1 --max-time 2 'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd' | "$PY" -c 'import sys,json; d=json.load(sys.stdin); print(d.get("bitcoin",{}).get("usd",""))'
}

# 값 보강: 비어있으면 보조 소스로 채움
[[ -z "$t_val" ]] && t_val=$(fetch_tsla)
[[ -z "$x_val" ]] && x_val=$(fetch_gbp_eur)
[[ -z "$b_val" ]] && b_val=$(fetch_btc)

# 빈 값 대체
[[ -z "$w_val"       ]] && w_val="…"
[[ -z "$t_val"       ]] && t_val="…"
[[ -z "$x_val"       ]] && x_val="…"
[[ -z "$b_val"       ]] && b_val="…"

# 숫자 포맷 간소화 (정수/2소수)
read -r w_fmt t_fmt x_fmt b_fmt <<EOF
$("$PY" - "$w_val" "$t_val" "$x_val" "$b_val" <<'PY'
import sys,re
w,t,x,b=sys.argv[1:5]
def fmt(s,dec):
    s=re.sub(r'[ ,]','',s)
    try:
        f=float(s)
        if dec==0:
            return str(int(round(f)))
        return (f"{f:.{dec}f}").rstrip('0').rstrip('.')
    except:
        return s
print(fmt(w,0), fmt(t,0), fmt(x,2), fmt(b,0))
PY
)
EOF

# 회전 표시 (5초 간격)
interval=5
slot=$(( ( $(date +%s) / interval ) % 4 ))

case $slot in
  0)
    echo "${w_fmt}°"
    ;;
  1)
    echo "T${t_fmt}"
    ;;
  2)
    echo "£€${x_fmt}"
    ;;
  3)
    echo "${b_fmt}"
    ;;
esac


