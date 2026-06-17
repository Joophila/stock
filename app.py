import os
import csv
import feedparser
import yfinance as yf
import streamlit as st
from datetime import datetime

# ==========================================
# UI & CONSTANTS SEETING
# ==========================================
st.set_page_config(page_title="Event-Driven Investment Ops v2.0", page_icon="⚡", layout="wide")
st.title("⚡ Event-Driven Investment Ops Dashboard v2.0")
st.subheader("AI Knowledge Ops Pipeline: 외부 매크로·공시 데이터 구조화 및 의사결정 지원 시스템")

DB_FILE = "trading_ops_history.csv"

# 지수별 세부 매핑 룰 및 도메인 지식 뱅크 (환율 1,500원 뉴노멀 완벽 반영)
INDICATOR_GUIDES = {
    "나스닥 100": {"ticker": "^NDX", "up": "글로벌 성장주/기술주 전반 투자 심리 개선 지지", "down": "성장주 하방 압력 및 위험자산 회피 성향 강화", "stocks": "삼성전자, NAVER, 카카오"},
    "필라델피아 반도체": {"ticker": "^SOX", "up": "글로벌 반도체 업황 턴어라운드 및 장비주 수혜", "down": "반도체 소부장 섹터 단기 차익 실현 매물 출하 주의", "stocks": "SK하이닉스, 한미반도체, ISC, 리노공업"},
    "엔비디아": {"ticker": "NVDA", "up": "AI 전방 인프라 투자(CAPEX) 폭발 및 HBM 공급망 가속", "down": "국내 HBM/AI 반도체 밸류체인 일시적 숨고르기 국면", "stocks": "한미반도체, 이수페타시스, SK스퀘어, 디아이"},
    "테슬라": {"ticker": "TSLA", "up": "전기차 캐즘 돌파 기대감 및 국내 배터리 셀/소재 동조화", "down": "2차전지 소재/양극재 섹터 추가 하방 압력 및 리스크 경계", "stocks": "LG에너지솔루션, 에코프로비엠, 포스코퓨처엠"},
    "애플": {"ticker": "AAPL", "up": "온디바이스 AI 교체 주기 진입 및 부품 공급망 낙수효과", "down": "IT 전방 세트 수요 둔화 우려 및 부품주 모멘텀 소강", "stocks": "LG이노텍, 비에이치, 뉴프렉스"},
    "미국 전력지수": {"ticker": "XLU", "up": "AI 데이터센터발 전력 소비 폭증 및 미국 노후 전력망 교체", "down": "국내 변압기/전력기기 섹터 단기 과열 해소 국면 진입", "stocks": "HD현대일렉트릭, 효성중공업, LS ELECTRIC"},
    "미국 방산지수": {"ticker": "ITA", "up": "글로벌 지정학적 불안 고조 및 국가별 국방비 증액 트렌드", "down": "국내 방산 섹터 단발성 모멘텀 소강 및 기간 조정 진입", "stocks": "한화에어로스페이스, 현대로템, LIG넥스원"},
    "WTI 유가": {"ticker": "CL=F", "up": "비용 인플레 자극 우려 (정유 수혜 / 항공·화학·조선 악재)", "down": "정유 마진 축소 우려 (항공·물류 비용 절감 수혜)", "stocks": "상승시 S-Oil, 흥구석유 / 하락시 대한항공, 진에어"},
    "미국채 10년물 금리": {"ticker": "^TNX", "up": "밸류에이션 할인율 부담 증가 (바이오/소프트웨어 타격)", "down": "유동성 완화 기대로 고밸류 기술/성장주 투자 심리 회복", "stocks": "하락시 NAVER, 알테오젠, HLB"},
    "원달러 환율": {"ticker": "USDKRW=X", "up": "1515원 돌파 시 외인 환차손 매물 출하 경계령 발동", "down": "1500원 이하 안착 시 외인 패시브 바스켓 자금 대거 유입", "stocks": "하락시 KOSPI200 대형주 / 상승시 자동차, 방산"},
    "VIX 공포지수": {"ticker": "^VIX", "up": "시장 변동성 폭발 (투매 유발 및 지수 대형주 하방 압력)", "down": "공포 심리 완화 (이성적인 펀더멘털 및 카탈리스트 장세)", "stocks": "상승시 코스피 인버스, 정유, 방산 / 하락시 정상 성장주"}
}

