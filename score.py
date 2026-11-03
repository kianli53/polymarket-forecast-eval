"""
score.py
Compute Brier scores for your model vs. the market and two simple controls.

Inputs (same folder):
  questions.csv  - made by collect_questions.py (needs: id, question, market_prob, outcome)
  forecasts.csv  - made by you, one row per question, columns: id,model_prob
                   (extra columns such as raw_response are fine and ignored)

Output: prints a summary table and writes results.csv (per-question detail).
Needs only the standard library.
"""
import csv
import random
import statistics

SEED = 42
N_BOOT = 10_000


def brier(forecasts, outcomes):
    """Mean squared error between probabilities and 0/1 outcomes. Lower is better."""
    return statistics.mean((p - o) ** 2 for p, o in zip(forecasts, outcomes))


def read_csv(path, required):
    """Read a CSV tolerantly (handles a BOM and stray spaces in headers) and
    fail with a clear message if a needed column is missing."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [h.strip() for h in (reader.fieldnames or [])]
        missing = [c for c in required if c not in reader.fieldnames]
        if missing:
            raise SystemExit(
                f"{path}: missing column(s) {missing}. The header row I found is "
                f"{reader.fieldnames}. The first line of the file must be exactly: "
                f"{','.join(required)}[,...]"
            )
        return [{k: (v.strip() if isinstance(v, str) else v) for k, v in r.items()}
                for r in reader]


def main():
    questions = {r["id"]: r for r in read_csv("questions.csv", ["id", "market_prob", "outcome"])}
    model = {r["id"]: float(r["model_prob"])
             for r in read_csv("forecasts.csv", ["id", "model_prob"])}

    ids = [i for i in questions if i in model]
    missing = [i for i in questions if i not in model]
    if missing:
        print(f"Warning: {len(missing)} questions have no forecast and are skipped.")
    if not ids:
        raise SystemExit("No overlapping ids between questions.csv and forecasts.csv")

    y = [int(questions[i]["outcome"]) for i in ids]
    p_model = [model[i] for i in ids]
    p_market = [float(questions[i]["market_prob"]) for i in ids]
    base_rate = sum(y) / len(y)  # in-sample, so slightly flattering to this control
    p_half = [0.5] * len(ids)
    p_base = [base_rate] * len(ids)

    rows = [
        ("Model", brier(p_model, y)),
        ("Market (7 days before close)", brier(p_market, y)),
        ("Control: always 50%", brier(p_half, y)),
        (f"Control: always base rate ({base_rate:.2f})", brier(p_base, y)),
    ]
    print(f"\nn = {len(ids)} questions, {sum(y)} resolved Yes\n")
    for name, score in rows:
        print(f"{name:<40} Brier = {score:.4f}")

    # Paired comparison: model minus market, per question (negative = model better)
    diffs = [(pm - o) ** 2 - (pk - o) ** 2 for pm, pk, o in zip(p_model, p_market, y)]
    mean_diff = statistics.mean(diffs)
    random.seed(SEED)
    boots = sorted(
        statistics.mean(random.choices(diffs, k=len(diffs))) for _ in range(N_BOOT)
    )
    lo, hi = boots[int(0.025 * N_BOOT)], boots[int(0.975 * N_BOOT)]
    print(f"\nModel minus market Brier: {mean_diff:+.4f}  (95% bootstrap CI {lo:+.4f} to {hi:+.4f})")
    if lo <= 0 <= hi:
        print("The interval includes 0: with this many questions you cannot tell them apart.")
    elif mean_diff < 0:
        print("The model scored better than the market, and the interval excludes 0.")
    else:
        print("The market scored better than the model, and the interval excludes 0.")

    with open("results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "question", "outcome", "model_prob", "market_prob",
                    "model_sq_err", "market_sq_err"])
        for i, o, pm, pk in zip(ids, y, p_model, p_market):
            w.writerow([i, questions[i]["question"], o, pm, pk,
                        round((pm - o) ** 2, 4), round((pk - o) ** 2, 4)])
    print("\nWrote results.csv")


if __name__ == "__main__":
    main()