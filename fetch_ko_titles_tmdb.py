"""TMDB(The Movie Database) API에서 한국어 제목을 가져와 data/title_ko_tmdb.csv로 저장한다.

준비: https://www.themoviedb.org 가입 -> 설정 -> API 에서 무료 키 발급(비상업적 용도).
키는 코드나 GitHub에 넣지 않고 환경변수로만 전달한다.

  export TMDB_API_KEY="발급받은 키"        # v3 API Key 또는 긴 'API Read Access Token' 둘 다 가능
  python fetch_ko_titles_tmdb.py

동작
 1. 작품마다 일본어 원제(없으면 영문 제목)로 TMDB TV 검색 (language=ko-KR)
 2. 일본 애니메이션만 후보로 하고, 원제가 비슷한지(유사도 0.8 이상) 확인
 3. 신작은 방영 연도가 2025~2026인지도 확인해서 동명이작을 거른다
 4. 한국어 이름이 있으면 저장. 후속작은 영문 제목의 시즌 번호를 붙여 '2기'처럼 만든다
이 데이터는 TMDB 이용 조건에 따라 앱 화면에 "TMDB API 사용" 문구를 표시한다.
"""
import os
import re
import sys
import time
from difflib import SequenceMatcher

import pandas as pd
import requests

KEY = os.environ.get("TMDB_API_KEY", "").strip()
if not KEY:
    sys.exit("환경변수 TMDB_API_KEY가 비어 있어요. 위 사용법처럼 먼저 설정해 주세요.")

session = requests.Session()
params_base = {"language": "ko-KR"}
if len(KEY) > 40:  # 긴 문자열이면 'API Read Access Token' (Bearer 방식)
    session.headers["Authorization"] = f"Bearer {KEY}"
else:  # 짧으면 v3 API Key
    params_base["api_key"] = KEY

df = pd.read_csv("data/anime.csv")
df[["title_native", "title_english"]] = df[["title_native", "title_english"]].fillna("")  # 빈 제목은 빈 문자열로
HANGUL = re.compile("[가-힣]")
SEASON = re.compile(
    r"(第?\s*[0-9０-９一二三四五六七八九十]+\s*(期|シリーズ|クール|部|章))|(\d+(st|nd|rd|th)\s*Season)|"
    r"Season\s*[0-9０-９]+|シーズン\s*[0-9０-９]+|[ⅠⅡⅢⅣⅤ]+|Part\s*\d+|\d+クール|\bSeason\b|\(\d{4}\)")


def clean(title):
    """제목에서 '第3期', 'Season 2' 같은 시즌 표시를 지운다."""
    return re.sub(r"\s+", " ", SEASON.sub(" ", title or "")).strip(" ～-")


def similarity(a, b):
    a, b = clean(a).lower(), clean(b).lower()
    if not a or not b:
        return 0.0
    if len(min(a, b, key=len)) >= 3 and (a.startswith(b) or b.startswith(a)):
        return 0.9
    return SequenceMatcher(None, a, b).ratio()


def season_suffix(english_title):
    m = re.search(r"Season (\d+)", english_title or "") or re.search(r"(\d+)(?:st|nd|rd|th) Season", english_title or "")
    return f" {m.group(1)}기" if m else ""


def search(query):
    r = session.get("https://api.themoviedb.org/3/search/tv", params={**params_base, "query": query}, timeout=30)
    if r.status_code == 401:
        sys.exit("TMDB 키가 거부됐어요(401). 키를 다시 확인해 주세요.")
    r.raise_for_status()
    time.sleep(0.1)
    return r.json()["results"]


rows = []
for a in df.itertuples():
    best = None
    queries = [clean(a.title_native), clean(a.title_english) if isinstance(a.title_english, str) else None]
    for q in dict.fromkeys(x for x in queries if x):
        for res in search(q):
            if res.get("original_language") != "ja" or 16 not in res.get("genre_ids", []):
                continue
            score = max(similarity(a.title_native, res["original_name"]),
                        similarity(a.title_english or "", res["name"]))
            year = int((res.get("first_air_date") or "0000")[:4])
            if not a.has_prequel and year not in (2025, 2026):  # 신작인데 옛날 작품이면 동명이작
                continue
            if score >= 0.8 and (best is None or (score, res["popularity"]) > (best[0], best[1]["popularity"])):
                best = (score, res)
        if best:
            break
    if best:
        base = best[1]["name"]
        if not HANGUL.search(base):  # 검색 결과의 이름이 영어/일본어면 '한국어 번역' 목록에서 한 번 더 찾는다
            tr = session.get(f"https://api.themoviedb.org/3/tv/{best[1]['id']}/translations",
                             params={k: v for k, v in params_base.items() if k == "api_key"}, timeout=30).json()
            time.sleep(0.1)
            ko = [t["data"].get("name") for t in tr.get("translations", [])
                  if t["iso_639_1"] == "ko" and t["data"].get("name")]
            base = ko[0] if ko else base
        if HANGUL.search(base):  # 한국어 이름이 실제로 있을 때만 저장
            rows.append((a.id, base + season_suffix(a.title_english), best[1]["id"], best[1]["original_name"],
                         round(best[0], 2)))

out = pd.DataFrame(rows, columns=["id", "title_ko", "tmdb_id", "tmdb_original_name", "match_score"])
out.to_csv("data/title_ko_tmdb.csv", index=False, encoding="utf-8")

total = df["id"].nunique()
print(f"TMDB 한국어 제목 {len(out)}개 / 전체 {total}개 -> data/title_ko_tmdb.csv")
if os.path.exists("title_review.csv"):
    rv = pd.read_csv("title_review.csv")
    chart = rv[rv["차트에 오름(Top10)"]]
    got = chart["id"].isin(out["id"]).sum()
    print(f"차트에 오르는 작품 {len(chart)}개 중 {got}개 확보")
    print("\n못 찾은 작품(차트에 오르는 것):")
    for _, r in chart[~chart["id"].isin(out["id"])].iterrows():
        print(" -", r["id"], r["영문 제목"])