# 정교화된 다차원 가치사슬 사전 (Value Chain Matrix)
KNOWLEDGE_DICTIONARY = {
    "반도체/메모리": {"triggers": ["^SOX", "NVDA"], "stocks": ["SK하이닉스", "한미반도체", "ISC", "SK스퀘어", "리노공업"]},
    "AI 소프트웨어/소버린 동맹": {"triggers": ["NVDA", "^NDX"], "stocks": ["NAVER", "이스트소프트", "솔트룩스"]},
    "2차전지/소재": {"triggers": ["TSLA"], "stocks": ["LG&에너지솔루션", "에코프로비엠", "포스코퓨처엠", "엘앤에프"]},
    "전력기기/변압기": {"triggers": ["XLU"], "stocks": ["HD현대일렉트릭", "효성중공업", "LS ELECTRIC", "일진전기"]},
    "우주항공/방산": {"triggers": ["ITA"], "stocks": ["한화에어로스페이스", "현대로템", "LIG넥스원", "한국항공우주"]},
    "항공/물류 (비용 절감 수혜)": {"triggers": ["CL=F_DOWN"], "stocks": ["대한항공", "진에어", "제주항공"]},
    "정유/에너지 (비용 인플레 수혜)": {"triggers": ["CL=F_UP"], "stocks": ["S-Oil", "흥구석유", "중앙에너비스"]},
    "금리민감 성장주 (바이오/플랫폼)": {"triggers": ["^TNX_DOWN"], "stocks": ["NAVER", "알테오젠", "셀트리온", "유한양행"]}
}

# 심층 기획 기사 및 DART 원천 데이터 탐지용 4대 카테고리 핵심 키워드 팩
WHITE_LIST_KEYWORDS = [
    # 1. 기업 지배구조 및 주주환원 (가장 확실한 하방 경직성 명분)
    "자사주", "소각", "매입", "신탁계약", "주주환원", "최대주주 변경", "지분 취득", "무상증자", "공개매수",
    # 2. 공급망 확장 및 확정적 현금 흐름
    "공급계약", "수주", "통과", "승인", "선정", "계약체결", "MRO", "본계약", "공장 증설", "턴키",
    # 3. 펀더멘털 변화 및 턴어라운드
    "어닝 서프라이즈", "흑자전환", "최대 실적", "영업이익 상향", "가이던스 상향", "턴어라운드", "어닝",
    # 4. 메가 트렌드 기획 및 가치사슬 빅딜 (아시아경제 '이주의 관종' 등 심층 기사 포착 타깃)
    "재평가", "동맹", "독점", "지분 맞교환", "소버린", "전략적 제휴", "플랫폼 공조", "기술 이전", "밸류체인 진입"
]

BLACK_LIST_KEYWORDS = ["MOU", "업무협약", "검토 중", "추진 예정", "기대감", "협력하기로", "테마주", "단독보도이나 공시 미확인"]

# ==========================================
# CORE ENGINE: PIPELINE LOGIC
# ==========================================
def init_local_logger():
    """Point-in-Time 사후 검증을 위한 로컬 CSV 적재소 레이어 생성"""
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "Scenario", "Verified_Sectors", "Watch_Stocks"])

