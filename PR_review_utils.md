# Pull Request Review: `utils.py`

## 1. Docstring for `clean_demand_per_group`

```python
def clean_demand_per_group(demand: pd.DataFrame) -> pd.DataFrame:
    """
    Impute missing demand values for each (supermarket, SKU) group independently.

    For each unique combination of supermarket and SKU, missing demand values are
    filled using backward fill (next valid observation carried backwards), with any
    remaining NaNs (e.g. at the tail of the series) replaced by the group mean.

    Imputing per group is important to avoid cross-contamination between products
    or stores that may have very different demand levels.

    Parameters
    ----------
    demand : pd.DataFrame
        DataFrame with columns ['demand', 'sku', 'supermarket'] and a DatetimeIndex.
        The 'demand' column may contain NaN values.

    Returns
    -------
    pd.DataFrame
        The input DataFrame with NaN values in the 'demand' column filled in-place
        for each (supermarket, SKU) combination.

    Examples
    --------
    >>> d = read_demand("demand.csv")
    >>> d_clean = clean_demand_per_group(d)
    >>> d_clean.demand.isnull().sum()
    0
    """
```

---

## 2. Code Review Comments on `utils.py`

### 🔴 Critical (must fix before production)

**[C1] `extend_promotions_days` uses deprecated `DataFrame.append()`**
```python
# Current (broken on pandas >= 2.0)
extended_promotions = extended_promotions.append(additional_promotion_days)

# Fix: use pd.concat
additional_days_list = [extended_promotions]
for days_to_add in range(1, n_days):
    ...
    additional_days_list.append(additional_promotion_days)
extended_promotions = pd.concat(additional_days_list)
```
`DataFrame.append()` was deprecated in pandas 1.4 and removed in pandas 2.0. This will raise `AttributeError` on any modern environment. Using `pd.concat` on a list outside the loop is also more efficient (avoids O(n²) copies).

---

**[C2] `clean_demand_per_group` mutates its input**
```python
# Current — modifies caller's dataframe in place
demand.loc[mask, "demand"] = clean(...)

# Fix — work on a copy or document the mutation explicitly
def clean_demand_per_group(demand: pd.DataFrame) -> pd.DataFrame:
    demand = demand.copy()  # avoid surprising the caller
    ...
```
In-place mutation of function arguments is a production anti-pattern: it violates the principle of least surprise, makes pipelines hard to debug, and causes silent errors if the caller reuses the original dataframe.

---

### 🟡 Important (should fix)

**[I1] `merge` uses an outer join but no test guards against rows lost from demand**
The outer join preserves all promotion dates even if they have no corresponding demand row. This is likely intentional, but should be documented — and the function should raise or warn if the merged result has *more* rows than demand (which would indicate unexpected promotion dates outside the demand date range).

**[I2] `aggregate_to_weekly` uses `"max"` for promotion aggregation without explanation**
`"max"` on a boolean series is equivalent to `"any"` — correct, but non-obvious. A comment or using `.any()` explicitly would improve readability:
```python
# Current
{"demand": "sum", "promotion": "max"}
# Clearer
{"demand": "sum", "promotion": "any"}
```

**[I3] `parse_time` is called per-row via `.apply()` — slow for large files**
```python
# Current — O(n) Python function calls
df.date.apply(parse_time)

# Fix — vectorised, ~10–50x faster
pd.to_datetime(df.date, format="%Y-%m-%d")
```

**[I4] `aggregate_to_weekly` uses deprecated `include_groups` pattern**
In newer pandas, calling `.apply()` on a `GroupBy` without `include_groups=False` emits a `FutureWarning`. Add `include_groups=False` to suppress.

---

### 🟢 Minor (nice to have)

**[M1] No module-level `__all__` export list** — makes it unclear which functions are public API vs internal helpers.

**[M2] `read_demand` and `read_promotions` accept `path` as a positional string but have no type hint** — adding `path: str` or `path: Path` would improve IDE support.

**[M3] Magic number `7` in caller code** — `extend_promotions_days(promotions, 7)` appears in multiple places. Define `PROMOTION_DURATION_DAYS = 7` as a named constant.

---

## 3. Additional: Bug in `merge` / Unexpected Behavior

**Unexpected behavior in `test_merge_has_promotions`:**

```python
def test_merge_has_promotions(demand_path, promotion_path):
    d = read_demand(demand_path)
    p = read_promotions(promotion_path)
    m = merge(d, p)
    assert m.promotion.sum() == len(p)   # ← This assertion is fragile
```

The `merge` function receives the *raw* promotions (single-day rows, 15 rows total). The test asserts that `promotion.sum() == 15`. However, `extend_promotions_days` is not called in the test — so this test only validates the single-day case. In actual usage, `merge` is always called with *extended* promotions (7 days each = 105 rows). The test should either:
1. Call `extend_promotions_days` before `merge` and assert `sum == len(p) * 7`, or
2. Keep the single-day test but add a separate test for the extended case.

Additionally, if two promotion periods for the same SKU×store overlap (which can happen in the data), `promotion.sum()` will be less than `len(p) * 7`. The test and function are both silent about this edge case.
