"""라프텔 공지의 작품 제목(data/laftel_notice.txt)을 AniList 작품(data/anime.csv)과 맞춰 data/laftel.csv로 저장한다.

실행: python match_laftel.py
- 같은 분기 작품끼리 한국어 제목이 비슷한 쌍을 찾는다. (시즌·기수 표기와 기호는 빼고 비교)
- 비슷함이 기준 이상이면 자동으로 맞추고, 애매한 것은 화면에 따로 보여 준다.
- 자동으로 못 맞춘 것·잘못 맞춘 것은 data/laftel_manual.csv(laftel_title,id)에 적어 고친다.
  id를 비워 두면 '대시보드에 없는 작품'으로 본다. (예: 극장판·어린이용·재방영 작품)
"""
import re
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

DATA_DIR = Path("data")
AUTO = 0.80     # 이 이상이면 자동으로 맞춘다
REVIEW = 0.55   # 이 이상 AUTO 미만이면 '확인 필요'로 보여 준다


def norm(t, keep_paren=False):
    """비교용으로 제목을 다듬는다: 앞 표기, 시즌·기수, 기호, 공백을 뺀다.
    keep_paren=True이면 괄호 안 글자는 남긴다. (예: 'BLACK TORCH (블랙 토치)')"""
    t = re.sub(r"^\[(선독점|독점)\]\s*", "", t)
    t = re.sub(r"^\((자막|더빙)\)\s*", "", t)
    if not keep_paren:
        t = re.sub(r"\(.*?\)|【.*?】", "", t)
    t = re.sub(r"(제?\s*\d+\s*기|시즌\s*\d+|season\s*\d+|\d+(st|nd|rd|th)\s*season|part\s*\d+|[ⅠⅡⅢⅣ]+)", "", t, flags=re.I)
    t = re.sub(r"[^0-9a-zA-Z가-힣]", "", t)
    return t.lower()


def load_titles():
    df = pd.read_csv(DATA_DIR / "anime.csv")

    def ko_map(name):
        p = DATA_DIR / name
        if not p.exists():
            return {}
        k = pd.read_csv(p).dropna(subset=["id", "title_ko"])
        return dict(zip(k["id"], k["title_ko"]))

    df["title"] = (df["id"].map(ko_map("title_ko.csv")).fillna(df["id"].map(ko_map("title_ko_tmdb.csv")))
                   .fillna(df["title_english"]).fillna(df["title_native"]))
    return df[["id", "quarter", "title"]]


def read_notice():
    rows, quarter = [], None
    for line in (DATA_DIR / "laftel_notice.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("# "):
            continue
        line = re.sub(r"\s{2,}#.*$", "", line)  # 줄 끝에 공백 두 칸 이상 + '#'로 붙인 메모는 뺀다
        if line.startswith("## "):
            quarter = line[3:].strip()
            continue
        m = re.match(r"^\[(선독점|독점)\]", line)
        rows.append({"quarter": quarter, "laftel_title": line, "exclusive": m.group(1) if m else ""})
    return pd.DataFrame(rows)


def score(a, b):
    if not a or not b:
        return 0.0
    r = SequenceMatcher(None, a, b).ratio()
    if len(a) >= 4 and len(b) >= 4 and (a in b or b in a):  # 한쪽이 다른 쪽에 통째로 들어 있으면 가깝다고 본다
        r = max(r, 0.9)
    return r


def main():
    anime, notice = load_titles(), read_notice()
    anime["key"] = anime["title"].map(norm)
    manual_path = DATA_DIR / "laftel_manual.csv"
    manual = pd.read_csv(manual_path) if manual_path.exists() else pd.DataFrame(columns=["laftel_title", "id"])
    manual_map = dict(zip(manual["laftel_title"], manual["id"]))

    matched, review, none = [], [], []
    for _, n in notice.iterrows():
        if n["laftel_title"] in manual_map:
            mid = manual_map[n["laftel_title"]]
            if pd.notna(mid):
                matched.append({"id": int(mid), "laftel_title": n["laftel_title"], "exclusive": n["exclusive"], "how": "manual"})
            continue
        keys = {norm(n["laftel_title"]), norm(n["laftel_title"], keep_paren=True)}
        cand = anime[anime["quarter"] == n["quarter"]].copy()
        cand["s"] = cand["key"].map(lambda k: max(score(key, k) for key in keys))
        best = cand.sort_values("s", ascending=False).iloc[0] if len(cand) else None
        if best is not None and best["s"] >= AUTO:
            matched.append({"id": int(best["id"]), "laftel_title": n["laftel_title"], "exclusive": n["exclusive"], "how": f"auto {best['s']:.2f}"})
        elif best is not None and best["s"] >= REVIEW:
            review.append((n["quarter"], n["laftel_title"], best["title"], int(best["id"]), best["s"]))
        else:
            other = anime.copy()
            other["s"] = other["key"].map(lambda k: max(score(key, k) for key in keys))
            ob = other.sort_values("s", ascending=False).iloc[0]
            if ob["s"] >= AUTO:  # 분기가 다르게 분류된 작품. 맞춰 두되 화면에 알려 준다.
                matched.append({"id": int(ob["id"]), "laftel_title": n["laftel_title"], "exclusive": n["exclusive"], "how": f"other-quarter {ob['s']:.2f}"})
                print(f"  (다른 분기에서 찾음) {n['quarter']} {n['laftel_title'][:30]} -> {ob['quarter']} {ob['title'][:30]}")
            else:
                none.append((n["quarter"], n["laftel_title"]))

    # AniList는 2쿨 작품을 분기마다 따로 올리기도 한다. 같은 제목의 다른 분기 작품도 라프텔에 있는 것으로 본다.
    # (제목이 같을 때만. 시즌·기수 표기는 비교에서 빠지므로 '같은 시리즈'를 뜻한다.)
    found = {r["id"] for r in matched}
    by_key = anime.groupby("key")["id"].apply(list).to_dict()
    for r in list(matched):
        key = anime.loc[anime["id"] == r["id"], "key"].iloc[0]
        for sid in by_key.get(key, []):
            if key and sid not in found:
                matched.append({"id": int(sid), "laftel_title": r["laftel_title"], "exclusive": r["exclusive"], "how": "same-title"})
                found.add(sid)

    out = pd.DataFrame(matched)
    # 같은 작품이 두 번 올라온 경우(자막/더빙, 분기 걸침)는 한 번만 센다. 독점 표기는 있는 쪽을 남긴다.
    out["ex_rank"] = out["exclusive"].map({"선독점": 2, "독점": 1}).fillna(0)
    out = out.sort_values("ex_rank", ascending=False).drop_duplicates("id").drop(columns="ex_rank").sort_values("id")
    out.to_csv(DATA_DIR / "laftel.csv", index=False, encoding="utf-8-sig")

    print(f"공지 {len(notice)}개 중 자동·수동으로 맞춘 것 {len(matched)}개 → laftel.csv {len(out)}편 (대시보드 {len(anime)}편 중)")
    print(f"\n[확인 필요 {len(review)}개] (분기 / 라프텔 제목 / 가장 비슷한 대시보드 작품 / id / 비슷함)")
    for r in review:
        print(f"  {r[0]} | {r[1][:40]} | {r[2][:40]} | {r[3]} | {r[4]:.2f}")
    print(f"\n[대시보드에서 못 찾음 {len(none)}개] (극장판·어린이용·재방영이거나, 수집 때 빠진 작품)")
    for q, t in none:
        print(f"  {q} | {t[:60]}")


if __name__ == "__main__":
    main()
