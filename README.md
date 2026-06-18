# Morning Trend Board (단순화 버전)

미국 지표 최근 3거래일 등락 + 미국 뉴스(키워드 필터) + 한국경제 카탈리스트(watchlist 매칭),
세 블록을 해석 없이 나란히 보여주는 개인용 보드. 시나리오 판정이나 ★ 신뢰도 점수는 없다 —
"추세인지 노이즈인지" 판단은 본인이 직접 한다는 전제로 일부러 뺐다.

이전 버전(시나리오 8개+교차검증 점수+RSS/네이버/DART 3소스+10분 간격 갱신)은 복잡도가
너무 올라가서 토큰 제한에 걸렸다. 이 버전은 핵심 로직 파일이 1개(`hud_core.py`)뿐이고,
자동 매매·카카오·DART·네이버 연동을 전부 뺐다. 필요해지면 그때 하나씩 더한다.

## 데이터는 진짜인가

`main.py`가 실행하는 `hud_core.fetch_indicator_trends()` / `fetch_kr_catalysts()` /
`fetch_us_news()`는 실제로 yfinance·한국경제 RSS·Yahoo Finance RSS·Investing.com RSS를
호출한다. 다만 이 코드를 만든 작업 환경 자체가 보안상 그 도메인들에 접속할 수 없어서, 직접
실행해 실데이터를 보여줄 수는 없었다 — 대신 모든 소스가 막힌 상태로 `main.py`를 실제로
돌려봐서, 죽지 않고 지표는 N/A·뉴스는 "조건을 충족하는 항목 없음"으로 안전하게 처리되는
것까지 확인했다. `demo_mock.py`는 그 화면이 어떻게 보이는지 모의데이터로 미리 보는 용도다.

```bash
pip install -r requirements.txt
python demo_mock.py   # 키/네트워크 없이 화면만 미리보기 → output/trend_board_demo.html
python main.py        # 실제 파이프라인 (인터넷이 열린 환경에서 실행해야 진짜 데이터)
```

## 운영 설정

1. 이 폴더를 GitHub repo로 push.
2. repo Settings → Pages → Source를 `main` 브랜치 `/docs` 폴더로 지정.
   이후 `https://<아이디>.github.io/<repo명>/`을 휴대폰에 북마크해두면 매일 아침 7시 이후
   갱신된 화면을 본다.
3. Actions 탭에서 워크플로를 한 번 수동 실행(`workflow_dispatch`)해서 정상 동작 확인.

## 비용

GitHub Actions(하루 1회, 무료 티어로 충분) + yfinance + 한국경제/Yahoo/Investing RSS +
GitHub Pages, 전부 0원.

## 커스터마이즈는 config.json만

- `trend_days`: 며칠치 추세를 볼지 (기본 3일)
- `news_lookback_days`: 뉴스 수집 기간 (기본 3일)
- `watchlist`: 관심종목·섹터
- `catalyst_whitelist` / `catalyst_blacklist`: 한국 뉴스 필터 키워드
- `us_keywords`: 미국 뉴스 필터 키워드
- `kr_rss_feeds` / `us_rss_feeds`: 소스 추가/교체

## 의도적으로 뺀 것 (필요해지면 다시 요청하면 됨)

- 8대 매크로 시나리오 판정, ★ 교차검증 점수 — 해석은 본인이 직접
- 네이버 검색 API, DART 공시 연동 — 한경 RSS 하나로 며칠 써보고 부족하면 추가
- 카카오 알림 — 필요 없다고 해서 제외
- 자동매매 — 애초에 고려 대상 아님, 어디에도 주문 API 연결 없음
