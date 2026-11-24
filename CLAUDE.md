# anime-dashboard

산업데이터시각화 2026-2 개인 프로젝트. AniList 공개 데이터로 분기별 TV 애니의 "볼만함"(평점·인기·하차율·즐겨찾기 비율)을 비교하는 Streamlit 대시보드. 자세한 구조와 데이터 출처는 `README.md` 참고.

## 규칙
- 사용자에게는 한국어로 답한다.
- `app.py`는 `data/`의 CSV만 읽는다. 앱에서 API를 직접 호출하지 않는다 (발표 중 API 장애 대비).
- `data/*.csv`는 배포된 앱이 읽는 파일이라 `.gitignore`에 넣지 않는다. `data/raw/`만 제외.
- API 키(`TMDB_API_KEY` 등)는 환경변수로만 쓰고 코드나 GitHub에 넣지 않는다. `.env`는 올리지 않는다.
- 이 저장소는 PUBLIC이다. 올려도 되는 내용인지 확인하고 push한다.

## 두 컴퓨터 동기화 (집 데스크탑 / 학교 맥북)
- 작업 시작: `git pull`
- 작업 끝: 커밋 → `git push`, 아래 "진행 상황"도 갱신
- 가상환경(`venv/`)은 컴퓨터마다 따로 만든다: `pip install -r requirements.txt`

## 진행 상황
- (2026-11-24) GitHub 동기화 설정 완료. 데이터 수집일은 2026-11-11 기준.
- 아직 커밋하지 않은 파일: `.mcp.json`(Supabase MCP 설정), `프레젠테이션1.pptx`(발표 자료, 2.4MB)

## 다음에 할 일
- (작업 끝낼 때 여기에 적기)
