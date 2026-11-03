"""
ask_model.py
Builds the forecasting prompt for each row of questions.csv and records the
model's probability in forecasts.csv. It resumes where it left off if you stop.

TWO MODES
  manual (default, no API key):  python ask_model.py
      Prints one prompt at a time. Paste it into a FRESH chat (search/memory off),
      paste the one-line reply back here, press Enter. Repeat.
  api (automatic):               python ask_model.py api
      Calls an OpenAI-compatible chat API for every question.
      Needs:  pip install openai
      And environment variables:
        API_KEY     your key
        MODEL_NAME  the model's API name (from the provider's docs)
        BASE_URL    only if the provider isn't OpenAI itself (optional)

Output columns: id, model_prob, raw_response
"""
import csv
import os
import re
import sys
from datetime import datetime

PROMPT = """You are a forecaster. Today's date is {date}.

Question: {question}

Resolution rules: {description}

Estimate the probability that this question resolves YES. Use only what you already know; you have no ability to look anything up. Even if you are unsure, give your best numeric estimate.

Reply on a SINGLE line in exactly this format, with nothing else:
PROBABILITY: <a number between 0 and 1> | REASON: <one sentence>"""

PROB_RE = re.compile(r"PROBABILITY:\s*([0-9]*\.?[0-9]+)", re.IGNORECASE)


def build_prompt(row):
    date = datetime.fromisoformat(row["ref_time"]).date().isoformat()
    desc = (row["description"] or "(none given)")[:1500]
    return PROMPT.format(date=date, question=row["question"], description=desc)


def parse_prob(text):
    m = PROB_RE.search(text)
    if not m:
        return None
    p = float(m.group(1))
    return p if 0.0 <= p <= 1.0 else None


def load_done():
    if not os.path.exists("forecasts.csv"):
        return set()
    with open("forecasts.csv", newline="", encoding="utf-8") as f:
        return {r["id"] for r in csv.DictReader(f)}


def append_row(qid, prob, raw):
    new_file = not os.path.exists("forecasts.csv")
    with open("forecasts.csv", "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["id", "model_prob", "raw_response"])
        w.writerow([qid, prob, raw.replace("\n", " ").strip()])


def ask_api(client, model, prompt):
    kwargs = dict(model=model, messages=[{"role": "user", "content": prompt}])
    try:
        resp = client.chat.completions.create(temperature=0, **kwargs)
    except Exception:
        # some models don't accept a temperature setting
        resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "manual"
    with open("questions.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    done = load_done()
    todo = [r for r in rows if r["id"] not in done]
    print(f"{len(rows)} questions, {len(done)} already done, {len(todo)} to go.\n")

    client = model = None
    if mode == "api":
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["API_KEY"],
                        base_url=os.environ.get("BASE_URL") or None)
        model = os.environ["MODEL_NAME"]

    for n, row in enumerate(todo, 1):
        prompt = build_prompt(row)
        if mode == "api":
            raw = ask_api(client, model, prompt)
            prob = parse_prob(raw)
            print(f"[{n}/{len(todo)}] {row['question'][:60]} -> {prob}")
            if prob is None:
                print(f"   could not parse a probability; raw reply: {raw[:100]!r} (skipped)")
                continue
        else:
            print("=" * 70)
            print(f"Question {n} of {len(todo)}. Paste EVERYTHING below into a NEW chat:\n")
            print(prompt)
            print("\n" + "-" * 70)
            while True:
                raw = input("Paste the model's one-line reply (or type q to quit): ").strip()
                if raw.lower() == "q":
                    print("Stopped. Run again later to continue where you left off.")
                    return
                prob = parse_prob(raw)
                if prob is not None:
                    break
                print("Couldn't find 'PROBABILITY: <0 to 1>' in that. Try again.")
        append_row(row["id"], prob, raw)

    print("\nDone. forecasts.csv is ready; now run: python score.py")


if __name__ == "__main__":
    main()