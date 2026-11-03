"""
collect_questions.py
Collect resolved binary (Yes/No) Polymarket questions that closed AFTER a model's
training cutoff, and record the market's price a fixed time before close.

Output: questions.csv with columns
  id, question, description, end_time, ref_time, market_prob, outcome

Usage:  pip install requests
        python collect_questions.py
"""
import csv
import json
import random
import time
from datetime import datetime, timedelta, timezone

import requests

# ---------------- settings ----------------
MODEL_CUTOFF = datetime(2026, 2, 16, tzinfo=timezone.utc)   # GPT-5.6 Luna cutoff (https://developers.openai.com/api/docs/models/gpt-5.6-luna)
MIN_END = MODEL_CUTOFF + timedelta(days=14)    # buffer after the cutoff
MAX_END = datetime.now(timezone.utc) - timedelta(days=3)   # must be fully resolved
DAYS_BEFORE_CLOSE = 7          # fixed forecast point: market price this long before close
MIN_VOLUME = 10_000            # USD; filters out thin, noisy markets
EXTREME = (0.03, 0.97)         # drop markets already near-decided at the forecast point
N_QUESTIONS = 30
SEED = 42                      # fixed seed so your sample is reproducible
MAX_PAGES = 30                 # 100 markets per page
GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
# --------------------------------------------------------


def as_list(x):
    """Gamma sometimes returns lists as JSON-encoded strings."""
    return json.loads(x) if isinstance(x, str) else x


def parse_dt(s):
    if not s:
        return None
    s = s.strip().replace(" ", "T").replace("Z", "+00:00")
    if s.endswith("+00"):
        s += ":00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def fetch_closed_markets():
    rows, offset = [], 0
    for _ in range(MAX_PAGES):
        params = {
            "closed": "true",
            "limit": 100,
            "offset": offset,
            "end_date_min": MIN_END.isoformat(),
            "end_date_max": MAX_END.isoformat(),
            "volume_num_min": MIN_VOLUME,
        }
        r = requests.get(f"{GAMMA}/markets", params=params, timeout=30)
        if r.status_code in (400, 422) and rows:
            # The API rejects very deep offsets; keep what we already have.
            print(f"API stopped paging at offset {offset} (HTTP {r.status_code}); "
                  f"using the {len(rows)} markets fetched so far")
            break
        r.raise_for_status()
        page = r.json()
        if not page:
            break
        rows.extend(page)
        offset += 100
        time.sleep(0.2)
    print(f"Fetched {len(rows)} closed markets")
    return rows


def parse_market(m):
    """Return a clean dict, or None if the market doesn't qualify."""
    try:
        outcomes = [o.lower() for o in as_list(m["outcomes"])]
        prices = [float(p) for p in as_list(m["outcomePrices"])]
        tokens = as_list(m["clobTokenIds"])
    except (KeyError, TypeError, ValueError):
        return None
    if outcomes != ["yes", "no"] or len(prices) != 2 or len(tokens) != 2:
        return None

    # Clean resolution only: one side ~1, the other ~0 (skips 50/50 and disputes)
    if prices[0] > 0.99 and prices[1] < 0.01:
        outcome = 1
    elif prices[1] > 0.99 and prices[0] < 0.01:
        outcome = 0
    else:
        return None

    end = parse_dt(m.get("endDate"))
    closed = parse_dt(m.get("closedTime"))
    end_time = min(t for t in (end, closed) if t) if (end or closed) else None
    if not end_time or not (MIN_END <= end_time <= MAX_END):
        return None

    return {
        "id": m.get("id"),
        "question": m.get("question", "").strip(),
        "description": (m.get("description") or "").strip().replace("\n", " "),
        "end_time": end_time,
        "yes_token": tokens[0],
        "outcome": outcome,
    }


def price_before(token_id, ts_target):
    """Last observed Yes price at or before ts_target (no look-ahead)."""
    params = {
        "market": token_id,
        "startTs": int(ts_target.timestamp()) - 2 * 86400,
        "endTs": int(ts_target.timestamp()),
        "fidelity": 60,  # minutes
    }
    r = requests.get(f"{CLOB}/prices-history", params=params, timeout=30)
    if r.status_code != 200:
        return None
    hist = r.json().get("history", [])
    return float(hist[-1]["p"]) if hist else None


def main():
    markets = [pm for pm in (parse_market(m) for m in fetch_closed_markets()) if pm]
    print(f"{len(markets)} markets pass the Yes/No + clean-resolution + date filters")

    random.seed(SEED)
    random.shuffle(markets)

    kept = []
    for pm in markets:
        ref_time = pm["end_time"] - timedelta(days=DAYS_BEFORE_CLOSE)
        p = price_before(pm["yes_token"], ref_time)
        time.sleep(0.2)
        if p is None or not (EXTREME[0] <= p <= EXTREME[1]):
            continue
        pm.update(ref_time=ref_time, market_prob=p)
        kept.append(pm)
        print(f"  kept {len(kept)}/{N_QUESTIONS}: {pm['question'][:70]}  p={p:.2f}")
        if len(kept) >= N_QUESTIONS:
            break

    with open("questions.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "question", "description", "end_time", "ref_time",
                    "market_prob", "outcome"])
        for pm in kept:
            w.writerow([pm["id"], pm["question"], pm["description"],
                        pm["end_time"].isoformat(), pm["ref_time"].isoformat(),
                        round(pm["market_prob"], 4), pm["outcome"]])
    print(f"Wrote {len(kept)} questions to questions.csv")


if __name__ == "__main__":
    main()
