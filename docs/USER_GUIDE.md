# Aivara User Guide

Welcome to **Aivara**, an autonomous business intelligence and presentation platform designed to transform raw tabular spreadsheets into executive-ready dashboards and PowerPoint decks.

---

## 1. Preparing Your Data

Aivara is designed to ingest messy, arbitrary business tabular data without requiring custom ETL scripts.

### Supported File Formats
- **CSV (`.csv`)**: Any delimiter (comma, semicolon, tab, pipe), UTF-8, UTF-16, Latin-1, or Windows-1252 encodings.
- **Excel (`.xlsx`)**: Standard modern Excel workbooks (first active worksheet parsed).

### Ingestion Guidelines & Limits
- **Maximum File Size**: 100 MB.
- **Maximum Columns**: 500 columns.
- **Maximum Rows**: 500,000 rows. Files exceeding 500k rows are deterministically sampled down to 500k rows with an informative notification displayed in the UI.
- **Metadata Rows**: Aivara automatically detects and skips title rows, report timestamps, and blank lines before the real table headers.
- **Summary Rows**: Trailing summary rows (e.g. "Total", "Grand Total") are pruned to prevent double-counting.

---

## 2. Ingestion & Schema Review

When you upload a file, Aivara performs an automated first pass:

1. **Cleaning**:
   - Detects missing value strings (`N/A`, `NULL`, `none`, `-`) and standardizes them.
   - Detects compact date formats (`YYYYMMDD`) and standardizes dates.
   - Divides percentage columns by 100 if stored on a 0–100 scale.
2. **Semantic Role Classification**:
   - **Date Column**: The primary chronological dimension used for trend analysis.
   - **Metrics**: Numeric columns representing quantities, currency, volumes, or rates.
   - **Dimensions**: Categorical fields used for grouping, driver breakdowns, and cohort analysis.
   - **ID Columns**: Primary keys or high-cardinality unique codes (e.g. `Order_ID`, `Transaction_Hash`).
3. **Schema Review Gate**:
   - An interactive schema panel allows you to review and override classified column roles before pipeline execution.
   - You can designate primary metrics and verify assigned metric aggregation methods.

---

## 3. Metric Aggregation & Mathematical Rules

To maintain statistical integrity, Aivara applies distinct aggregation methods based on metric semantics:

- **Sum Aggregation (`sum`)**:
  - Applied to volumetric totals (e.g., `Revenue`, `Cost`, `Units Sold`, `Hours`).
  - Total = $\sum \text{values}$.
- **Mean Aggregation (`mean`)**:
  - Applied to rates, percentages, ratios, and averages (e.g., `Margin %`, `Conversion Rate`, `NPS`, `Satisfaction Score`, `Tenure`).
  - Average = $\frac{1}{n}\sum \text{values}$.
- **Period-over-Period Changes**:
  - Percentage changes are computed as: $\Delta\% = \frac{\text{Current} - \text{Prior}}{|\text{Prior}|} \times 100\%$.
  - When prior value is zero or undefined, delta displays as `+100.0%` or `N/A` rather than crashing with division-by-zero.

---

## 4. Dashboard Views & Tabs

Once processed, Aivara unlocks interactive analysis tabs based on your dataset profile:

### 4.1 Executive View
- High-level KPI tiles comparing the current period against the prior period.
- Primary metric trend line with historical context.
- Top contributing business dimension and key driver rankings.
- Automated natural language executive takeaways.

### 4.2 Revenue / Metric Deep-Dive
- Detailed timeseries charts with interactive date range filtering.
- Dimension breakdowns showing absolute contribution and share of total.

### 4.3 Drivers View
- Decomposes metric movements across categorical dimensions.
- Ranked explanatory power showing which dimensions (e.g., `Region`, `Product Line`, `Customer Tier`) account for variance.
- Correlation matrix for identifying relationships between numeric metrics ($n \ge 5$).

### 4.4 Risk & Anomaly Signals
- Automatically surfaces operational and statistical anomalies:
  - **Temporal Anomalies**: Rolling-baseline standard score $|z| \ge 2.5$ deviations from expected history.
  - **Structural Outliers**: Unusual distributional spikes in static snapshots.
  - **Concentration Risk**: Herfindahl-Hirschman index (HHI) warnings when revenue or volume is excessively concentrated in few categories.
  - **Budget / Cost Overruns**: Flagging variance thresholds.

### 4.5 Domain Specialized Views
- When specialized schemas are detected, dedicated tabs are activated:
  - **Commerce**: Average Order Value (AOV), top customer cohorts, refund rates.
  - **Finance**: Gross margin percentages, OPEX vs. Revenue breakdowns.
  - **Workforce**: Headcount distribution, salary bands, attrition risk indicators.
  - **Feedback**: Net Promoter Score (NPS) breakdown (% Promoters − % Detractors), sentiment distributions.

---

## 5. Exporting to PowerPoint (`.pptx`)

You can export the entire dashboard into a presentation deck via the sidebar:

1. Click **Export Presentation (.pptx)** in the sidebar.
2. Aivara compiles an OpenXML PowerPoint presentation featuring:
   - Branded 16:9 widescreen layout with corporate typography.
   - Cover slide with dataset metadata and timestamp.
   - Auto-generated Table of Contents.
   - Executive Summary slide with KPI scorecard and primary chart.
   - Dedicated domain analysis slides with Plotly visualizations and driver tables.
   - Comprehensive Risk & Recommendations slide.
3. **Safety & Privacy Guarantees**:
   - Formula injection characters (`=`, `+`, `-`, `@`) are neutralized to prevent spreadsheet execution vulnerabilities.
   - Graphics rendering is strictly local via Kaleido; zero network calls occur during export.

---

## 6. Troubleshooting Common Notices

| Notice / Warning | Meaning & Recommended Action |
| :--- | :--- |
| `"Dataset exceeds 500,000 rows; sampled down for responsiveness."` | Your file was safely sampled down to 500,000 rows. Results reflect a statistically representative sample. |
| `"Skipped N malformed lines during CSV loading."` | Some rows had uneven column counts or corrupted quotes. They were omitted to preserve dataset integrity. |
| `"Auto-detected table header at row N."` | Metadata or title rows above the actual table headers were automatically bypassed. |
| `"Offline narrative fallback used."` | LLM generation was skipped due to offline mode, missing API key, or exhausted daily budget. All numerical calculations remain 100% accurate. |
