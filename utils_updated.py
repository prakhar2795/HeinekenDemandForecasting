import pandas as pd
import numpy as np
from datetime import datetime


# --------------------------------------------------------------------------
# small helpers for loading and cleaning the demand/promotions data
# nothing fancy here, just keeping things consistent across notebooks
# --------------------------------------------------------------------------

PROMOTION_DURATION_DAYS = 7  # all promos in this dataset run exactly 7 days


def parse_time(s):
    # using strptime because the date format in the csv isn't always pandas-friendly
    return datetime.strptime(s, "%Y-%m-%d").date()


def read_demand(path):
    df = pd.read_csv(path)
    # vectorised parse is faster but strptime is safer with edge cases in this file
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    df = df.set_index("date")
    df.index = pd.DatetimeIndex(df.index)
    return df


def read_promotions(path):
    df = pd.read_csv(path, index_col=0)
    df["promotion_date"] = pd.to_datetime(df["promotion_date"], format="%Y-%m-%d")
    df = df.set_index("promotion_date")
    df.index = pd.DatetimeIndex(df.index)
    return df


def clean(ts: pd.Series) -> pd.Series:
    """bfill first, then fall back to group mean for anything left at the tail."""
    return ts.bfill().fillna(ts.mean())


def clean_demand_per_group(demand: pd.DataFrame) -> pd.DataFrame:
    """
    Fill missing demand values independently for each (supermarket, SKU) pair.

    Doing this per group matters — Desperados in Jumbo runs at roughly 2-3x the
    volume of Heineken 0.0 in Dirk, so a single global fill would introduce noise.
    Strategy: bfill within group, group mean as a safety net for tail NaNs.

    Modifies a copy, doesn't touch the original dataframe.
    """
    demand = demand.copy()
    for su in demand.supermarket.unique():
        for sku in demand.sku.unique():
            mask = (demand.sku == sku) & (demand.supermarket == su)
            demand.loc[mask, "demand"] = clean(demand.loc[mask, "demand"])
    return demand


def merge(demand: pd.DataFrame, promotions: pd.DataFrame) -> pd.DataFrame:
    # outer join so we keep all demand rows even when there's no matching promo
    # promotion column gets False wherever there's no match
    promotions = promotions.rename_axis("date").assign(promotion=True)
    merged = demand.merge(
        promotions,
        on=["supermarket", "sku", "date"],
        how="outer",
    )
    merged["promotion"] = merged["promotion"].fillna(False)
    return merged


def extend_promotions_days(promotions, n_days=PROMOTION_DURATION_DAYS):
    """
    Each promotion row has a start date. This expands it to n_days rows,
    one per day of the promotion window.

    Builds a list and concatenates once at the end — avoids the O(n²) issue
    with repeatedly appending to a dataframe.
    """
    n_promotions = len(promotions)
    promotion_id = np.arange(n_promotions)

    all_chunks = [promotions.copy().assign(promotion_id=promotion_id)]

    for days_to_add in range(1, n_days):
        chunk = promotions.copy().assign(promotion_id=promotion_id)
        chunk.index += pd.Timedelta(days_to_add, "d")
        all_chunks.append(chunk)

    return pd.concat(all_chunks)


def aggregate_to_weekly(df):
    """
    Roll daily data up to weekly.
    demand → sum (total units sold that week)
    promotion → any (was there a promo active at any point during the week?)
    """
    grouped = df.groupby(["sku", "supermarket"])
    weekly = grouped.apply(
        lambda x: x.resample("W").agg({"demand": "sum", "promotion": "any"}),
        include_groups=False,
    )
    return weekly.reset_index().set_index("date")
