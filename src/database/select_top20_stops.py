from pathlib import Path
import pandas as pd
from difflib import SequenceMatcher

BASE_DIR = Path(__file__).resolve().parent

# Input (your Herzliya-only file)
IN_FILE = BASE_DIR / "herzliya_stops_clean.csv"

# Output: only the final 20 stops (no mapping, no scores)
OUT_SELECTED = BASE_DIR / "herzliya_top20_selected.csv"

# 20 hub targets (keywords). Adjust freely.
HUB_TARGETS = [
    ("Herzliya Train Station", ["תחנת רכבת הרצליה", "ת. רכבת הרצליה", "רכבת הרצליה"]),
    ("Herzliya Interchange", ["מחלף הרצליה", "צומת הרצליה", "מחלף"]),
    ("Herzliya Central Station", ["תחנה מרכזית הרצליה", "הורדה", "תחנה מרכזית"]),
    ("Herzliya Marina", ["מרינה הרצליה", "מרינה", "השונית", "יורדי ים"]),
    ("Arena Mall", ["קניון ארנה", "ארנה"]),
    ("Seven Stars Mall", ["קניון שבעת הכוכבים", "שבעת הכוכבים", "7 כוכבים"]),
    ("Sokolov Corridor", ["סוקולוב"]),
    ("Ben Gurion Corridor", ["בן גוריון"]),
    ("Weizman Corridor", ["וייצמן", "ויצמן"]),
    ("HaRav Kook Corridor", ["הרב קוק"]),
    ("Shivat HaKochavim Blvd", ["שדרות שבעת הכוכבים", "שבעת הכוכבים שד"]),
    ("Abba Eban Blvd", ["אבא אבן", "שדרות אבא אבן"]),
    ("Shenkar St", ["אריה שנקר", "שנקר"]),
    ("Alan Turing St", ["אלן טיורינג", "טיורינג"]),
    ("Moshe Dayan", ["משה דיין"]),
    ("Jabotinsky", ["ז'בוטינסקי", "זבוטינסקי"]),
    ("Pinsker", ["פינסקר"]),
    ("Arlozorov", ["ארלוזורוב"]),
    ("Magen David", ["מגן דוד"]),
    ("South Anchor", ["מנחם בגין", "יד התשעה", "הדר"]),
]


def norm(s: str) -> str:
    if pd.isna(s):
        return ""
    return str(s).strip().lower()


def similarity(a: str, b: str) -> float:
    # 0..1
    return SequenceMatcher(None, a, b).ratio()


def best_match_index(stop_names_norm: list[str], hub_keywords: list[str]) -> int:
    """
    Find the best row index for a hub.
    Uses substring match (strong) + fuzzy similarity fallback.
    Returns index in stop_names_norm, or -1 if empty.
    """
    if not stop_names_norm:
        return -1

    best_idx = -1
    best_score = -1.0

    kws = [norm(k) for k in hub_keywords if norm(k)]
    if not kws:
        return -1

    for i, name in enumerate(stop_names_norm):
        local_best = -1.0
        for kw in kws:
            if kw in name:
                local_best = max(local_best, 1.0)
            else:
                local_best = max(local_best, similarity(name, kw))

        if local_best > best_score:
            best_score = local_best
            best_idx = i

    return best_idx


def main():
    if not IN_FILE.exists():
        raise FileNotFoundError(f"Missing input file: {IN_FILE}")

    df = pd.read_csv(IN_FILE, encoding="utf-8-sig")

    required = {"stop_id", "stop_name", "stop_lat", "stop_lon"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Input is missing columns: {missing}")

    df = df.copy()
    df["stop_name_norm"] = df["stop_name"].map(norm)

    stop_names_norm = df["stop_name_norm"].tolist()

    chosen_ids: list[str] = []
    chosen_set: set[str] = set()

    # Pick one stop per hub, avoiding duplicates
    for _hub_name, keywords in HUB_TARGETS:
        idx = best_match_index(stop_names_norm, keywords)
        if idx == -1:
            continue

        candidate_id = str(df.iloc[idx]["stop_id"])

        # If already taken, pick next best for that hub
        if candidate_id in chosen_set:
            # score all rows for this hub and take the best unused
            kws = [norm(k) for k in keywords if norm(k)]
            scored = []
            for i, row in df.iterrows():
                name = row["stop_name_norm"]
                s = max((1.0 if kw in name else similarity(name, kw)) for kw in kws)
                scored.append((s, i))
            scored.sort(reverse=True, key=lambda x: x[0])

            found = False
            for _s, i in scored:
                sid = str(df.iloc[i]["stop_id"])
                if sid not in chosen_set:
                    candidate_id = sid
                    found = True
                    break
            if not found:
                continue

        chosen_set.add(candidate_id)
        chosen_ids.append(candidate_id)

    # Ensure exactly 20:
    # If fewer than 20, fill by closest to centroid (keeps it “central” / connected-ish)
    if len(chosen_ids) < 20:
        centroid_lat = float(df["stop_lat"].mean())
        centroid_lon = float(df["stop_lon"].mean())
        df["dist2centroid"] = (df["stop_lat"] - centroid_lat) ** 2 + (df["stop_lon"] - centroid_lon) ** 2

        remaining = df[~df["stop_id"].astype(str).isin(chosen_set)].sort_values("dist2centroid")
        need = 20 - len(chosen_ids)
        filler_ids = remaining.head(need)["stop_id"].astype(str).tolist()
        chosen_ids.extend(filler_ids)

    # If more than 20 (rare), trim deterministically by appearance order
    chosen_ids = chosen_ids[:20]

    selected = df[df["stop_id"].astype(str).isin(set(chosen_ids))][
        ["stop_id", "stop_name", "stop_lat", "stop_lon"]
    ].drop_duplicates(subset=["stop_id"]).copy()

    # Keep stable order according to chosen_ids
    order = {sid: i for i, sid in enumerate(chosen_ids)}
    selected["__order"] = selected["stop_id"].astype(str).map(order)
    selected = selected.sort_values("__order").drop(columns=["__order"])

    selected.to_csv(OUT_SELECTED, index=False, encoding="utf-8-sig")
    print(f"Saved: {OUT_SELECTED} (rows={len(selected)})")


if __name__ == "__main__":
    main()