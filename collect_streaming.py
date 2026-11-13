"""AniList에서 작품별 스트리밍 플랫폼(외부 링크)을 받아 data/streaming.csv로 저장한다.

실행: python collect_streaming.py   (먼저 collect.py로 data/anime.csv가 있어야 한다)
anime.csv의 작품 id만 조회하므로, 평점·인기 같은 기존 숫자는 바뀌지 않는다.
"""
import time
from pathlib import Path

import pandas as pd
import requests

URL = "https://graphql.anilist.co"
DATA_DIR = Path("data")
BATCH = 50
WAIT = 3  # 초. 분당 30회 제한에 여유를 둔다

QUERY = """
query ($ids: [Int]) {
  Page(perPage: 50) {
    media(id_in: $ids, type: ANIME) {
      id
      externalLinks { site type isDisabled }
    }
  }
}
"""

# AniList에 같은 서비스가 다른 이름으로 올라온 경우 하나로 합친다
SITE_FIX = {"Prime Video": "Amazon Prime Video"}


def main():
    ids = pd.read_csv(DATA_DIR / "anime.csv")["id"].tolist()
    rows = []
    for i in range(0, len(ids), BATCH):
        chunk = ids[i:i + BATCH]
        for attempt in range(5):
            res = requests.post(URL, json={"query": QUERY, "variables": {"ids": chunk}}, timeout=30)
            if res.status_code == 429:
                time.sleep(int(res.headers.get("Retry-After", 60)) + 1)
                continue
            res.raise_for_status()
            break
        else:
            raise RuntimeError("재시도 횟수를 넘겼습니다. 잠시 후 다시 실행하세요.")
        for m in res.json()["data"]["Page"]["media"]:
            for e in m["externalLinks"]:
                if e["type"] == "STREAMING" and not e["isDisabled"]:
                    rows.append({"id": m["id"], "site": SITE_FIX.get(e["site"], e["site"])})
        print(f"{min(i + BATCH, len(ids))}/{len(ids)}개 작품 조회")
        time.sleep(WAIT)

    out = pd.DataFrame(rows).drop_duplicates()
    out.to_csv(DATA_DIR / "streaming.csv", index=False, encoding="utf-8-sig")
    print(f"저장 완료: data/streaming.csv ({len(out)}행, 플랫폼이 있는 작품 {out['id'].nunique()}개 / 전체 {len(ids)}개)")
    print(out["site"].value_counts().head(15))


if __name__ == "__main__":
    main()
