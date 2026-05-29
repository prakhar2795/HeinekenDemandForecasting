"""
This module contains helper functions for the EDA and modelling exercises.
Feel free to use them to get you started more quickly.
"""
import pandas as pd
import numpy as np
from datetime import datetime


def parse_time(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def read_demand(path):
    df = pd.read_csv(path)
    df = df.assign(date=lambda df: df.date.apply(parse_time))
    df = df.set_index("date")
    df.index = pd.DatetimeIndex(df.index)
    return df


def read_promotions(path):
    df = pd.read_csv(path, index_col=0)
    df = df.assign(promotion_date=lambda df: df.promotion_date.apply(parse_time))
    df = df.set_index("promotion_date")
    df.index = pd.DatetimeIndex(df.index)
    return df


def clean(ts: pd.Series) -> pd.Series:
    """Replace missing values using backward fill, falling back to series mean."""
    return ts.bfill().fillna(ts.mean())


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
    sus = demand.supermarket.unique()
    skus = demand.sku.unique()
    for su in sus:
        for sku in skus:
            mask = (demand.sku == sku) & (demand.supermarket == su)
            demand.loc[mask, "demand"] = clean(demand.loc[mask, "demand"])
    return demand


def merge(demand: pd.DataFrame, promotions: pd.DataFrame) -> pd.DataFrame:
    promotions = promotions.rename_axis("date").assign(promotion=True)
    demand = demand.merge(
        promotions,
        on=["supermarket", "sku", "date"],
        how="outer",
    )
    demand = demand.assign(promotion=lambda df: df.promotion.fillna(False))
    return demand


def extend_promotions_days(promotions, n_days):
    """
    Extends the promotions to have multiple rows for a specific number of days.

    The input promotions is assumed be specified with a single row with a starting date.
    The output extends the input promotions with multiple days, one row for each day
    of the promotion.
    """
    n_promotions = len(promotions)
    initial_promotions = promotions.copy()
    promotion_id = np.arange(n_promotions)
    extended_promotions = promotions.copy().assign(promotion_id=promotion_id)

    additional_days_list = [extended_promotions]
    for days_to_add in range(1, n_days):
        additional_promotion_days = initial_promotions.copy().assign(promotion_id=promotion_id)
        additional_promotion_days.index += pd.Timedelta(days_to_add, "d")
        additional_days_list.append(additional_promotion_days)

    extended_promotions = pd.concat(additional_days_list)
    return extended_promotions


def aggregate_to_weekly(df):
    grouped = df.groupby(["sku", "supermarket"])
    weekly = grouped.apply(
        lambda df: df.resample("W").agg({"demand": "sum", "promotion": "max"}),
        include_groups=False,
    )
    weekly = weekly.reset_index().set_index("date")
    return weekly
