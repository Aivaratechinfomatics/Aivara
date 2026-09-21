"""
analytics/domains/commerce.py — Specialized e-commerce and retail analytics.

Computes:
1. Average Order Value (AOV) and Basket Size (Units/Order).
2. Customer metrics (Repeat purchase rate, Customer Pareto).
3. Product performance (Top revenue items, sales velocity, discount impact).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
import pandas as pd


@dataclass
class CommerceAnalyticsResult:
    total_revenue: float
    total_orders: int
    total_units: int
    unique_customers: int
    aov: float
    basket_size: float
    repeat_customer_rate: float
    avg_discount_rate: float
    top_products_table: pd.DataFrame
    customer_spend_table: pd.DataFrame
    channel_breakdown_table: pd.DataFrame | None


def compute_commerce_analytics(
    df: pd.DataFrame,
    order_col: str | None = None,
    customer_col: str | None = None,
    product_col: str | None = None,
    revenue_col: str | None = None,
    qty_col: str | None = None,
    discount_col: str | None = None,
    channel_col: str | None = None,
) -> CommerceAnalyticsResult:
    """Computes specialized retail and e-commerce KPI scorecard and aggregations."""
    # Find columns dynamically if not explicitly specified
    cols = df.columns
    if not order_col:
        order_col = next((c for c in cols if re.search(r"(order[_\s]?id|invoice|receipt|trans)", c, re.I)), None)
    if not customer_col:
        customer_col = next((c for c in cols if re.search(r"(cust|client|account|buyer|user[_\s]?id)", c, re.I)), None)
    if not product_col:
        product_col = next((c for c in cols if re.search(r"(product|item|sku|title)", c, re.I)), None)
    if not revenue_col:
        revenue_col = next((c for c in cols if re.search(r"(sales|revenue|amount|total|price)", c, re.I) and pd.api.types.is_numeric_dtype(df[c])), None)
    if not qty_col:
        qty_col = next((c for c in cols if re.search(r"(qty|quantity|units|volume)", c, re.I) and pd.api.types.is_numeric_dtype(df[c])), None)
    if not discount_col:
        discount_col = next((c for c in cols if re.search(r"(disc|rebate|markdown)", c, re.I) and pd.api.types.is_numeric_dtype(df[c])), None)
    if not channel_col:
        channel_col = next((c for c in cols if re.search(r"(channel|store|region|market|source)", c, re.I)), None)

    # 1. Orders and Totals
    n_rows = len(df)
    total_orders = df[order_col].dropna().nunique() if order_col else n_rows
    total_orders = max(1, total_orders)

    total_rev = float(df[revenue_col].dropna().sum()) if revenue_col else 0.0
    total_units = int(df[qty_col].dropna().sum()) if qty_col else n_rows
    aov = total_rev / total_orders
    basket_size = total_units / total_orders

    # 2. Customer metrics
    unique_cust = df[customer_col].dropna().nunique() if customer_col else 0
    repeat_rate = 0.0
    customer_spend_table = pd.DataFrame()

    if customer_col and revenue_col:
        cust_grouped = (
            df.groupby(customer_col)
            .agg(
                total_spend=(revenue_col, "sum"),
                order_count=(order_col if order_col else revenue_col, "nunique" if order_col else "count"),
            )
            .reset_index()
            .sort_values(by="total_spend", ascending=False)
        )
        repeats = (cust_grouped["order_count"] > 1).sum()
        repeat_rate = float(repeats / max(1, len(cust_grouped)))
        customer_spend_table = cust_grouped.head(20)

    # 3. Product metrics
    top_products_table = pd.DataFrame()
    if product_col and revenue_col:
        prod_agg = {revenue_col: "sum"}
        if qty_col:
            prod_agg[qty_col] = "sum"
        prod_grouped = (
            df.groupby(product_col)
            .agg(prod_agg)
            .reset_index()
            .sort_values(by=revenue_col, ascending=False)
        )
        prod_grouped["share_pct"] = (prod_grouped[revenue_col] / max(1.0, total_rev)) * 100.0
        top_products_table = prod_grouped.head(20)

    # 4. Discounts
    avg_discount = float(df[discount_col].dropna().mean()) if discount_col else 0.0

    # 5. Channel Breakdown
    channel_table = None
    if channel_col and revenue_col:
        channel_table = (
            df.groupby(channel_col)
            .agg(
                revenue=(revenue_col, "sum"),
                orders=(order_col if order_col else revenue_col, "nunique" if order_col else "count"),
            )
            .reset_index()
            .sort_values(by="revenue", ascending=False)
        )

    return CommerceAnalyticsResult(
        total_revenue=total_rev,
        total_orders=total_orders,
        total_units=total_units,
        unique_customers=unique_cust,
        aov=round(aov, 2),
        basket_size=round(basket_size, 2),
        repeat_customer_rate=round(repeat_rate, 3),
        avg_discount_rate=round(avg_discount, 3),
        top_products_table=top_products_table,
        customer_spend_table=customer_spend_table,
        channel_breakdown_table=channel_table,
    )
