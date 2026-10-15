# Aivara — Autonomous Tabular Analytics & Executive Deck Generation

> 🎓 **Announcement**: **Internship Batch for this project starting 19 Oct 2026.** Applications are open via the [DBERT Internship Portal](https://internship.dbert.online/).

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](config.py)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-305%20passed-brightgreen.svg)](tests/)
[![Security](https://img.shields.io/badge/security-hardened-brightgreen.svg)](docs/SECURITY.md)

**Aivara** is an autonomous business intelligence platform designed to transform raw, messy business spreadsheets into executive-ready dashboards and branded 16:9 widescreen PowerPoint presentation decks — with complete data privacy and local computation.

---

## 🌟 Key Features

### 1. Universal Spreadsheet Ingestion & Smart Cleaning
- **Tolerant File Loading**: Ingests raw CSV and Excel (`.xlsx`, `.xls`) files regardless of unformatted structures, mixed delimiters (comma, semicolon, tab, pipe), or legacy character encodings (UTF-8, UTF-16, Latin-1, CP1252).
- **Auto-Header Detection**: Automatically detects and bypasses decorative banner rows, corporate title blocks, and metadata headers to identify the true tabular header row.
- **Data Quality Audit Panel**: Provides an instant health check on every upload — highlighting row counts, column counts, flagged duplicate records, and normalized null values.

### 2. Semantic Column Role Inference & Schema Gate
- **Intelligent Classification**: Automatically assigns semantic roles to every column — distinguishing between `date`, `metric` (numeric KPIs), `dimension` (categorical breakdown), `id` (identifiers), and `text` (free-form feedback).
- **Statistical Aggregation Guardrails**: Intelligently distinguishes volumetric metrics (aggregated via `sum`) from rates, ratios, percentages, and scores (aggregated via `mean`), preventing common statistical errors like summing NPS or conversion rates.
- **Interactive Review Gate**: Operators can review, verify, or override inferred roles before generating the analytics dashboard.

### 3. Elevated Executive Dashboard
- **Top-of-Screen Focus**: Upon confirming the dataset schema, upload boxes and configuration forms automatically collapse, elevating the executive summaries, KPI scorecards, and interactive charts directly to the top of the viewport.
- **Boardroom Executive Takeaways**: AI-synthesized strategic bullets highlighting overall portfolio scale, leading contributors, period-over-period performance swings, and distribution concentration.
- **Dynamic KPI Scorecard**: High-impact metric tiles displaying total volume, averages, and period-over-period percentage variance badges with directional indicators.
- **Interactive Trend Charts**: High-definition time series visualizations with hover tooltips, date-range selectors, and automatic daily, weekly, or monthly aggregation.

### 4. Domain-Specific Intelligence Packs & Archetypes
Aivara automatically classifies datasets into the optimal analytical archetype and business domain:
- **Customer Feedback & Sentiment**: Net Promoter Score (NPS) breakdown, customer satisfaction (CSAT) ratings, sentiment distributions, and communication channel performance.
- **Commerce & Sales Performance**: Gross merchandise value, Average Order Value (AOV), transaction volumes, and product breakdown.
- **Financial Performance & Margin Analysis**: Revenue trends, operating expenditure (OPEX), operating margin %, and budget variance tracking.
- **Workforce & Organizational Insights**: Headcount distributions, compensation bands, tenure metrics, and departmental summaries.
- **Operations & Inventory Snapshots**: Cross-sectional analysis of warehouse stock, stockout risk indicators, and Pareto 80/20 concentration analysis.

### 5. Key Explanatory Drivers & Correlation Radar
- **Dimensional Decomposition**: Ranks categorical drivers by their mathematical explanatory power to reveal which factors drove performance gains or losses.
- **Pearson Correlation Matrix**: Computes a statistical correlation heatmap across all numerical dimensions ($n \ge 5$) to uncover hidden operational dependencies.

### 6. Statistical Risk Radar & Anomaly Detection
- **Rolling-Baseline Anomaly Alerts**: Flags statistically significant anomalies ($|z| \ge 2.5$) using historical rolling averages to identify operational spikes or sudden drops.
- **Concentration Risk Indicators**: Employs Herfindahl-Hirschman index algorithms to alert executives when revenue, inventory, or volume is excessively concentrated in too few entities.

### 7. Branded 16:9 Executive PowerPoint Presentation Export
- **One-Click Boardroom Deck Compilation**: Generates a complete 8-slide, 16:9 widescreen PowerPoint (`.pptx`) presentation ready for executive review.
- **Full Slide Showcase Included**:
  1. Executive Title & Run Metadata
  2. Boardroom Executive Summary & Strategic Takeaways
  3. Primary KPI Scorecards & Period-over-Period Deltas
  4. Domain Deep-Dive Analytics (Feedback, CSAT & Sentiment)
  5. Key Explanatory Drivers & Correlation Matrix
  6. Statistical Risk Radar & Anomaly Detection
  7. Enterprise Security & Sanitization Trace
  8. Methodology, Row Counts & Governance Sign-off
- **Spreadsheet Formula Injection Defense**: Implements strict CSV/formula sanitization (neutralizing characters like `=`, `+`, `-`, `@` with a leading `'`) to protect downstream presentation viewers from spreadsheet formula injection attacks (CWE-1236).

### 8. Enterprise Data Privacy & Local Air-Gapping
- **Zero Raw Data Egress**: Raw row data never leaves the server. All calculations, variance math, and statistical modeling are computed locally.
- **Categorical Label Pseudonymization**: Entity names, customer identifiers, and categorical labels are pseudonymized before generating natural language summaries (`Category A`, `Entity B`), ensuring proprietary identifiers never touch external APIs.
- **Daily Budget Monitor**: Built-in daily API quota tracking with visual progress indicators prevents unexpected cloud costs.

---

## 🎬 Demo Video & Media

A complete **1080p Full HD live video demonstration** (101 seconds) walks through universal ingestion of unformatted real-world business datasets, elevated dashboard exploration, archetype switching, and the high-definition PowerPoint slide deck showcase:

- **Universal Demo Video**: [demo_output/aivara_v1_demo.mp4](demo_output/aivara_v1_demo.mp4)
- **High-Definition Slide Deck Presentation**: [demo_output/Aivara_Executive_Presentation.pptx](demo_output/Aivara_Executive_Presentation.pptx)
- **Visual Walkthrough & Screenshot Gallery**: See the detailed walkthrough in [`walkthrough.md`](docs/USER_GUIDE.md).

---

## 🚀 Quick Setup & Usage

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/Aivaratechinfomatics/Aivara.git
cd Aivara

# Create virtual environment and install requirements
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration (Optional)
```bash
cp .env.example .env
# Add your OPENROUTER_API_KEY for optional AI narrative enrichment (offline mode supported by default)
```

### 3. Launch Application
```bash
streamlit run app.py
```
Open your browser to `http://localhost:8501`.

---

## 🏛️ Built by DBERT AI Venture Studio

Gayatri School OS was architected and built by the engineering squad at [DBERT](https://dbert.online/startups/portfolio/gayatri-ai) — India's premier AI Venture Studio, Delhi.

DBERT (Digital Blinc Education Research & Technology) incubates transformative AI products, ships institutional enterprise platforms, and trains top-tier engineers. Gayatri is developed under the DBERT Internship Program, Batch Aug–Oct 2026.

- 🌐 **Website**: [dbert.online](https://dbert.online/)
- 📂 **Startup Portfolio**: [dbert.online/startups/portfolio](https://dbert.online/startups/portfolio)
- 🎓 **DBERT Fellowship Program**: [dbert.online/learners/fellowship](https://dbert.online/learners/fellowship)
- 💼 **Internship Portal**: [internship.dbert.online](https://internship.dbert.online/)

---

## 🚀 About Aivara Tech

**Aivara Tech** is dedicated to pioneering autonomous data intelligence, tabular reasoning engines, and boardroom-ready presentation automation for modern enterprises. Built with a compute-first, privacy-by-design architecture, Aivara transforms raw tabular spreadsheets into executive-grade visual stories and verified analytical insights.

- 🎓 **Internship Batch**: Internship Batch for this project starting **19 Oct 2026**
- 🌐 **DBERT AI Venture Studio**: [dbert.online](https://dbert.online/)
- 💼 **Apply for Internship**: [internship.dbert.online](https://internship.dbert.online/)
- 📂 **Explore Enterprise Solutions**: [dbert.online/startups/portfolio](https://dbert.online/startups/portfolio)

---

## License

Aivara is open-source software licensed under the [Apache License, Version 2.0](LICENSE).
