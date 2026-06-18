"""
main.py — 하루 1회 실행. 미국 지표 추세 + 미국/한국 뉴스를 모아 docs/index.html로 출력.
"""
from pathlib import Path
from hud_core import load_config, fetch_indicator_trends, fetch_kr_catalysts, fetch_us_news, render_html

OUT_DIR = Path(__file__).parent / "output"


def run():
    cfg = load_config()

    trends = fetch_indicator_trends(cfg)
    kr_catalysts = fetch_kr_catalysts(cfg)
    us_news = fetch_us_news(cfg)

    OUT_DIR.mkdir(exist_ok=True)
    html = render_html(trends, kr_catalysts, us_news, cfg)
    (OUT_DIR / "index.html").write_text(html, encoding="utf-8")

    print(f"생성 완료: {OUT_DIR / 'index.html'}")
    print(f"  미국 지표 {len(trends)}개 / 한국 카탈리스트 {len(kr_catalysts)}건 / 미국 뉴스 {len(us_news)}건")


if __name__ == "__main__":
    run()
