"""
hud_core.py — 단순화 버전.
시나리오 판정, ★ 교차검증 점수, 다중 소스 폴백 같은 해석 레이어는 의도적으로 없음.
미국 지표 3일치 등락 + 미국/한국 뉴스 원문(2~3일 윈도우)을 색깔만 입혀 나열한다.
"오늘 추세인지 노이즈인지"는 본인이 직접 본다 — 이게 설계 의도다.
자동 주문 없음. 매수/매도 문구 없음.
"""
import datetime as dt
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"
KST = dt.timezone(dt.timedelta(hours=9))
UTC = dt.timezone.utc


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 미국 지표 — 최근 N거래일 일별 등락률 (오늘 1일치가 아니라 추세를 보려는 목적)
# ---------------------------------------------------------------------------
def fetch_indicator_trends(cfg):
    import yfinance as yf

    days = cfg.get("trend_days", 3)
    result = {}
    for item in cfg["indicators"]:
        name, ticker, div = item["name"], item["ticker"], item.get("divide_by", 1)
        try:
            hist = yf.Ticker(ticker).history(period=f"{days + 5}d")["Close"].dropna()
            closes = (hist / div).iloc[-(days + 1):]
            if len(closes) < days + 1:
                raise ValueError("거래일 데이터 부족")
            pct_changes = [
                float((closes.iloc[i] - closes.iloc[i - 1]) / closes.iloc[i - 1] * 100)
                for i in range(1, len(closes))
            ]
            result[name] = {"pct_changes": pct_changes, "last_value": float(closes.iloc[-1]), "ok": True}
        except Exception as e:
            result[name] = {"pct_changes": [], "last_value": None, "ok": False, "error": str(e)}
    return result


# ---------------------------------------------------------------------------
# 공통 RSS 유틸 — published_parsed(feedparser가 UTC로 파싱)로 최근 N일만 거름
# ---------------------------------------------------------------------------
def _fetch_rss(url):
    import feedparser
    try:
        feed = feedparser.parse(url)
    except Exception:
        return []
    return feed.entries


def _entry_datetime(e):
    pp = getattr(e, "published_parsed", None) or getattr(e, "updated_parsed", None)
    if not pp:
        return None
    return dt.datetime(*pp[:6], tzinfo=UTC)


def _within_lookback(e, lookback_days):
    when = _entry_datetime(e)
    if when is None:
        return True  # 날짜 파싱이 안 되면 일단 포함 (거르다가 놓치는 것보단 나음)
    cutoff = dt.datetime.now(UTC) - dt.timedelta(days=lookback_days)
    return when >= cutoff


def _fmt_kst(e):
    when = _entry_datetime(e)
    return when.astimezone(KST).strftime("%m/%d %H:%M") if when else ""


# ---------------------------------------------------------------------------
# 한국 카탈리스트 — 한국경제 RSS, watchlist 종목명 + 화이트/블랙리스트로 필터
# ---------------------------------------------------------------------------
def fetch_kr_catalysts(cfg, max_items=8):
    lookback = cfg.get("news_lookback_days", 3)
    whitelist, blacklist, wl = cfg["catalyst_whitelist"], cfg["catalyst_blacklist"], cfg["watchlist"]

    seen, out = set(), []
    for url in cfg["kr_rss_feeds"]:
        for e in _fetch_rss(url):
            title = getattr(e, "title", "")
            if not title or title in seen:
                continue
            if not _within_lookback(e, lookback):
                continue
            if any(b in title for b in blacklist):
                continue
            if not any(w in title for w in whitelist):
                continue
            stock = next((s for s in wl if s["name"] in title), None)
            if not stock:
                continue
            seen.add(title)
            out.append({
                "title": title, "link": getattr(e, "link", ""),
                "stock": stock["name"], "sector": stock["sector"], "when": _fmt_kst(e),
                "sort_key": _entry_datetime(e) or dt.datetime.min.replace(tzinfo=UTC),
            })
    out.sort(key=lambda x: x["sort_key"], reverse=True)
    return out[:max_items]


# ---------------------------------------------------------------------------
# 미국 뉴스 — Yahoo Finance / Investing.com RSS, 키워드 기반 가벼운 필터
# (한국 종목 매칭은 하지 않음 — 매크로 내러티브 참고용 원문 그대로)
# ---------------------------------------------------------------------------
def fetch_us_news(cfg, max_items=8):
    lookback = cfg.get("news_lookback_days", 3)
    keywords = cfg.get("us_keywords", [])

    seen, out = set(), []
    for url in cfg["us_rss_feeds"]:
        for e in _fetch_rss(url):
            title = getattr(e, "title", "")
            if not title or title in seen:
                continue
            if not _within_lookback(e, lookback):
                continue
            if keywords and not any(k.lower() in title.lower() for k in keywords):
                continue
            seen.add(title)
            out.append({
                "title": title, "link": getattr(e, "link", ""), "when": _fmt_kst(e),
                "sort_key": _entry_datetime(e) or dt.datetime.min.replace(tzinfo=UTC),
            })
    out.sort(key=lambda x: x["sort_key"], reverse=True)
    return out[:max_items]


