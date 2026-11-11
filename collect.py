"""AniList에서 분기별 TV 애니 데이터를 한 번 수집해 data/anime.csv로 저장한다.

실행: python collect.py
앱(app.py)은 이 CSV만 읽는다. (발표 중 API 장애에 대비)
"""
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

URL = "https://graphql.anilist.co"

# 수집할 분기: (연도, 시즌). 첫 번째가 이번 분기, 나머지는 비교용 이전 분기
QUARTERS = [(2026, "FALL"), (2026, "SUMMER"), (2026, "SPRING"), (2026, "WINTER")]

PER_PAGE = 50
WAIT_BETWEEN_REQUESTS = 3  # 초. 분당 30회 제한 -> 최소 2초 간격이 필요하므로 여유를 둔다
MAX_RETRIES = 5

DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"

QUERY = """
query ($page: Int, $perPage: Int, $season: MediaSeason, $year: Int) {
  Page(page: $page, perPage: $perPage) {
    pageInfo { hasNextPage }
    media(season: $season, seasonYear: $year, type: ANIME, format: TV,
          isAdult: false, sort: POPULARITY_DESC) {
      id
      title { native english romaji }
      averageScore
      meanScore
      popularity
      favourites
      episodes
      status
      genres
      source
      studios(isMain: true) { nodes { name } }
      relations { edges { relationType } }
      coverImage { large }
      stats { statusDistribution { status amount } }
    }
  }
}
"""


def post_with_retry(variables):
    """API 호출. 429(너무 많은 요청)가 오면 기다렸다가 다시 시도한다."""
    for attempt in range(1, MAX_RETRIES + 1):
        res = requests.post(URL, json={"query": QUERY, "variables": variables}, timeout=30)
        if res.status_code == 429:
            wait = int(res.headers.get("Retry-After", 60)) + 1
            print(f"  429 응답: {wait}초 기다린 뒤 재시도 ({attempt}/{MAX_RETRIES})")
            time.sleep(wait)
            continue
        res.raise_for_status()  # 그 밖의 오류는 바로 멈춘다
        return res.json()["data"]["Page"]
    raise RuntimeError("재시도 횟수를 넘겼습니다. 잠시 후 다시 실행하세요.")


def fetch_quarter(year, season):
    """한 분기의 모든 페이지를 받아 작품 리스트로 돌려준다."""
    items, page = [], 1
    while True:
        print(f"{year} {season} - {page}쪽 요청")
        data = post_with_retry(
            {"page": page, "perPage": PER_PAGE, "season": season, "year": year}
        )
        items += data["media"]
        if not data["pageInfo"]["hasNextPage"]:
            return items
        page += 1
        time.sleep(WAIT_BETWEEN_REQUESTS)


def flatten(m, year, season, collected_at):
    """API 응답 1건을 CSV 한 줄(딕셔너리)로 펼친다."""
    dist = {d["status"]: d["amount"] for d in m["stats"]["statusDistribution"]}
    relation_types = [e["relationType"] for e in m["relations"]["edges"]]
    studios = m["studios"]["nodes"]
    return {
        "id": m["id"],
        "quarter": f"{year} {season}",
        "title_native": m["title"]["native"],
        "title_english": m["title"]["english"],
        "title_romaji": m["title"]["romaji"],  # 표시용으로는 안 쓰고 보관만 한다
        "averageScore": m["averageScore"],
        "meanScore": m["meanScore"],
        "popularity": m["popularity"],
        "favourites": m["favourites"],
        "episodes": m["episodes"],
        "status": m["status"],
        "genres": "|".join(m["genres"]),
        "studio": studios[0]["name"] if studios else None,
        "source": m["source"],
        "has_prequel": "PREQUEL" in relation_types,  # True면 후속작
        "cover_image": m["coverImage"]["large"],
        "n_current": dist.get("CURRENT", 0),
        "n_completed": dist.get("COMPLETED", 0),
        "n_dropped": dist.get("DROPPED", 0),
        "n_paused": dist.get("PAUSED", 0),
        "n_planning": dist.get("PLANNING", 0),
        "n_repeating": dist.get("REPEATING", 0),
        "collected_at": collected_at,
    }


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    kst = timezone(timedelta(hours=9))
    collected_at = datetime.now(kst).strftime("%Y-%m-%d %H:%M (KST)")

    rows = []
    for i, (year, season) in enumerate(QUARTERS):
        if i > 0:
            time.sleep(WAIT_BETWEEN_REQUESTS)
        items = fetch_quarter(year, season)
        # 원본 응답도 저장해 두면 나중에 필드를 더 뽑고 싶을 때 다시 수집하지 않아도 된다
        raw_path = RAW_DIR / f"{year}_{season}.json"
        raw_path.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
        rows += [flatten(m, year, season, collected_at) for m in items]
        print(f"  -> {len(items)}개 작품")

    df = pd.DataFrame(rows)
    # utf-8-sig: 엑셀로 열어도 한글/일본어가 깨지지 않게 한다
    df.to_csv(DATA_DIR / "anime.csv", index=False, encoding="utf-8-sig")
    print(f"\n저장 완료: data/anime.csv ({len(df)}행, 수집 일시 {collected_at})")
    print(df.groupby("quarter").size())


if __name__ == "__main__":
    main()