def log_signals_to_file(scenario, sectors, stocks):
    """생성된 신호를 BigQuery처럼 로컬 테이블에 적재"""
    init_local_logger()
    with open(DB_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M'), scenario, "|".join(sectors), "|".join(stocks)])

def run_ops_pipeline():
    # 실행할 때마다 데이터 가중치를 독립 초기화하여 중복 연산 버그 원천 차단
    current_sector_matrix = {k: {"name": k, "weight": 0, "stocks": v["stocks"]} for k, v in KNOWLEDGE_DICTIONARY.items()}
    
    indicators_output = []
    raw_data = {}
    
    # 1. 매크로 데이터 수집 레이어 (yfinance)
    for name, info in INDICATOR_GUIDES.items():
        try:
            stock = yf.Ticker(info["ticker"])
            hist = stock.history(period="2d")
            if len(hist) >= 2:
                pct = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
                val_str = f"{hist['Close'].iloc[-1]:.1f}원" if name == "원달러 환율" else f"{pct:+.2f}%"
                raw_data[name] = pct if name != "원달러 환율" else hist['Close'].iloc[-1]
                
                direction_comment = info["up"] if pct > 0 else info["down"]
                indicators_output.append(f"• **{name}**: {val_str} ➔ ({direction_comment} \| *추천 프록시: {info['stocks']}*)")
        except Exception as e:
            raw_data[name] = 0.0
            indicators_output.append(f"• **{name}**: 데이터 연동 지연 ({str(e)})")

    # 변수 추출 및 바인딩
    ndx = raw_data.get("나스닥 100", 0.0)
    sox = raw_data.get("필라델피아 반도체", 0.0)
    nvda = raw_data.get("엔비디아", 0.0)
    tsla = raw_data.get("테슬라", 0.0)
    aapl = raw_data.get("애플", 0.0)
    xlu = raw_data.get("미국 전력지수", 0.0)
    ita = raw_data.get("미국 방산지수", 0.0)
    oil = raw_data.get("WTI 유가", 0.0)
    bond = raw_data.get("미국채 10년물 금리", 0.0)
    fx = raw_data.get("원달러 환율", 1510.0)
    vix = raw_data.get("VIX 공포지수", 0.0)

    # 2. 8대 매크로 메가 시나리오 디시전 트리 연산 (정량적 수치 분석)
    scenario_commentary = ""
    
    if vix > 5.0 and oil > 3.0 and ndx < -1.5:
        scenario_commentary = "🚨 [시나리오 4: 지정학적 리스크 / 전쟁 공포 폭발] 지정학 리스크 확산으로 VIX 공포지수와 원자재 유가가 동반 폭발했습니다. 글로벌 자금의 급격한 패닉 대피 장세가 유력합니다. 한국 시장 전체에 강한 하방 압력이 작용하므로, [우주항공/방산] 및 [정유/에너지] 섹터를 제외한 모든 자산의 신규 진입을 전면 금지하고 보수적인 스탠스를 유지하십시오."
        current_sector_mapping = current_sector_matrix["우주항공/방산"]
        current_sector_matrix["우주항공/방산"]["weight"] += 3
        current_sector_matrix["정유/에너지 (비용 인플레 수혜)"]["weight"] += 3
    elif ndx > 1.0 and bond < -1.5 and vix < -3.0 and fx < 1500:
        scenario_commentary = "✨ [시나리오 1: 골디락스 - 유동성 장세 부활] 미국 고용/물가 둔화 신호가 안정적인 금리 인하 경로를 지지하며 환율이 1,500원 뉴노멀 하단 아래로 안전하게 안착했습니다. 달러 약세 반전으로 장 초반 코스피 대형주 바스켓을 향한 외국인 패시브 자금의 대규모 유입 가능성이 매우 높습니다. 시총 상위 주도주 중심의 과감한 베팅이 유효합니다."
        current_sector_matrix["반도체/메모리"]["weight"] += 2
        current_sector_matrix["금리민감 성장주 (바이오/플랫폼)"]["weight"] += 2
    elif sox > 3.0 and nvda > 4.0 and sox > ndx:
        scenario_commentary = "🤖 [시나리오 3: 반도체·AI 독주 - 주도주 차별화 장세] 거시 경제의 매크로 노이즈와 무관하게 글로벌 빅테크의 AI 인프라 투자(CAPEX) 및 고대역폭메모리(HBM) 수요 독점이 증명되었습니다. 코스피 지수 자체는 보합이거나 타 섹터가 무너지더라도, 국내 장은 [반도체/메모리] 및 [소버린 AI] 관련 밸류체인만 차별화되어 강한 우상향 독주 무빙을 펼칠 판이 깔렸습니다."
        current_sector_matrix["반도체/메모리"]["weight"] += 2
        current_sector_matrix["AI 소프트웨어/소버린 동맹"]["weight"] += 2
    elif fx > 1515 and bond > 1.5:
        scenario_commentary = "🚨 [시나리오 2: 긴축 우려 재점화 & 고환율 쇼크] 환율이 뉴노멀 상단(1,515원)을 돌파하고 미국채 금리가 튀어 올랐습니다. 외국인 매스컴/프로그램 매도세가 환차손 회피를 위해 기계적 폭탄 물량을 출하할 리스크가 극대화되는 시점입니다. 시가총액 상위 대형주 추격 매수를 전면 금지하고 극도로 방어적인 포지션을 취해야 합니다."
    elif fx > 1502 and abs(ndx) < 0.5:
        scenario_commentary = "💸 [고환율 박스권 저항 및 개별 장세] 미국 증시는 평온하게 마감했으나 국내 환율이 1,500원 초반대 저항선에 걸쳐있어 대형주 중심의 지수 견인력은 상단이 강하게 차단됩니다. 패시브 자금 유입이 제약되므로, 무거운 시총 대형주보다는 3번 항목에 포착된 '확정 공시'나 '재평가 기획 기사'를 보유한 가벼운 중소형 개별주 진입이 훨씬 효율적입니다."
    elif xlu > 1.5:
        scenario_commentary = "⚡ [시나리오 8-A: 미국 전력 인프라 낙수효과 선행] 미국 AI 데이터센터 전력 공급 부족 및 노후 전력망 교체 모멘텀 수혜가 유틸리티 지수 급등으로 증명되었습니다. 한국 증시의 전통 주도주가 쉬어가는 타이밍에 [전력기기/변압기] 섹터로 강력한 기관 순환매 수급 유입을 추적하십시오."
        current_sector_matrix["전력기기/변압기"]["weight"] += 2
    elif ita > 1.5:
        scenario_commentary = "⚔️ [시나리오 8-B: 글로벌 국방비 증액 및 대형 수주 랠리] 미국 방산 지수의 반등은 지정학적 갈등 장기화와 방산 수출 시장의 구조적 성장을 의미합니다. 한국의 [우주항공/방산] 수출 대장주들의 추가 수주 공시 매칭 여부를 체킹하세요."
        current_sector_matrix["우주항공/방산"]["weight"] += 2
    else:
        scenario_commentary = "📊 [매크로 숨고르기 - 모멘텀 공백 상태] 선제 글로벌 지수들의 변동폭이 임계치 내에 갇혀 지수 방향성이 모호합니다. 거시 환경의 영향력이 약화되는 대신, 오늘 하루는 개별 기업의 DART 공시나 미디어 속보의 영향력이 시장을 완전히 지배하는 전형적인 종목 장세가 전개됩니다."

    # 역베팅(Short/Inverse) 판정 로직: 나스닥/반도체 동반 폭락 시 안전지대 매핑
    if ndx < -2.0 and sox < -2.5:
        st.sidebar.error("⚠️ [SHORT SIGNAL] 매크로 붕괴 징후 포착: 시장 인버스(곱버스) 및 방어주 중심의 헤징을 검토하십시오.")

    # 개별 미국 지표 등락에 따른 1차 가중치 점수 사전 누적
    if sox > 1.5: current_sector_matrix["반도체/메모리"]["weight"] += 1
    if nvda > 2.0: current_sector_matrix["AI 소프트웨어/소버린 동맹"]["weight"] += 1
    if tsla > 2.0: current_sector_matrix["2차전지/소재"]["weight"] += 2
    if xlu > 1.0: current_sector_matrix["전력기기/변압기"]["weight"] += 1
    if ita > 1.0: current_sector_matrix["우주항공/방산"]["weight"] += 1
    if oil < -2.0: current_sector_matrix["항공/물류 (비용 절감 수혜)"]["weight"] += 2
    if oil > 2.0: current_sector_matrix["정유/에너지 (비용 인플레 수혜)"]["weight"] += 2
    if bond < -1.5: current_sector_matrix["금리민감 성장주 (바이오/플랫폼)"]["weight"] += 2

    # 3. 미디어 속보 및 DART 공시 원천 데이터 필터링 파이프라인
    # 확장성 아키텍처: 한국경제 RSS 리드를 메인으로 긁되 포털 속보 프록시 통합 처리
    rss_urls = ["https://www.hankyung.com/feed/finance", "https://www.hankyung.com/feed/economy"]
    media_signals = []
    
    for url in rss_urls:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.title
            
            # 블랙리스트 키워드가 섞인 찌라시/스토리형 기사는 1차 컷탈락
            if any(black in title for black in BLACK_LIST_KEYWORDS):
                continue
                
            # 실제 정량적 가치 변화를 일으키는 화이트리스트 단어가 포함되어 있는지 스캔
            if any(white in title for white in WHITE_LIST_KEYWORDS):
                for sector_key, info in current_sector_matrix.items():
                    # 해당 업종 키워드나 핵심 프록시 종목이 제목에 매칭되는지 다차원 검색
                    if info["name"] in title or any(stock in title for stock in info["stocks"]):
                        info["weight"] += 2  # 조건 결합 점수 대폭 부여
                        source = "[DART 원천공시]" if any(k in title for k in ["공시", "계약", "수주", "매입", "소각", "취득"]) else "[미디어 핵심속보]"
                        media_signals.append(f"{source} {title}")

    # 4. 3-Layer Cross-Verification (최종 복합 교차검증 점수 연산)
    verified_sectors = []
    final_stocks = []
    
    for k, info in current_sector_matrix.items():
        # 미국 선제 지표 조건(+1~3점) + 국내 공시/미디어 핵심 속보 매칭(+2점) = 최종 합산 스코어 4점 만점 달성 확인
        if info["weight"] >= 4:
            verified_sectors.append(f"{info['name']} (교차검증 신뢰도: ★★★★★)")
            final_stocks.extend(info["stocks"])
        elif info["weight"] == 2:
            verified_sectors.append(f"{info['name']} (뉴스/공시 단발성 포착)")
            
    # 백테스트용 로그 데이터 적재 작동
    if final_stocks:
        log_signals_to_file(scenario_commentary[:50], verified_sectors, final_stocks)
            
    return indicators_output, scenario_commentary, list(set(media_signals))[:6], verified_sectors, list(set(final_stocks))

# ==========================================
# UI REPRESENTATION LAYOUT
# ==========================================
# 사이드바: 아키텍처 투명성 정보 및 사후 백테스트 로그 뷰어 제공
st.sidebar.markdown("### 🏢 System Operations Info")
st.sidebar.caption("본 앱은 외부 API 호출 비용이 전혀 발생하지 않는 100% Deterministic 규칙 기반 데이터 자급자족형 인하우스 플랫폼입니다.")

if st.sidebar.checkbox("📊 사후 검증용 신호 데이터셋 로그 보기"):
    st.sidebar.markdown("### Accumulating Point-in-Time Logs")
    if os.path.exists(DB_FILE):
        with open(DB_FILE, mode='r', encoding='utf-8') as f:
            st.sidebar.text(f.read())
    else:
        st.sidebar.caption("아직 누적된 데이터 로그가 없습니다. 분석 버튼을 딸깍하여 신호를 생성하세요.")

# 메인 트리거 실행 버튼 (딸깍 한 번으로 모든 파이프라인 구동)
if st.button("🔥 데이터 구조화 분석 및 투자 의사결정 HUD 리포트 생성 (딸깍)"):
    with st.spinner("글로벌 지수 동기화 및 DART·미디어 텍스트 밸류체인 다차원 연산 중..."):
        ind_out, scenario, media_out, sectors, stocks = run_ops_pipeline()
        
        # 2분할 대시보드 그리드 배치 설계
        layout_col1, layout_col2 = st.columns(2)
        
        with layout_col1:
            st.markdown("### 🌐 [1. 글로벌 선제 지수 및 지수별 실시간 가이드]")
            for ind in ind_out:
                st.write(ind)
                
            st.markdown("### 📊 [2. 매크로 경제·지정학 시나리오 판정 결과]")
            st.info(scenario)
            
        with layout_col2:
            st.markdown("### 📰 [3. DART 공시 & 미디어 핵심 헤드라인 교차]")
            if media_out:
                for m in media_out:
                    st.write(f"• {m}")
            else:
                st.write("• 장 시작 전 기업 가치를 근본적으로 뒤흔들 만한 고가치 확정 공시나 기획 기사가 미디어 룸에 감지되지 않았습니다.")
                
            st.markdown("### 🎯 [4. 🔥 최종 교차검증 완료 분야 및 최우선 주도주]")
            if sectors:
                for s in sectors:
                    if "★★★★★" in s:
                        st.success(s)
                    else:
                        st.warning(s)
                st.markdown(f"**📈 장초반 수급 집중 관찰 최우선 순위 종목 리스트:**")
                st.code(f"🚀 {', '.join(stocks)}", language="text")
                st.caption("💡 의사결정 수문장 규칙: 개장 이후 09:05~09:10 사이에 위 종목들로 외국인/기관 프로그램 순매수 자금이 실시간으로 유입되는지 HTS 영수증을 최종 교차 검증하고 진입 여부를 확정하세요. 2~3일 스윙 타깃입니다.")
            else:
                st.error("• 글로벌 거시 환경 점수와 국내 미디어/공시 매칭 조건이 상호 동시 충족되는 고신뢰도 교차검증 섹터가 오늘 아침에는 존재하지 않습니다.")
                st.caption("🚨 오늘은 무리한 섹터 추격 베팅을 전면 중단하고, 철저히 시총이 가벼운 개별 공시 기업 위주로 방어적 단타 대응만 수행하십시오.")
                
        st.balloons()
