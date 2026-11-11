# 2026 분기별 제일 볼만한 애니는?

산업데이터시각화 2026-2 개인 프로젝트. AniList 공개 데이터로 TV 애니의 "볼만함"을 평점·인기·하차율·즐겨찾기 비율로 비교하는 Streamlit 대시보드.

**질문**: 분기별로 TV 애니 중 제일 볼만한 작품은 무엇인가? (기본은 지난 분기인 2026년 3분기, 7~9월. 1·2·4분기도 선택 가능, 수집 일시 2026-11-11 기준)

## 구조
- `collect.py` : AniList GraphQL API에서 한 번 수집해 `data/anime.csv`로 저장 (앱은 API를 직접 호출하지 않음)
- `app.py` : `data/` 의 CSV만 읽어 보여 주는 Streamlit 앱
- `fetch_ko_titles_tmdb.py` : TMDB API(무료 키 필요, 환경변수 `TMDB_API_KEY`)에서 한국어 제목을 받아 `data/title_ko_tmdb.csv`로 저장
- `data/title_ko.csv` : (id, title_ko) 직접 고친 제목. 있으면 가장 먼저 표시 (그다음 TMDB, 영문, 일본어 원제 순)
- `data/raw/` : 수집 중간 산출물 (git 제외)

## 데이터
- 출처: AniList GraphQL API (https://graphql.anilist.co), 비상업적 교육 용도
- 수집 일시는 CSV의 수집 일시 컬럼과 앱 화면에 표시

## 실행
```bash
pip install -r requirements.txt
python collect.py        # 데이터 수집 (한 번만)
streamlit run app.py     # 로컬 실행
```

한국어 제목 출처: TMDB. *This product uses the TMDB API but is not endorsed or certified by TMDB.*
