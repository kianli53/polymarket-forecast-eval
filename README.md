# DIRECTION 1: Forecasting against the market
Post-cutoff forecasts. Score one language model on 20 to 30 resolved Polymarket, Manifold, or Metaculus questions that closed after its training cutoff, against the market price or Metaculus community forecast at a fixed point before each resolved.

## Question
Can GPT-5.6 Luna, with no web access, forecast real-world events that resolved after its training cutoff as accurately as Polymarket’s own prices, and does it beat trivial baselines? More broadly, does an LLM’s forecasting skill on post-cutoff events approach that of a prediction market?

## Methodology
**MODEL**
GPT-5.6 Luna, cutoff Feb 16, 2026 (https://developers.openai.com/api/docs/models/gpt-5.6-luna). Same prompt, no search or tools, and a new chat for every question.

**PROMPT**
You are a forecaster. Today's date is {ref_time date}.

Question: {question}

Resolution rules: {description}

Estimate the probability that this question resolves YES. Use only what you already know; you have no ability to look anything up. Even if you are unsure, give your best numeric estimate.
Reply on a SINGLE line in exactly this format, with nothing else:
PROBABILITY: <a number between 0 and 1> | REASON: <one sentence>

**DATA**
Resolved Yes/No Polymarket markets that closed at least 14 days after the cutoff, filtered by a volume threshold and clean resolution, then sampled randomly with a fixed seed. Text descriptions were checked for text that revealed the outcome. Forecasted using the market's last price 7 days before close.

**METRIC**
The Brier score was used, a metric used to measure the accuracy of probabilistic predictions.
Brier score: $mean((forecast - outcome)^2)$, where a score of 0 means a perfect forecast and a score of 1 means the worst possible forecast.

**BASELINES AND CONTROLS**
(a) the market price, the strong baseline
(b) always 50%
(c) always the base rate of Yes in my sample
Controls show whether the model has any skill at all, while the market shows how the model compares to the crowd.

## First Experiment
On 30 questions, the model scored Brier 0.2383, the market 0.1525, always-50% 0.2500, and the base-rate control 0.2322. The model minus market difference was +0.0859 (95% confidence interval from -0.0135 to +0.1882). The data is consistent with no difference, but the point estimate favors the market and most of the interval does too. n=30 is too small a sample size to say more.

The model barely beat the 50% control (0.2500) and did not beat the base-rate control (0.2322), so I found no evidence of useful forecasting skill on this sample.

**Worst misses**
+ Arsenal win the EPL: model 0.28, market 0.855, resolved Yes.
+ Graham Platner (Maine): model 0.18, market 0.957, resolved Yes.
+ Liverpool top 4: model 0.95, market 0.445, resolved No. The single worst miss.
The model knows nothing after Feb 16, 2026, while the market price on the forecast date reflects all the news up to that date. Since the market had between a week and about 7.5 months of news the model never saw, these misses may mostly reflect missing information rather than poor reasoning.

On this sample, GPT-5.6 Luna showed no clear skill beyond a constant guess and was worse than the market, largely because the market knew about events after the cutoff.

## Next Steps
**RESULTS THAT WOULD CHANGE CONCLUSION**
+ If the model had done worse than the 50% control, my conclusion would be that it has little forecasting skill.
+ If the model had beat the market with an interval excluding zero, I'd suspect leakage.
+ If the model had matched the market on questions it could have seen but fell behind on post-cutoff questions, I'd suspect memorization.

**WITH ANOTHER WEEK**
+ Run the leakage test using the same pipeline on questions resolved *before* the cutoff, comparing the gap to the market on each set.
+ Sort the questions by how long after the cutoff the forecast date falls, and compare the model vs market gap for early vs late questions.
+ Expand the sample size to 100+ questions, so a difference can be detected.
+ Try a second model, and sample each question multiple times to see how much an answer varies.
+ Devise graphs and plots for the results and data.
+ Current limitations are the small sample, one prompt, one forecast point, volume-based selection of markets, and the possibility that descriptions or question wordings hint at outcomes.

**What I'd want to work on in the future**
World models are still a relatively new concept to me, but I'm interested in learning more, especially methods in evaluating them as I've done through this small project. In the future however, I'd like to leverage my knowledge to work on building said models instead of simply testing them.

AI tools were used to help write data collection and scoring scripts, which were reviewed and ran personally. Choosing the question, filters, and controls were personal decisions.