"""2026 분기별 최고의 애니는? - Streamlit 대시보드

data/anime.csv(collect.py가 수집)만 읽는다. 앱에서 API를 호출하지 않는다.
실행: streamlit run app.py
"""
import html
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

DATA_DIR = Path(__file__).parent / "data"
TOP_N = 10

st.set_page_config(page_title="2026 분기별 최고의 애니는?", layout="wide")

# 브라우저가 이 페이지를 영어로 착각해 자동 번역하면 한국어 글이 이상하게 바뀐다.
# 그래서 페이지 언어를 한국어(ko)로 알리고 '번역 금지' 표식을 단다.
NO_TRANSLATE_JS = """<script>
const d = window.parent.document;
d.documentElement.lang = "ko";
d.documentElement.setAttribute("translate", "no");
if (!d.querySelector('meta[name="google"]')) {
  const m = d.createElement("meta"); m.name = "google"; m.content = "notranslate"; d.head.appendChild(m);
}
</script>"""
if hasattr(st, "iframe"):  # 최신 Streamlit
    st.iframe(NO_TRANSLATE_JS, height=1)
else:  # 예전 Streamlit
    components.html(NO_TRANSLATE_JS, height=0)

# AniList의 시즌 이름 -> 한국식 분기 이름
SEASON_KO = {"WINTER": "1분기(겨울)", "SPRING": "2분기(봄)", "SUMMER": "3분기(여름)", "FALL": "4분기(가을)"}
SEASON_ORDER = {"WINTER": 1, "SPRING": 2, "SUMMER": 3, "FALL": 4}
# AniList의 장르 이름(영어) -> 화면에 보여 줄 한국어 이름. 목록에 없는 장르는 영어 그대로 보여 준다.
GENRE_KO = {
    "Action": "액션", "Adventure": "모험", "Comedy": "코미디", "Drama": "드라마", "Ecchi": "에치",
    "Fantasy": "판타지", "Horror": "공포", "Mahou Shoujo": "마법소녀", "Mecha": "메카", "Music": "음악",
    "Mystery": "미스터리", "Psychological": "심리", "Romance": "로맨스", "Sci-Fi": "SF",
    "Slice of Life": "일상", "Sports": "스포츠", "Supernatural": "초자연", "Thriller": "스릴러",
}
SEASON_MONTHS = {"WINTER": "1~3월", "SPRING": "4~6월", "SUMMER": "7~9월", "FALL": "10~12월"}

# 지표 4개: 이름, 정규화된 컬럼, 가중치 키, 차트 색(파스텔)
PARTS = [
    ("끝까지 본다(하차율↓)", "n_drop", "drop", "#34C38F"),
    ("평점", "n_score", "score", "#4C8DF6"),
    ("즐겨찾기 비율", "n_fav", "fav", "#A98BEA"),
    ("인기(담은 사람 수)", "n_pop", "pop", "#F6C453"),
]
ACCENT, GRAY = "#3B82F6", "#D6DCE5"
# 제작사 이름(영문) -> 한국어 표기. 차트에 나오는 3편 이상 제작사만 옮겼고, 목록에 없는 곳은 원래 이름 그대로 보여 준다.
STUDIO_KO = {
    "LIDENFILMS": "리덴필름스", "OLM": "OLM", "Studio DEEN": "스튜디오 딘", "Studio KAI": "스튜디오 카이",
    "Zero-G": "제로지", "SILVER LINK.": "실버 링크", "SynergySP": "시너지SP", "ENGI": "엔지",
    "TMS Entertainment": "TMS 엔터테인먼트", "Bandai Namco Pictures": "반다이 남코 픽처스",
    "Studio Comet": "스튜디오 코멧", "East Fish Studio": "이스트 피시 스튜디오", "Doga Kobo": "동화공방",
    "MAPPA": "마파", "Studio Pierrot": "스튜디오 피에로", "Brain's Base": "브레인즈 베이스",
    "project No.9": "프로젝트 No.9", "Maho Film": "마호 필름", "TROYCA": "트로이카", "MADHOUSE": "매드하우스",
    "Sunrise": "선라이즈", "J.C.STAFF": "J.C.스태프", "bones film": "본즈 필름", "Satelight": "새틀라이트",
    "Passione": "파시오네", "diomedéa": "디오메데아",
}
# 스트리밍 플랫폼 이름 -> 한국어 표기. 목록에 없는 곳은 원래 이름 그대로 보여 준다.
PLATFORM_KO = {
    "Crunchyroll": "크런치롤", "YouTube": "유튜브", "Bilibili TV": "비리비리 TV", "iQ": "iQIYI(아이치이)",
    "Netflix": "넷플릭스", "Amazon Prime Video": "아마존 프라임 비디오", "HIDIVE": "하이다이브",
    "Hulu": "훌루", "Disney Plus": "디즈니+", "OceanVeil": "오션베일", "Viki": "비키", "Laftel": "라프텔",
}
SOURCE_KO = {"MANGA": "만화", "LIGHT_NOVEL": "라이트노벨", "ORIGINAL": "오리지널"}  # 그 외는 '기타'
FONT = "Noto Sans KR, sans-serif"

