# Heineken Demand Forecasting

Predicting weekly beer demand 8 weeks ahead, per SKU × supermarket combination.

The repo covers the full workflow — EDA, data cleaning, feature engineering, model comparison, and a utility module that the notebooks share.

---

## Background

The Demand Planning team needs 8-week-ahead forecasts for 3 SKUs across 3 supermarket chains. Without reliable forecasts, the business ends up either holding too much stock (write-offs) or too little (stock-outs). Both are expensive.

---

## What's in here

```
EDA_exercise_solution.ipynb       data exploration and cleaning
Modelling_exercise_solution.ipynb feature engineering, model comparison, evaluation
utils_updated.py                  shared functions used by both notebooks
PR_review_utils.md                code review notes on utils.py
eda_fig1_data_quality.png         data quality summary chart
eda_fig2_timeseries.png           weekly demand by SKU over time
eda_fig3_seasonality_promo.png    seasonality and promo lift analysis
model_fig1_comparison.png         model comparison results
```

---

## The data

Two input files (not included — proprietary):
- `demand.csv` — daily demand per SKU × supermarket, Jan 2019 – Dec 2021
- `promotions.csv` — promotion start dates (each promo runs 7 days)

3 SKUs: Heineken Regular, Heineken 0.0, Desperados  
3 stores: Albert Heijn, Jumbo, Dirk  
~156 weeks per series after aggregating to weekly

---

## How to run

Both notebooks import from `utils_updated.py`, so that file needs to be in the same directory as the CSVs.

```python
from utils_updated import read_demand, read_promotions, extend_promotions_days, merge, clean_demand_per_group, aggregate_to_weekly
```

Run `EDA_exercise_solution.ipynb` first to understand the data, then `Modelling_exercise_solution.ipynb` for the forecast models.

---

## Key findings

**Data quality**
- ~11% of daily demand values are missing — imputed per SKU×store using backward fill with group mean as fallback
- Outliers (~0.5–1%) align with promotion periods — kept and modelled explicitly

**What drives demand**
- Promotions move Desperados demand by ~+14%, Heineken 0.0 and Regular by 5–6%
- Monthly seasonality is mild — lag features matter more than calendar features for beer
- Desperados is the most volatile series (CV ~0.29), Heineken Regular the most stable (CV ~0.13)

**Model results**

| Model | MAPE | vs Naive |
|---|---|---|
| Naive (8-week avg) | ~19% | — |
| Ridge Regression | **~13%** | −6 pp |
| Random Forest | ~14% | −5 pp |
| Gradient Boosting | ~14% | −5 pp |
| LightGBM | ~14% | −5 pp |

Ridge wins, which makes sense in hindsight — once the lag structure is built, the demand signal is largely linear. A 13% MAPE on Desperados (~587 units/week) translates to roughly ±76 units per week per store, which is workable for setting safety stock buffers.

---

## utils_updated.py

| Function | What it does |
|---|---|
| `read_demand(path)` | Load demand CSV, parse dates, set DatetimeIndex |
| `read_promotions(path)` | Load promotions CSV |
| `clean_demand_per_group(df)` | Impute missing demand per SKU×store (bfill + mean fallback) |
| `extend_promotions_days(df, n)` | Expand single-day promo rows to n-day windows |
| `merge(demand, promos)` | Outer join demand and promotions |
| `aggregate_to_weekly(df)` | Resample to weekly (demand=sum, promotion=any) |

Code review notes in `PR_review_utils.md` — covers the bugs that were in the original version and what was fixed.

---

## Author
Prakhar Acharya
