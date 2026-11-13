# 2026 분기별 최고의 애니는?

산업데이터시각화 2026-2 개인 프로젝트. AniList 공개 데이터로 TV 애니의 "볼만함"을 평점·인기·하차율·즐겨찾기 비율로 비교하는 Streamlit 대시보드.

**질문**: 분기별로 TV 애니 중 최고의 작품은 무엇인가? (기본은 지난 분기인 2026년 3분기, 7~9월. 1·2·4분기도 선택 가능, 수집 일시 2026-11-11 기준)

## 구조
- `collect.py` : AniList GraphQL API에서 한 번 수집해 `data/anime.csv`로 저장 (앱은 API를 직접 호출하지 않음)
- `app.py` : `data/` 의 CSV만 읽어 보여 주는 Streamlit 앱
- `collect_streaming.py` : AniList에서 작품별 스트리밍 플랫폼(외부 링크)을 받아 `data/streaming.csv`로 저장 (anime.csv의 작품 id만 조회). 산업 구조 탭의 플랫폼 차트(⑦)에 쓰임
- `data/laftel_notice.txt` : 라프텔 고객센터 「2026년 1~4분기 공개 작품 안내」 공지에 적힌 작품 제목을 직접 옮겨 적은 파일 (AniList에는 라프텔 정보가 거의 없어서)
- `match_laftel.py` : 위 제목을 한국어 제목이 비슷한 AniList 작품과 맞춰 `data/laftel.csv`로 저장. 못 맞추거나 잘못 맞춘 것은 `data/laftel_manual.csv`에 직접 적어 고침
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