# ---------------------------------------------------------------------------
# 렌더링 — 시나리오/점수 패널 없음. 지표 추세 + 미국뉴스 + 한국뉴스 3블록만.
# ---------------------------------------------------------------------------
def _color(pct):
    if pct is None:
        return "var(--neutral-gray)"
    return "var(--up-red)" if pct >= 0 else "var(--down-blue)"


def render_html(trends, kr_catalysts, us_news, cfg):
    now = dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")

    ind_rows = ""
    for item in cfg["indicators"]:
        name = item["name"]
        t = trends.get(name, {})
        if not t.get("ok"):
            chips = '<span class="chip chip-na">N/A</span>'
        else:
            chips = "".join(
                f'<span class="chip" style="color:{_color(p)}">{p:+.2f}%</span>'
                for p in t["pct_changes"]
            )
        ind_rows += f"""
        <div class="ind-row">
          <div class="ind-name">{name}</div>
          <div class="ind-trend">{chips}</div>
        </div>"""

    def news_block(items, show_tag):
        if not items:
            return '<div class="empty-state">최근 기간 내 조건을 충족하는 항목이 없습니다.</div>'
        cards = ""
        for it in items:
            tag = f'<span class="news-tag">{it["stock"]} · {it["sector"]}</span>' if show_tag else ""
            cards += f"""
            <a class="news-card" href="{it['link'] or '#'}" target="_blank" rel="noopener">
              <div class="news-meta">{it['when']} {tag}</div>
              <div class="news-title">{it['title']}</div>
            </a>"""
        return cards

    kr_block = news_block(kr_catalysts, show_tag=True)
    us_block = news_block(us_news, show_tag=False)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>모닝 트렌드 보드 — {now}</title>
<link rel="stylesheet" crossorigin
  href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css">
<style>
  :root {{
    --bg:#0a0d0f; --panel:#11181b; --panel-border:#1f2e31;
    --text-primary:#d7e6e4; --text-dim:#6b8482;
    --accent-phosphor:#3ddc97;
    --up-red:#ff6b6b; --down-blue:#5b9bd5; --neutral-gray:#56666a;
    --mono:'JetBrains Mono', ui-monospace, monospace;
    --sans:'Pretendard', -apple-system, sans-serif;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; padding:24px; background:var(--bg); color:var(--text-primary); font-family:var(--sans); }}
  .shell {{ max-width:820px; margin:0 auto; }}
  .header {{ display:flex; justify-content:space-between; align-items:baseline; border-bottom:1px solid var(--panel-border); padding-bottom:12px; margin-bottom:20px; }}
  .title {{ font-family:var(--mono); font-size:14px; letter-spacing:2px; color:var(--accent-phosphor); text-transform:uppercase; }}
  .time {{ font-family:var(--mono); font-size:12px; color:var(--text-dim); }}
  .section-label {{ font-family:var(--mono); font-size:11px; letter-spacing:1.5px; color:var(--text-dim); text-transform:uppercase; margin:28px 0 10px; }}
  .ind-row {{ display:flex; justify-content:space-between; align-items:center; padding:10px 12px; background:var(--panel); border:1px solid var(--panel-border); border-radius:4px; margin-bottom:6px; }}
  .ind-name {{ font-size:13px; }}
  .ind-trend {{ display:flex; gap:8px; }}
  .chip {{ font-family:var(--mono); font-size:13px; font-weight:600; min-width:60px; text-align:right; }}
  .chip-na {{ color:var(--text-dim); }}
  .news-card {{ display:block; background:var(--panel); border:1px solid var(--panel-border); border-left:3px solid var(--accent-phosphor); border-radius:4px; padding:10px 14px; margin-bottom:8px; text-decoration:none; color:var(--text-primary); }}
  .news-meta {{ font-family:var(--mono); font-size:11px; color:var(--text-dim); margin-bottom:4px; }}
  .news-tag {{ color:var(--accent-phosphor); margin-left:6px; }}
  .news-title {{ font-size:13px; line-height:1.4; }}
  .empty-state {{ color:var(--text-dim); font-size:13px; padding:14px; background:var(--panel); border:1px dashed var(--panel-border); border-radius:4px; }}
  .disclaimer {{ margin-top:28px; padding-top:14px; border-top:1px solid var(--panel-border); font-size:11px; color:var(--text-dim); line-height:1.6; }}
</style>
</head>
<body>
  <div class="shell">
    <div class="header">
      <div class="title">Morning Trend Board</div>
      <div class="time">{now} 갱신 (1일 1회)</div>
    </div>

    <div class="section-label">미국 지표 — 최근 {cfg.get("trend_days",3)}거래일 등락 (좌:오래된순 → 우:최신)</div>
    {ind_rows}

    <div class="section-label">미국 뉴스 (최근 {cfg.get("news_lookback_days",3)}일, 키워드 필터)</div>
    {us_block}

    <div class="section-label">한국 카탈리스트 — 한국경제 RSS (최근 {cfg.get("news_lookback_days",3)}일)</div>
    {kr_block}

    <div class="disclaimer">
      본 화면은 매수·매도 추천이 아니며 시나리오 판정이나 신뢰도 점수를 매기지 않습니다.
      추세인지 노이즈인지에 대한 판단과 최종 투자 결정은 전적으로 본인이 합니다.
      모든 데이터는 yfinance·한국경제 RSS·Yahoo Finance·Investing.com 공개 데이터를 그대로 정리한 것입니다.
    </div>
  </div>
</body>
</html>"""
