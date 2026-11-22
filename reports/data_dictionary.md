# Data Dictionary: Bluestock MF Analysis

Database: `data/processed/bluestock_mf.db` (SQLite)
Schema definition: `sql/schema.sql`
Loading script: `load_db.py`

## Overview

| Table | Type | Rows | Primary key | Source file |
|---|---|---|---|---|
| dim_date | Dimension | 1,826 | date | Generated (2022-01-01 to 2026-12-31) |
| dim_fund | Dimension | 40 | amfi_code | 01_fund_master.csv |
| fact_nav | Fact | 64,320 | amfi_code, date | 02_nav_history.csv (cleaned) |
| fact_transactions | Fact | 32,778 | transaction_id | 08_investor_transactions.csv (cleaned) |
| fact_performance | Fact | 40 | amfi_code | 07_scheme_performance.csv (cleaned) |
| fact_aum | Fact | 90 | date, fund_house | 03_aum_by_fund_house.csv |

## dim_date

One row per calendar day. Used to join facts by date and to group by month, quarter, or year.

| Column | Type | Definition |
|---|---|---|
| date | TEXT (YYYY-MM-DD) | Calendar date. Primary key. |
| year | INTEGER | Calendar year. |
| month | INTEGER | Month number, 1 to 12. |
| month_name | TEXT | Full month name, for example "January". |
| quarter | INTEGER | Calendar quarter, 1 to 4. |
| year_month | TEXT (YYYY-MM) | Year and month, used for monthly grouping. |
| is_weekend | INTEGER | 1 if Saturday or Sunday, otherwise 0. |

## dim_fund

One row per mutual fund scheme. Source for scheme attributes.

| Column | Type | Definition |
|---|---|---|
| amfi_code | INTEGER | AMFI scheme code, a 6-digit ID that uniquely identifies a scheme. Primary key. |
| fund_house | TEXT | Asset management company that runs the scheme, for example "SBI Mutual Fund". |
| scheme_name | TEXT | Full name of the scheme, including plan and option. |
| category | TEXT | SEBI broad category: Equity, Debt, Hybrid, and so on. |
| sub_category | TEXT | Narrower category, for example "Large Cap" or "Small Cap". |
| plan | TEXT | Regular or Direct. Direct plans have lower expense ratios. |
| launch_date | TEXT | Date the scheme was launched. |
| benchmark | TEXT | Index used to compare the scheme's performance, for example "NIFTY 100 TRI". |
| exit_load_pct | REAL | Fee charged on redemption before a holding period ends, as a percentage. |
| min_sip_amount | REAL | Minimum monthly SIP amount in INR. |
| min_lumpsum_amount | REAL | Minimum one-time investment in INR. |
| fund_manager | TEXT | Name of the fund manager. |
| risk_category | TEXT | Risk level from the fund master, for example Moderate or Very High. |
| sebi_category_code | TEXT | SEBI classification code for the scheme, for example EC01. |

Data note: row 20 of the source file (Nippon India ETF Nifty 50 BeES) has shifted columns. Its values should be checked before analysis.

## fact_nav

Daily Net Asset Value (NAV) per scheme. NAV is the price of one unit of the fund.

| Column | Type | Definition |
|---|---|---|
| amfi_code | INTEGER | Scheme identifier. Foreign key to dim_fund. |
| date | TEXT (YYYY-MM-DD) | Date of the NAV. Foreign key to dim_date. |
| nav | REAL | Net Asset Value in INR per unit. Always greater than 0. |
| nav_filled | INTEGER | 1 if the NAV was carried forward from the previous trading day (weekend or holiday), 0 if it is an actual published NAV. |

Cleaning applied: dates converted to datetime, sorted by scheme and date, duplicates removed, NAV validated as greater than 0, missing days forward-filled.

Data quality: 46,000 raw rows, 0 bad dates, 0 missing NAV, 0 NAV values at or below 0, 0 duplicates. After daily fill: 64,320 rows, of which 18,320 are forward-filled. Date range 2022-01-03 to 2026-05-29.

## fact_transactions

One row per investor transaction. Each row is a single SIP, lumpsum, or redemption.