# "가중치를 바꿔도 남는 작품"을 찾기 위한 비교 시나리오 (하차율, 평점, 즐겨찾기 비율, 인기 순서)
SCENARIOS = {
    "균등": dict(drop=25, score=25, fav=25, pop=25),
    "끝까지 보기 중심": dict(drop=70, score=10, fav=10, pop=10),
    "평점 중심": dict(drop=10, score=70, fav=10, pop=10),
    "즐겨찾기 중심": dict(drop=10, score=10, fav=70, pop=10),
    "인기 중심": dict(drop=10, score=10, fav=10, pop=70),
}

# ---------------------------------------------------------------- 디자인 (CSS)
# 크림색 배경, 둥근 흰 카드, 파스텔 포인트. 글꼴은 Google Fonts에서 불러온다(없으면 기본 글꼴).
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600&display=swap');
.stApp :where(p, label, div, li, a, button, input, textarea, td, th, summary, small, h1, h2, h3, h4),
.stApp span:not([data-testid="stIconMaterial"]) { font-family: 'Noto Sans KR', sans-serif; }
.stApp h2, .stApp h3, .hero h1, .stat b, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    font-family: 'Noto Sans KR', sans-serif !important; font-weight: 600 !important; letter-spacing: -0.02em; }
.block-container { padding-top: 1.6rem; max-width: 1280px; }
.stApp h3 { font-size: 1.15rem !important; }
header[data-testid="stHeader"] { background: transparent; }

/* 흰 카드 + 얇은 테두리 */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #fff; border: 1px solid #E6EAF0 !important; border-radius: 16px; padding: 0.9rem 1.1rem 0.5rem;
    box-shadow: none; }
