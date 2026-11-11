"""TMDB에서 작품을 직접 검색해 어떤 이름으로 올라 있는지 확인하는 도구.

사용법 (터미널에서 한 줄로, 키는 환경변수로만 전달):
  TMDB_API_KEY="발급받은 키" python3 tmdb_lookup.py
  TMDB_API_KEY="발급받은 키" python3 tmdb_lookup.py "검색어1" "검색어2"

검색어를 주지 않으면 확인이 필요한 4개 작품(클레바테스, 책벌레의 하극상, 치킨파이터, 니아 리스톤)을 찾는다.
각 검색 결과마다 한국어 이름(검색 결과의 name), 원제, 첫 방영일, 한국어 번역(translations)을 보여 준다.
"""
import os
import sys
import time

import requests

KEY = os.environ.get("TMDB_API_KEY", "").strip()
if not KEY:
    sys.exit("환경변수 TMDB_API_KEY가 비어 있어요. 사용법처럼 한 줄로 입력해 주세요.")

session = requests.Session()
base = {"language": "ko-KR"}
if len(KEY) > 40:
    session.headers["Authorization"] = f"Bearer {KEY}"
else:
    base["api_key"] = KEY

DEFAULT = ["클레바테스", "Clevatess", "책벌레의 하극상", "本好きの下剋上", "치킨파이터", "ニワトリ・ファイター",
           "Rooster Fighter", "흉란영애", "凶乱令嬢ニア・リストン", "Nia Liston"]
queries = sys.argv[1:] or DEFAULT


def get(path, **extra):
    r = session.get(f"https://api.themoviedb.org/3{path}", params={**base, **extra}, timeout=30)
    if r.status_code == 401:
        sys.exit("TMDB 키가 거부됐어요(401). 키를 다시 확인해 주세요.")
    r.raise_for_status()
    time.sleep(0.1)
    return r.json()


for q in queries:
    print(f"\n=== 검색어: {q}")
    results = get("/search/tv", query=q)["results"]
    if not results:
        print("  (결과 없음)")
    for res in results[:4]:
        print(f"  id {res['id']} | 이름: {res['name']} | 원제: {res['original_name']} | "
              f"첫방영 {res.get('first_air_date') or '?'} | 언어 {res.get('original_language')}")
        ko = [t["data"].get("name") for t in get(f"/tv/{res['id']}/translations")["translations"]
              if t["iso_639_1"] == "ko" and t["data"].get("name")]
        if ko:
            print(f"      한국어 번역: {ko[0]}")
