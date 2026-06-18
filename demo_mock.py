"""
demo_mock.py — 네트워크/키 없이 모의 데이터로 화면만 미리 확인.
실제 운영은 main.py (GitHub Actions 등 인터넷이 열린 환경에서 실행).
"""
from pathlib import Path
from hud_core import load_config, render_html

OUT_DIR = Path(__file__).parent / "output"

MOCK_TRENDS = {
    "나스닥100": {"pct_changes": [0.21, 0.85, 1.42], "ok": True},
    "필라델피아반도체(SOX)": {"pct_changes": [-0.30, 1.80, 4.10], "ok": True},
    "엔비디아": {"pct_changes": [0.50, 2.10, 6.17], "ok": True},
    "테슬라": {"pct_changes": [1.10, -0.40, -0.81], "ok": True},
    "애플": {"pct_changes": [0.10, 0.05, 0.30], "ok": True},
    "미국전력(XLU)": {"pct_changes": [0.20, 0.10, 0.50], "ok": True},
    "미국방산(ITA)": {"pct_changes": [0.05, 0.10, 0.20], "ok": True},
    "WTI유가": {"pct_changes": [-0.50, 0.30, 0.91], "ok": True},
    "미국채10년물": {"pct_changes": [0.02, -0.01, -0.03], "ok": True},
    "VIX": {"pct_changes": [-1.20, -0.80, -2.74], "ok": True},
    "원달러환율": {"pct_changes": [0.05, 0.10, 0.18], "ok": True},
}

MOCK_KR = [
    {"title": "SK하이닉스, 3조원 규모 HBM4 공급계약 체결", "link": "https://www.hankyung.com/article/mock1",
     "stock": "SK하이닉스", "sector": "반도체", "when": "06/18 07:10"},
    {"title": "한화에어로스페이스, 역대 최대 수주 공시", "link": "https://www.hankyung.com/article/mock2",
     "stock": "한화에어로스페이스", "sector": "방산", "when": "06/17 18:40"},
]

MOCK_US = [
    {"title": "Fed officials signal openness to rate cut as inflation cools",
     "link": "https://finance.yahoo.com/mock3", "when": "06/18 05:30"},
    {"title": "Chip stocks surge after Nvidia raises data center capex guidance",
     "link": "https://www.investing.com/mock4", "when": "06/17 22:15"},
]


def run():
    cfg = load_config()
    OUT_DIR.mkdir(exist_ok=True)
    html = render_html(MOCK_TRENDS, MOCK_KR, MOCK_US, cfg)
    (OUT_DIR / "trend_board_demo.html").write_text(html, encoding="utf-8")
    print(f"생성됨: {OUT_DIR / 'trend_board_demo.html'}")


if __name__ == "__main__":
    run()