[data-testid="stSidebar"] { background: #fff; border-right: 1px solid #E6EAF0; }
[data-testid="stExpander"] { background: #fff; border: 1px solid #E6EAF0; border-radius: 16px; }
[data-testid="stExpander"] details { border: none; }

/* 맨 위 소개 카드 */
.hero { background: #fff; border: 1px solid #E6EAF0; border-radius: 16px; padding: 22px 28px; }
.hero h1 { font-size: 1.75rem; line-height: 1.3; margin: 0 0 8px; padding: 0; }
.hero .kick { font-size: .8rem; color: #3B82F6; font-weight: 600; margin: 0 0 6px; }
.hero .q { font-size: 1rem; margin: 0 0 6px; color: #1F2937; }
.hero .how { font-size: .9rem; margin: 0 0 6px; color: #6B7280; }
.hero .src { font-size: .8rem; color: #9AA3AF; margin: 0; }

/* 요약 숫자: 흰 카드 안의 회색 타일 */
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px;
    background: #fff; border: 1px solid #E6EAF0; border-radius: 16px; padding: 14px; margin: 14px 0 10px; }
.stat { border-radius: 12px; padding: 14px 18px; background: #F4F6FA; }
.stat span { font-size: .82rem; display: block; color: #6B7280; }
.stat b { font-size: 1.7rem; line-height: 1.3; display: block; word-break: keep-all; color: #1F2937; }
.stat.long b { font-size: 1.15rem; }
.stat em { font-style: normal; font-size: .82rem; color: #3B82F6; }

/* 현재 조건 알약 */
.chips { margin: 4px 0 12px; }
.chip { display: inline-block; border-radius: 999px; padding: 3px 12px; margin: 0 6px 6px 0; font-size: .82rem; font-weight: 500; }
.chip.yellow { background: #E8F0FE; color: #1D4ED8; } .chip.pink { background: #E6F7F0; color: #157F5B; }
.chip.mint { background: #F1ECFD; color: #6D4BC4; } .chip.blue { background: #FFF5DB; color: #9A6B00; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)



# ---------------------------------------------------------------- 데이터 읽기
def data_version():
    """CSV 파일이 바뀌면 값이 바뀌는 표식. 이 값이 달라지면 캐시를 버리고 다시 읽는다."""
    names = ["anime.csv", "title_ko.csv", "title_ko_tmdb.csv"]
    return tuple((DATA_DIR / n).stat().st_mtime for n in names if (DATA_DIR / n).exists())


@st.cache_data
def load_data(version):
    df = pd.read_csv(DATA_DIR / "anime.csv")

    # 표시 제목: 직접 고친 제목(title_ko.csv) > TMDB 한국어 제목 > 영문 제목 > 일본어 원제.
    # 로마자(romaji)는 쓰지 않는다. (일본어 원제는 알아보기 어려워서 마지막 순위, 표에는 따로 보여 준다)
    def ko_map(filename):
        path = DATA_DIR / filename
        if not path.exists():
            return {}
        ko = pd.read_csv(path).dropna(subset=["id", "title_ko"])
        return dict(zip(ko["id"], ko["title_ko"]))

    df["title"] = (df["id"].map(ko_map("title_ko.csv"))
                   .fillna(df["id"].map(ko_map("title_ko_tmdb.csv")))
                   .fillna(df["title_english"]).fillna(df["title_native"]))

    # 하차율 = 하차 / (보는 중 + 완료 + 하차 + 보류). 볼 예정(PLANNING)은 뺀다.
    den = df["n_current"] + df["n_completed"] + df["n_dropped"] + df["n_paused"]
    df["drop_rate"] = df["n_dropped"] / den.where(den > 0)
    # 즐겨찾기 비율 = 즐겨찾기(favourites) 수 / 목록에 담은 사람 수(popularity)
    df["fav_rate"] = df["favourites"] / df["popularity"]
    df["genres"] = df["genres"].fillna("")
    return df


def quarter_name(q):
    year, season = q.split()
    return f"{year}년 {SEASON_KO[season]}"


def make_label(d):
    """차트에 쓸 짧은 제목. 너무 길면 자르고, 같은 이름이 있으면 번호를 붙인다."""
    s = d["title"].str.slice(0, 16)
    s = s.where(d["title"].str.len() <= 16, s + "…")
    dup = s.groupby(s).cumcount()
    return s.where(dup == 0, s + " (" + (dup + 1).astype(str) + ")")


# ---------------------------------------------------------------- 점수 계산
def minmax(s):
    """가장 낮은 값 0, 가장 높은 값 1로 맞춘다. 값이 모두 같으면 0.5."""
    rng = s.max() - s.min()
    return (s - s.min()) / rng if rng > 0 else s * 0 + 0.5


def add_normalized(d):
    d = d.copy()
    d["n_score"] = minmax(d["averageScore"])
    d["n_pop"] = minmax(np.log10(d["popularity"]))  # 인기는 격차가 커서 로그를 씌운다
    d["n_fav"] = minmax(d["fav_rate"])
    d["n_drop"] = 1 - minmax(d["drop_rate"])  # 하차율은 낮을수록 좋으므로 뒤집는다
    return d


def total_score(d, w):
    """가중 평균 x 100. 가중치 합이 100이 아니어도 비율로 환산된다."""
    wsum = sum(w.values())
    return (d["n_drop"] * w["drop"] + d["n_score"] * w["score"]
            + d["n_fav"] * w["fav"] + d["n_pop"] * w["pop"]) / wsum * 100


def style(fig, height=None):
    fig.update_layout(template="plotly_white", font=dict(size=13, family=FONT, color="#1F2937"), height=height,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      margin=dict(l=10, r=10, t=90, b=10),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    fig.update_xaxes(gridcolor="#EDF0F4", zerolinecolor="#D6DCE5")
    fig.update_yaxes(gridcolor="#EEE8E1")
    return fig


df = load_data(data_version())

# ---------------------------------------------------------------- 사이드바 위젯
st.sidebar.header("조건 바꾸기")

quarters = sorted(df["quarter"].unique(),
                  key=lambda q: (int(q.split()[0]), SEASON_ORDER[q.split()[1]]), reverse=True)
default_idx = quarters.index("2026 SUMMER") if "2026 SUMMER" in quarters else 0
quarter = st.sidebar.selectbox("분기", quarters, index=default_idx, format_func=quarter_name)

kind = st.sidebar.radio("신작 / 후속작", ["전체", "신작만", "후속작만"])

dq = df[df["quarter"] == quarter]
all_genres = sorted({g for gs in dq["genres"] for g in gs.split("|") if g})
genres = st.sidebar.multiselect("장르 (여러 개를 고르면 하나라도 해당하는 작품)", all_genres,
                                format_func=lambda g: GENRE_KO.get(g, g))

min_pop = st.sidebar.slider("최소 인기 기준 (담은 사람 수)", 0, 30000, 5000, step=500,
                            help="이 작품을 '내 목록'에 담은 사람의 수예요(AniList 이용자 기준). 이보다 적은 작품은 평가가 몇 명에 "
                                 "좌우되어 불안정하니 비교에서 뺍니다. 기본값은 5,000명이에요.")

st.sidebar.subheader("무엇을 더 중요하게 볼까요?")
st.sidebar.caption("숫자가 클수록 종합 점수에 크게 반영돼요. 합이 100이 아니어도 비율로 맞춰져요.")
w = dict(
    drop=st.sidebar.slider("끝까지 본다 (하차율이 낮을수록 ↑)", 0, 100, 40, step=5,
                           help="보기 시작한 사람 중 중간에 그만둔 사람(하차)의 비율이 낮을수록 높은 점수를 줘요."),
    score=st.sidebar.slider("평점", 0, 100, 25, step=5, help="AniList 이용자들이 이 작품에 준 점수(100점 만점)의 평균이에요."),
    fav=st.sidebar.slider("즐겨찾기 비율", 0, 100, 20, step=5,
                          help="이 작품을 담은 사람 중에서 즐겨찾기(하트)까지 누른 사람의 비율이에요."),
    pop=st.sidebar.slider("인기 (담은 사람 수)", 0, 100, 15, step=5,
                          help="이 작품을 '내 목록'에 담은 사람의 수예요. 많을수록 많이 알려진 작품이에요."),
)

# ---------------------------------------------------------------- 조건에 맞게 거르기
d = dq.copy()
if kind == "신작만":
    d = d[~d["has_prequel"]]
elif kind == "후속작만":
    d = d[d["has_prequel"]]
if genres:
    d = d[d["genres"].apply(lambda gs: any(g in gs.split("|") for g in genres))]
d = d[d["popularity"] >= min_pop]
n_before = len(d)
d = d.dropna(subset=["averageScore", "drop_rate"]).reset_index(drop=True)

# ---------------------------------------------------------------- 제목과 설명
collected_at = df["collected_at"].iloc[0]

# 질문 문장: 왼쪽에서 고른 분기, 신작/후속작, 장르에 맞게 바뀐다.
q_year, q_season = quarter.split()
kind_txt = {"전체": "", "신작만": "신작 ", "후속작만": "후속작 "}[kind]
genre_txt = f"({', '.join(GENRE_KO.get(g, g) for g in genres)} 장르) " if genres else ""
question = (f"{q_year}년 {SEASON_KO[q_season].split('(')[0]}({SEASON_MONTHS[q_season]})에 방영된 "
            f"{kind_txt}TV 애니 {genre_txt}중 최고의 작품은 무엇인가?")

st.markdown(
    '<div class="hero"><div>'
    '<p class="kick">2026 · TV 애니 · AniList 공개 데이터</p>'
    '<h1>2026 분기별 최고의 애니는?</h1>'
    f'<p class="q">{html.escape(question)}</p>'
    '<p class="how">평점, 인기, 끝까지 보는 사람의 비율, 즐겨찾기 비율을 합쳐서 종합 점수를 매기고, 작품별로 한 번, 원작 종류·제작사별로 한 번 더 비교했어요.</p>'
    f'<p class="src">데이터: AniList 공개 데이터 · 한국어 제목: TMDB · 수집 일시: {html.escape(collected_at)}</p>'
    '</div></div>',
    unsafe_allow_html=True)

# 지금 걸려 있는 조건을 알약(chip)으로 보여 준다
chips = [("yellow", quarter_name(quarter))]
if kind != "전체":
    chips.append(("pink", kind))
chips += [("mint", GENRE_KO.get(g, g)) for g in genres]
chips.append(("blue", f"담은 사람 {min_pop:,}명 이상"))
chips.append(("yellow", f"중요도: 끝까지 {w['drop']} · 평점 {w['score']} · 즐겨찾기 {w['fav']} · 인기 {w['pop']}"))
st.markdown('<div class="chips">' + "".join(
    f'<span class="chip {c}">{html.escape(t)}</span>' for c, t in chips) + '</div>', unsafe_allow_html=True)

if sum(w.values()) == 0:
    st.warning("중요도가 모두 0이에요. 하나 이상 올려 주세요.")
    st.stop()
if len(d) < 3:
    st.warning("비교할 작품이 3개보다 적어요. 필터를 조금 풀어 주세요.")
    st.stop()

# 점수 계산 (지금 걸러진 작품들 안에서 상대평가)
d = add_normalized(d)
d["total"] = total_score(d, w)
d["label"] = make_label(d)
top = d.nlargest(TOP_N, "total")
top_labels = set(top["label"])

# ---------------------------------------------------------------- 요약 숫자
t1 = top.iloc[0]
long_cls = " long" if len(t1["title"]) > 12 else ""
st.markdown(
    '<div class="stats">'
    f'<div class="stat yellow"><span>비교 대상 작품 수</span><b>{len(d)}개</b></div>'
    f'<div class="stat pink{long_cls}"><span>종합 점수 1위</span><b>{html.escape(t1["title"])}</b>'
    f'<em>{t1["total"]:.1f}점</em></div>'
    f'<div class="stat mint"><span>중도 포기율(하차율) 중간값</span><b>{d["drop_rate"].median() * 100:.1f}%</b></div>'
    f'<div class="stat blue"><span>평점 평균 (100점 만점)</span><b>{d["averageScore"].mean():.1f}</b></div>'
    '</div>', unsafe_allow_html=True)
if kind == "전체":
    n_seq = int(top["has_prequel"].sum())
    if n_seq >= 3:
        st.info(f"지금 Top {len(top)} 중 **{n_seq}편이 후속작**이에요. 후속작은 1기를 끝까지 본 팬들이 주로 보니까 중도 포기율이 낮고 "
                "평점이 높게 나와서, '전체'로 보면 유리해요. 새로 나온 작품끼리만 보려면 왼쪽에서 **신작만**을 골라 주세요.")
if n_before > len(d):
    st.caption(f"평점이나 하차율을 계산할 수 없는 작품 {n_before - len(d)}개는 제외했어요.")
n_airing = int((d["status"] == "RELEASING").sum())
if n_airing:
    st.caption(f"※ 이 중 {n_airing}개는 아직 방영 중이라 숫자가 계속 변해요.")

with st.expander("용어 설명 (눌러서 펼치기)"):
    st.markdown("""
- **인기 (담은 사람 수)**: 이 작품을 '내 목록'에 담은 사람의 수예요(AniList 이용자 기준). 많을수록 많이 알려진 작품이에요.
- **평점**: AniList 이용자들이 이 작품에 준 점수(100점 만점)의 평균이에요.
- **하차율 (중도 포기율)**: 보기 시작한 사람 중에서 **중간에 그만둔 사람의 비율**이에요. 낮을수록 끝까지 보게 되는 작품이에요.
- **즐겨찾기 비율**: 이 작품을 목록에 담은 사람 중에서 **즐겨찾기(하트)까지 누른 사람의 비율**이에요. 높을수록 '꼭 간직하고 싶다'는 사람이 많은 작품이에요.
- **종합 점수**: 위 네 가지를 같은 눈금(0~1)으로 맞춰서, 왼쪽에서 정한 중요도대로 섞은 100점 만점 점수예요.
- **숨은 명작**: 평점은 상위 25%인데 인기는 하위 50%인 작품이에요. 아직 덜 알려졌지만 평가가 좋은 작품이에요.
""")

# 모든 분기에서 같은 눈금을 쓰기 위한 전체 범위 (분기를 바꿔도 축이 안 변하게)
g_drop_max = df["drop_rate"].max() * 100 * 1.05
g_pop_range = [np.log10(df["popularity"].min() * 0.8), np.log10(df["popularity"].max() * 1.2)]
g_score_range = [df["averageScore"].min() - 3, df["averageScore"].max() + 3]

tab_c, tab_p = st.tabs(["작품 비교 — 어떤 작품이 최고인가", "산업 구조 — 어떤 원작·제작사가 강한가"])

with tab_c:
    # ---------------------------------------------------------------- 차트 1: 종합 점수 Top 10 (답)
    left, right = st.columns(2)
    with left, st.container(border=True):
        st.subheader("① 종합 점수 Top 10 — 이번 질문의 답")
        fig = go.Figure()
        ts = top.sort_values("total", ascending=False)
        wsum = sum(w.values())
        for name, col, key, color in PARTS:
            fig.add_bar(y=ts["label"], x=ts[col] * w[key] / wsum * 100, name=name, orientation="h",
                        marker=dict(color=color, line=dict(width=0)), customdata=ts["title"],
                        hovertemplate="%{customdata}<br>" + name + " 기여: %{x:.1f}점<extra></extra>")
        fig.add_scatter(x=ts["total"] + 1, y=ts["label"], mode="text", text=ts["total"].round(1).astype(str),
                        textposition="middle right", showlegend=False, hoverinfo="skip", cliponaxis=False)
        fig.update_layout(barmode="stack")
        fig.update_xaxes(range=[0, 118], tickvals=[0, 25, 50, 75, 100], title="종합 점수 (0~100)")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(style(fig, 460), width="stretch")
        st.caption("막대 전체 길이가 종합 점수(100점 만점)예요. 색 조각은 네 가지 지표가 점수에 얼마나 보탬이 됐는지 보여 줘요. "
                   "점수는 지금 비교 중인 작품들 사이에서의 상대 평가예요.")

    # ---------------------------------------------------------------- 차트 2: 안정성
    with right, st.container(border=True):
        st.subheader("② 중요도를 바꿔도 Top 10에 남는 작품")
        scenarios = {"지금 슬라이더 설정": w, **SCENARIOS}
        d["hits"] = 0
        d["which"] = ""
        for name, sw in scenarios.items():
            in_top = d.index.isin(d.assign(s=total_score(d, sw)).nlargest(TOP_N, "s").index)
            d["hits"] += in_top.astype(int)
            d.loc[in_top, "which"] += name + ", "
        n_sc = len(scenarios)
        stable = d[d["hits"] > 0].sort_values(["hits", "total"], ascending=False).head(15)
        fig = go.Figure(go.Bar(
            y=stable["label"], x=stable["hits"], orientation="h",
            marker=dict(color=[ACCENT if h == n_sc else GRAY for h in stable["hits"]], line=dict(width=0)),
            text=stable["hits"], textposition="outside", cliponaxis=False,
            customdata=np.stack([stable["title"], stable["which"].str.rstrip(", ")], axis=-1),
            hovertemplate="%{customdata[0]}<br>Top 10에 든 횟수: %{x}/" + str(n_sc) + "<br>%{customdata[1]}<extra></extra>"))
        fig.update_xaxes(range=[0, n_sc + 0.5], dtick=1, title=f"Top 10에 든 횟수 (최대 {n_sc})")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(style(fig, 460), width="stretch")
        st.caption(f"중요도를 {n_sc}가지로 바꿔 가며(지금 설정, 균등, 끝까지 보기·평점·즐겨찾기·인기 중심) Top 10을 다시 뽑았어요. "
                   f"분홍 막대는 {n_sc}번 모두 Top 10에 든 작품, 즉 **누가 어떤 기준으로 봐도 볼만한 애니**예요. "
                   "마우스를 올리면 어떤 설정에서 들었는지 보여요.")

    # ---------------------------------------------------------------- 차트 3: 산점도
    left, right = st.columns(2)
    with left, st.container(border=True):
        st.subheader("③ 평점 × 인기 — 숨은 명작 찾기")
        q_score, med_pop = d["averageScore"].quantile(0.75), d["popularity"].median()
        gem = (d["averageScore"] >= q_score) & (d["popularity"] <= med_pop)
        fig = go.Figure()
        x0, x1 = 10 ** g_pop_range[0], med_pop
        y0, y1 = q_score, g_score_range[1]
        fig.add_scatter(x=[x0, x1, x1, x0, x0], y=[y0, y0, y1, y1, y0], mode="lines", fill="toself",
                        line=dict(width=0), fillcolor="rgba(76,141,246,0.10)", hoverinfo="skip",
                        name="숨은 명작 구역 (평점 상위 25% · 인기 하위 50%)")
        for mask, name, color in [(~gem, "그 외 작품", GRAY), (gem, "숨은 명작", ACCENT)]:
            sub = d[mask]
            fig.add_scatter(x=sub["popularity"], y=sub["averageScore"], mode="markers", name=name,
                            marker=dict(size=11, color=color, line=dict(width=1.5, color="#1E40AF" if name == "숨은 명작" else "white")),
                            customdata=np.stack([sub["title"], sub["drop_rate"] * 100], axis=-1),
                            hovertemplate="%{customdata[0]}<br>평점 %{y}<br>담은 사람 %{x:,}명<br>"
                                          "중도 포기율 %{customdata[1]:.1f}%<extra></extra>")
        fig.update_xaxes(type="log", range=g_pop_range, title="인기 — 담은 사람 수 (로그 눈금)",
                         tickvals=[300, 1000, 3000, 10000, 30000, 100000],
                         ticktext=["300", "1천", "3천", "1만", "3만", "10만"], minor=dict(showgrid=False))
        fig.update_yaxes(range=g_score_range, title="평점 (100점 만점)")
        st.plotly_chart(style(fig, 460), width="stretch")
        gem_names = "、".join(d.loc[gem, "label"].tolist()[:5]) or "없음"
        st.caption("세로는 평점, 가로는 인기(담은 사람 수)예요. 인기 차이가 너무 커서 가로 눈금은 1천, 1만처럼 10배씩 벌어져요. "
                   f"분홍 점이 '숨은 명작'(평점 상위 25%인데 인기는 하위 50%) 후보예요: {gem_names}")

    # ---------------------------------------------------------------- 차트 4: 하차율
    with right, st.container(border=True):
        st.subheader("④ 작품별 중도 포기율 (하차율)")
        dd = d.sort_values("drop_rate")
        in_top = dd["label"].isin(top_labels)
        fig = go.Figure()
        for mask, name, color in [(in_top, "종합 점수 Top 10", ACCENT), (~in_top, "그 외", GRAY)]:
            sub = dd[mask]
            fig.add_bar(y=sub["label"], x=sub["drop_rate"] * 100, orientation="h", name=name,
                        marker=dict(color=color, line=dict(width=0)), customdata=sub["title"],
                        hovertemplate="%{customdata}<br>중도 포기율 %{x:.1f}%<extra></extra>")
        fig.update_xaxes(range=[0, g_drop_max], title="중도 포기율 (%) — 낮을수록 좋아요")
        fig.update_yaxes(autorange="reversed", categoryorder="array", categoryarray=dd["label"])
        st.plotly_chart(style(fig, max(460, 24 * len(dd) + 120)), width="stretch")
        st.caption("보기 시작한 사람(보는 중·완료·그만둠·보류) 중 중간에 그만둔 사람의 비율이에요. "
                   "막대는 0%에서 시작하고 어느 분기를 골라도 같은 눈금이에요. 분홍 막대는 종합 점수 Top 10 작품이에요.")

# ---------------------------------------------------------------- 산업 구조: 원작 유형 / 제작사
# 작품 하나가 아니라 '어떤 원작·제작사의 작품이 좋은 반응을 얻는가'를 본다.
with tab_p:
    st.info("앞 탭이 작품 하나하나를 비교했다면, 여기서는 **원작 종류와 제작사**로 묶어서 어떤 구조의 작품이 좋은 반응을 얻는지 봐요. "
            "점수는 왼쪽 중요도 설정을 그대로 따르고, 분기마다 따로 계산한 뒤 1\\~4분기 전체를 묶었어요(오래된 분기가 유리해지는 것을 막기 위해서예요).")

    pool = df.copy()
    if kind == "신작만":
        pool = pool[~pool["has_prequel"]]
    elif kind == "후속작만":
        pool = pool[pool["has_prequel"]]
    if genres:
        pool = pool[pool["genres"].apply(lambda gs: any(g in gs.split("|") for g in genres))]
    pool = pool[pool["popularity"] >= min_pop].dropna(subset=["averageScore", "drop_rate"])
    scored = []
    for _, g in pool.groupby("quarter"):
        if len(g) >= 3:
            g = add_normalized(g)
            g["score_all"] = total_score(g, w)
            scored.append(g)
    pool = pd.concat(scored) if scored else pool.iloc[0:0]
    pool["origin"] = pool["source"].map(SOURCE_KO).fillna("기타")
    pool["studio"] = pool["studio"].map(STUDIO_KO).fillna(pool["studio"]).fillna("미상")

    def median_bar(frame, group_col, min_n=1, top=12):
        """그룹별 종합 점수 중간값 막대 (이름에 작품 수 표시)."""
        g = frame.groupby(group_col)["score_all"].agg(["median", "count"]).reset_index()
        g = g[g["count"] >= min_n].sort_values("median", ascending=False).head(top)
        if g.empty:
            return None
        names = g[group_col] + " (" + g["count"].astype(str) + "편)"
        fig = go.Figure(go.Bar(y=names, x=g["median"], orientation="h",
                               marker=dict(color=ACCENT, line=dict(width=0)),
                               text=g["median"].round(1), textposition="outside", cliponaxis=False,
                               hovertemplate="%{y}<br>종합 점수 중간값 %{x:.1f}<extra></extra>"))
        fig.update_xaxes(range=[0, 118], tickvals=[0, 25, 50, 75, 100], title="종합 점수 중간값 (0~100)")
        fig.update_yaxes(autorange="reversed")
        return fig

    left, right = st.columns(2)
    with left, st.container(border=True):
        st.subheader("⑤ 원작 종류별 종합 점수")
        fig = median_bar(pool, "origin")
        if fig is None:
            st.caption("조건에 맞는 작품이 적어서 그릴 수 없어요.")
        else:
            st.plotly_chart(style(fig, 360), width="stretch")
            st.caption("1\\~4분기 작품을 원작 종류로 묶어 종합 점수의 **중간값**을 비교했어요. 괄호 안은 작품 수예요. "
                       "기타는 AniList가 따로 분류한 원작(게임·웹소설·캐릭터 프랜차이즈 등)이 섞여 있어요. 작품 수가 적은 그룹(오리지널·기타)은 한두 작품에 크게 흔들려요.")
    with right, st.container(border=True):
        st.subheader("⑥ 제작사별 종합 점수 (3편 이상)")
        fig = median_bar(pool, "studio", min_n=3)
        if fig is None:
            st.caption("조건에 맞는 작품 중 3편 이상 만든 제작사가 없어요. 필터를 조금 풀어 주세요.")
        else:
            st.plotly_chart(style(fig, 360), width="stretch")
            st.caption("1\\~4분기에 3편 이상 만든 제작사만, 종합 점수 **중간값**이 높은 순으로 보여 줘요. "
                       "작품 수가 3\\~6편이라 '그 제작사의 실력'이라기보다 참고용 숫자예요.")

    # 플랫폼: 작품 하나가 여러 플랫폼에 올라올 수 있어서, 플랫폼마다 그 플랫폼에 올라온 작품을 따로 센다.
    stream_path = DATA_DIR / "streaming.csv"
    with st.container(border=True):
        st.subheader("⑦ 스트리밍 플랫폼별 종합 점수 (3편 이상)")
        if not stream_path.exists():
            st.caption("플랫폼 데이터(data/streaming.csv)가 없어요. collect_streaming.py를 실행해 주세요.")
        else:
            stream = pd.read_csv(stream_path)
            stream = stream[stream["site"] != "Laftel"]  # AniList에는 라프텔이 거의 없어서, 라프텔은 공지에서 직접 맞춘 목록으로 대신한다.
            laftel_path = DATA_DIR / "laftel.csv"
            if laftel_path.exists():
                stream = pd.concat([stream, pd.read_csv(laftel_path)[["id"]].assign(site="Laftel")], ignore_index=True)
            ps = pool.merge(stream, on="id")
            ps["platform"] = ps["site"].map(PLATFORM_KO).fillna(ps["site"])
            fig = median_bar(ps, "platform", min_n=3)
            if fig is None:
                st.caption("조건에 맞는 작품 중 3편 이상 올라온 플랫폼이 없어요. 필터를 조금 풀어 주세요.")
            else:
                st.plotly_chart(style(fig, 400), width="stretch")
                st.caption("한 작품이 여러 플랫폼에 올라오기도 해서 같은 작품이 여러 막대에 들어가요. "
                           "**라프텔**은 라프텔 고객센터의 「2026년 1~4분기 공개 작품 안내」 공지에 적힌 제목을 직접 옮겨 AniList 작품과 맞춘 목록이에요(공지에 없어도 라프텔에서 직접 확인한 작품은 더했어요). "
                           "나머지 플랫폼은 AniList에 달린 스트리밍 링크 기준이라 나라별 서비스 여부를 구분하지 못해서, 한국에서 실제로 볼 수 있는지와는 다를 수 있어요. "
                           "크런치롤·유튜브처럼 작품 대부분에 걸린 플랫폼은 전체 평균과 비슷하게 나와요. "
                           "플랫폼이 작품을 좋게 만든다기보다, 어떤 작품이 어디에 올라오는지의 구조를 보는 참고용이에요.")

# ---------------------------------------------------------------- 표 + 집계 기준
with st.expander("작품별 숫자 표 보기"):
    show = d.sort_values("total", ascending=False)[
        ["title", "title_native", "total", "averageScore", "popularity", "drop_rate", "fav_rate", "has_prequel",
         "studio", "status"]]
    show["studio"] = show["studio"].map(STUDIO_KO).fillna(show["studio"])
    show = show.rename(columns={"title": "제목", "title_native": "일본어 원제", "total": "종합점수",
                                "averageScore": "평점", "popularity": "인기(담은 사람 수)",
                                "drop_rate": "중도 포기율(하차율)", "fav_rate": "즐겨찾기 비율", "has_prequel": "후속작", "studio": "스튜디오",
                                "status": "방영상태"})
    st.dataframe(show.round(3), hide_index=True, width="stretch")

with st.expander("점수는 어떻게 계산했나요? (집계 기준과 한계)"):
    st.markdown(f"""
**데이터**: 애니 이용자 커뮤니티 AniList의 공개 API에서 2026년 1~4분기 TV 애니(성인물 분류 제외)를 **{collected_at}에 한 번** 수집했어요. 앱은 이 CSV 파일만 읽어요.
한국어 제목은 TMDB(The Movie Database) API에서 가져왔고, 없는 작품은 영문 제목으로 표시해요.
TMDB의 제목은 시리즈 단위라 부제(예: 'OO편')가 빠진 경우가 있어요.

*This product uses the TMDB API but is not endorsed or certified by TMDB.* ([themoviedb.org](https://www.themoviedb.org))

**네 가지 지표**
- 평점: AniList 이용자들이 이 작품에 준 점수(100점 만점)의 평균
- 인기: 이 작품을 '내 목록'에 담은 사람의 수. 작품마다 격차가 커서 로그를 씌워 계산
- 중도 포기율(하차율): 중간에 그만둔 사람 ÷ (보는 중 + 완료 + 그만둠 + 보류). 볼 예정인 사람은 제외
- 즐겨찾기 비율: 즐겨찾기(하트)를 누른 사람 ÷ 목록에 담은 사람

**종합 점수**: 네 지표를 0~1로 맞춘 뒤(중도 포기율은 낮을수록 높은 점수가 되게 뒤집어서) 중요도(가중치)대로 섞고 100점 만점으로 바꿨어요.
지금 조건으로 걸러진 작품들끼리 비교하는 상대 점수예요. 담은 사람이 최소 기준보다 적은 작품과, 평점·중도 포기율을 계산할 수 없는 작품은 뺐어요.

**원작 종류·제작사 비교(⑤⑥)**: 1~4분기 작품을 묶어 비교하되, 종합 점수는 분기 안에서 따로 계산한 뒤 합쳤어요. 중요도 설정은 그대로 따라요.

**한계**
- 소비자와 제작·투자자의 입장을 비교하려 했지만, 작품별 매출과 제작비가 공개되어 있지 않아서 하지 못했어요. 이 대시보드는 시청자 반응만 다뤄요.
- 원작 종류·제작사 비교는 작품 수가 적은 그룹이 있어서 참고용이에요.
- 수집한 날의 스냅샷이라, 방영 중인 작품은 숫자가 계속 변해요.
- 후속작은 전작을 좋아한 사람만 봐서 평점이 높게 나오는 편향이 있어요. 그래서 신작/후속작 필터를 뒀어요.
- 스트리밍 플랫폼(⑦) 중 라프텔은 라프텔 공지(1~4분기 공개 작품 안내)에 올라온 신작·동시 방영 작품 기준이에요. 공지에 없는 작품(이전 분기부터 서비스 중이거나 나중에 추가된 작품)은 빠질 수 있어요(블리치처럼 공지에는 없지만 서비스 중인 작품은 직접 확인해 더했어요). 또한 제목을 한국어 제목으로 맞추는 과정에서 일부는 직접 확인해 고쳤어요.
- 라프텔 외 플랫폼은 AniList에 달린 링크 기준이라 나라별 서비스 여부를 알 수 없어요. 한국에서 볼 수 있는 곳과는 다를 수 있어요.
- AniList는 해외 이용자 비중이 커서 한국 시청자의 취향과 다를 수 있어요.
- 분기끼리는 방영 후 지난 시간이 달라서 숫자를 직접 비교하기 어려워요. 순위는 항상 한 분기 안에서만 매겨요.
- 중도 포기율과 평점은 함께 움직이는 경향이 있어서(평점이 높은 작품은 포기율도 낮아요), 중요도를 바꿔도 결과가 크게 안 바뀔 수 있어요.
""")