| Column | Type | Definition |
|---|---|---|
| transaction_id | INTEGER | Surrogate key generated during loading. Primary key. |
| investor_id | TEXT | Anonymised investor identifier. |
| transaction_date | TEXT (YYYY-MM-DD) | Date the transaction was made. Foreign key to dim_date. |
| amfi_code | INTEGER | Scheme the transaction relates to. Foreign key to dim_fund. |
| transaction_type | TEXT | SIP (regular monthly investment), Lumpsum (one-time investment), or Redemption (money withdrawn). |
| amount_inr | REAL | Transaction value in INR. Always greater than 0. |
| state | TEXT | Indian state of the investor. |
| city | TEXT | City of the investor. |
| city_tier | TEXT | City classification, for example T30 (top 30 cities) or B30 (beyond top 30). |
| age_group | TEXT | Investor age band, for example 18-25 or 56+. |
| gender | TEXT | Investor gender as recorded. |
| annual_income_lakh | REAL | Investor's annual income in lakh INR. |
| payment_mode | TEXT | Payment channel, for example UPI or Cheque. |
| kyc_status | TEXT | Know Your Customer status: Verified or Pending. |

Cleaning applied: transaction types standardised (SIP, Lumpsum, Redemption), amounts validated as greater than 0, dates checked, KYC values checked against the allowed list.

Data quality: 32,778 raw rows, 0 duplicates, 0 rows removed. Transaction types: SIP 19,716, Lumpsum 8,095, Redemption 4,967. KYC: Verified 30,146, Pending 2,632. Date range 2024-01-01 to 2025-05-30.

## fact_performance

One row per scheme with performance and risk metrics. Values are as reported in the source file.

| Column | Type | Definition |
|---|---|---|
| amfi_code | INTEGER | Scheme identifier. Primary key and foreign key to dim_fund. |
| return_1yr_pct | REAL | Annualised return over 1 year, as a percentage. |
| return_3yr_pct | REAL | Annualised return over 3 years, as a percentage. |
| return_5yr_pct | REAL | Annualised return over 5 years, as a percentage. |
| benchmark_3yr_pct | REAL | Benchmark index return over 3 years, as a percentage. |
| alpha | REAL | Return above what the benchmark would predict for the risk taken. Positive means the fund outperformed on a risk-adjusted basis. |
| beta | REAL | Sensitivity to market movements. A beta of 1 moves with the market, above 1 moves more, below 1 moves less. |
| sharpe_ratio | REAL | Return per unit of total risk. Higher is better. |
| sortino_ratio | REAL | Like Sharpe, but counts only downside risk. Higher is better. |
| std_dev_ann_pct | REAL | Annualised standard deviation of returns, a measure of volatility, as a percentage. |
| max_drawdown_pct | REAL | Largest peak-to-trough fall in NAV, as a percentage. |
| aum_crore | REAL | Assets under management of the scheme, in crore INR. |
| expense_ratio_pct | REAL | Annual fee charged by the fund as a percentage of assets. Valid range 0.1% to 2.5%. |
| morningstar_rating | INTEGER | Star rating from 1 to 5. |
| risk_grade | TEXT | Risk grade from the performance file, for example Moderate. |

Cleaning applied: return columns checked as numeric, missing values and out-of-range returns flagged, expense ratio checked against the 0.1% to 2.5% range.

Data quality: 40 rows, 0 missing returns, 0 non-numeric values, 0 returns outside -50% to 100%, 0 expense ratios outside 0.1% to 2.5% (range 0.55% to 1.64%). 0 rows flagged.

## fact_aum

Assets under management by fund house on a given date.

| Column | Type | Definition |
|---|---|---|
| date | TEXT (YYYY-MM-DD) | Reporting date. Primary key with fund_house. Foreign key to dim_date. |
| fund_house | TEXT | Asset management company. Primary key with date. |
| aum_crore | REAL | Total assets under management in crore INR. Always 0 or greater. |
| num_schemes | INTEGER | Number of schemes the fund house runs on that date. |

Note: the source file also contains aum_lakh_crore, which is the same figure in a different unit. It was dropped because aum_crore carries the same information.

Note: fact_aum links to dim_date but not to dim_fund, because it is recorded per fund house, not per scheme.

## Business Terms

| Term | Meaning |
|---|---|
| AUM | Assets under management: total money the fund manages. |
| NAV | Net Asset Value: price of one unit of a fund. |
| SIP | Systematic Investment Plan: fixed amount invested at regular intervals, usually monthly. |
| Lumpsum | One-time investment. |
| Redemption | Withdrawal of money from a fund. |
| Expense ratio | Annual fee as a percentage of assets. |
| Exit load | Fee on early redemption. |
| KYC | Know Your Customer: identity verification required before investing. |
| AMFI code | Unique 6-digit code assigned to each scheme by the Association of Mutual Funds in India. |
| Crore | 10 million (1 crore = 10,000,000). |
| Lakh | 100,000 (1 lakh = 100,000). |
