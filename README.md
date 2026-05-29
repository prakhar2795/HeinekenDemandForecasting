# Heineken Demand Forecasting

> **Predicting weekly beer demand 8 weeks in advance — across SKUs, stores, and promotions.**

A end-to-end demand forecasting solution built for Heineken's retail supply chain. This project covers everything from raw data quality assessment to a production-ready predictive model, reducing forecast error by **~6 percentage points** over a naïve baseline and directly addressing stock-outs and write-offs caused by manual planning.

---

## The Business Problem

A senior demand planner's retirement left a gap that no spreadsheet could fill. Without reliable 8-week-ahead forecasts, the team faced:

- **Stock-outs** → lost sales, brand damage
- **Write-offs** → excess inventory, margin erosion

This project replaces gut-feel planning with a data-driven forecasting pipeline covering **3 SKUs × 3 supermarkets**, delivering weekly forecasts calibrated to actual demand behaviour.

---

## Results at a Glance

| Model | MAPE | vs. Naïve Baseline |
|---|---|---|
| Naïve (8-week average) | ~19% | — |
| Ridge Regression | **~13%** | **−6 pp** |
| Random Forest | ~14% | −5 pp |
| Gradient Boosting | ~14% | −5 pp |
| LightGBM | ~14% | −5 pp |

> Ridge Regression wins — confirming the demand signal is largely linear once lag features are properly constructed. All models comfortably beat the baseline.

**Per-series accuracy:**
- Heineken Regular × Albert-Heijn → easiest (~10% MAPE, low volatility)
- Desperados × Jumbo → hardest (~16% MAPE, highest demand variability)

**Practical impact:** A 13% MAPE on Desperados (avg ~587 units/week per store) means ±76 units error — enough precision to set meaningful safety stock buffers and halve excess inventory costs.

---

## Project Structure

```
.
├── EDA_exercise_solution.ipynb        # Exploratory data analysis: quality, patterns, features
├── Modelling_exercise_solution.ipynb  # Model training, evaluation, feature importance
├── utils_updated.py                   # Shared data pipeline functions
├── PR_review_utils.md                 # Code review of utils.py (bugs, fixes, improvements)
├── eda_fig1_data_quality.png          # Data quality summary chart
├── eda_fig2_timeseries.png            # Weekly demand over time per SKU × store
├── eda_fig3_seasonality_promo.png     # Seasonality and promotion lift analysis
├── model_fig1_comparison.png          # Model comparison chart
└── Conclusion_Slide.pptx             # Executive summary slide
```

---

## Data

Two input files (not included in repo — proprietary):

| File | Description |
|---|---|
| `demand.csv` | Daily demand per SKU × supermarket, Jan 2019 – Dec 2021 |
| `promotions.csv` | Promotion start dates (each promotion runs exactly 7 days) |

**Coverage:** 3 SKUs (Heineken Regular, Heineken 0.0, Desperados) × 3 supermarkets (Albert Heijn, Jumbo, Dirk) = 9 time series, ~156 weeks each after aggregation.

---

## Methodology

### 1. Data Quality & Cleaning

- ~11% of daily demand values were missing — imputed **per group** using backward fill with group mean as fallback
- Imputing per group prevents cross-contamination between series with very different demand scales
- Outliers (~0.5–1% of rows, z > 3) retained and explained by promotion activity — modelled explicitly rather than removed

### 2. Feature Engineering

All features are constructed to respect the **8-week forecast horizon** — no look-ahead leakage:

| Feature | Rationale |
|---|---|
| `lag_8w`, `lag_9w`, `lag_10w`, `lag_12w`, `lag_13w` | Most recent demand observable at prediction time |
| `lag_52w` | Same week last year — captures annual patterns |
| `rolling_mean_4/8/13w` | Short, medium, and long demand trend |
| `rolling_std_4/8/13w` | Local demand volatility |
| `promotion` | Known from planning calendar; provides up to +14% lift (Desperados) |
| `month`, `week_of_year`, `quarter` | Seasonality markers |
| `sku_enc`, `sm_enc` | Series identity — allows a single global model to serve all series |

### 3. Model Design

A **single global model** is trained across all 9 series rather than 9 separate per-series models. With only ~150 observations per series, per-series models underfit. Pooling data allows the model to learn shared patterns (e.g. promotion effects that generalise across products).

### 4. Train / Test Split

A **time-based split** is used — the last 8 weeks form the test set, mirroring real deployment. Random splits are explicitly avoided: they allow future data to leak into training, producing optimistically false accuracy metrics.

### 5. Evaluation Metric

**MAPE (Mean Absolute Percentage Error)** is the primary metric. It is scale-free, allowing fair comparison across SKUs with very different demand levels, and directly interpretable by planners: "our forecast is off by X% on average."

---

## Key Findings

| Finding | Implication |
|---|---|
| Desperados has the highest demand volatility (CV = 0.29) | Hardest to forecast; requires the most safety stock buffer |
| Heineken Regular is the most stable (CV = 0.13) | Tight forecasts achievable; minimal buffer needed |
| Promotion drives up to +14% demand lift (Desperados) | Promotion calendar **must** be included in the model — dropping it degrades MAPE |
| Monthly seasonality is mild | Lag features matter more than calendar features for this category |
| Ridge Regression outperforms tree models | The demand signal is largely linear once lag structure is correct |

---

## Utility Functions (`utils_updated.py`)

| Function | What it does |
|---|---|
| `read_demand(path)` | Loads demand CSV, parses dates, sets DatetimeIndex |
| `read_promotions(path)` | Loads promotions CSV, parses dates, sets DatetimeIndex |
| `clean_demand_per_group(demand)` | Imputes missing demand per (SKU, store) group — bfill + mean fallback |
| `extend_promotions_days(promotions, n)` | Expands single-day promotion rows to n-day windows |
| `merge(demand, promotions)` | Outer joins demand and promotions on (date, sku, supermarket) |
| `aggregate_to_weekly(df)` | Resamples daily data to weekly (demand=sum, promotion=any) |

A detailed code review of this module — including critical bugs, performance issues, and minor improvements — is documented in [`PR_review_utils.md`](PR_review_utils.md).

---

## Possible Extensions

| Improvement | Expected Impact | Effort |
|---|---|---|
| National holiday calendar | Medium | Low |
| Weather data (temperature → beer demand) | High | Medium |
| Hyperparameter tuning (Optuna) | Low–Medium | Medium |
| Walk-forward cross-validation | Better confidence bounds | Medium |
| Quantile regression (prediction intervals) | Enables safety stock optimisation | Medium |
| Competitor promotion data | High | High |

---

## Requirements

```
pandas
numpy
scikit-learn
lightgbm
matplotlib
jupyter
```

Install with:
```bash
pip install pandas numpy scikit-learn lightgbm matplotlib jupyter
```

---

## Usage

```python
from utils_updated import read_demand, read_promotions, extend_promotions_days, merge, clean_demand_per_group, aggregate_to_weekly

demand     = read_demand("demand.csv")
promotions = read_promotions("promotions.csv")

cleaned    = clean_demand_per_group(demand.copy())
extended   = extend_promotions_days(promotions, 7)
daily      = merge(cleaned, extended.drop("promotion_id", axis=1))
weekly     = aggregate_to_weekly(daily)
```

Then open `EDA_exercise_solution.ipynb` for analysis or `Modelling_exercise_solution.ipynb` for model training.

---

## Author

**Prakhar Acharya**
