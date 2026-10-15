# Aivara — Autonomous Tabular Analytics & Executive Deck Generation

> 🎓 **Announcement**: **Internship Batch for this project starting 19 Oct 2026.** Apply online at [aivaratech.online/internships](https://aivaratech.online/internships).

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](config.py)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-305%20passed-brightgreen.svg)](tests/)
[![Security](https://img.shields.io/badge/security-hardened-brightgreen.svg)](docs/SECURITY.md)

**Aivara** is an autonomous business intelligence platform designed to transform raw, messy business spreadsheets into executive-ready dashboards and branded 16:9 widescreen PowerPoint presentation decks — with complete data privacy and local computation.

---

## 🚀 About Aivara Tech

**Aivaratech Infomatics** ([aivaratech.online](https://aivaratech.online/)) builds practical technology across AI, data analytics, business intelligence, automation, RPA, and software engineering.

Our flagship operational product, **Aivara Insight**, is dedicated to pioneering autonomous tabular reasoning engines and boardroom-ready presentation automation for modern enterprises. Built with a compute-first, privacy-by-design architecture, Aivara transforms raw tabular spreadsheets into executive-grade visual stories and verified analytical insights with zero cloud data leaks.

### Connect & Opportunities with Aivara Tech
- 🌐 **Official Website**: [aivaratech.online](https://aivaratech.online/)
- 💼 **Apply for Internship**: [aivaratech.online/internships](https://aivaratech.online/internships)
- 🎓 **Upcoming Internship Batch**: Starting **19 Oct 2026** (2-month structured live engineering & BI tracks, senior technical mentorship, verified GitHub contribution credits, and Certificate of Completion/LOR)
- 🏛️ **DBERT AI Venture Studio**: [dbert.online](https://dbert.online/)
- 📂 **Explore Enterprise Solutions**: [dbert.online/startups/portfolio](https://dbert.online/startups/portfolio)

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
- **Spreadsheet Formula Injection Defense**: Implements strict CSV/formula sanitization (neutralizing characters like `=`, `+`, `-`, `@` with a leading `'`) to protect downstream presentation viewers from spreadsheet formula injection attacks (CWE-1236).

### 8. Enterprise Data Privacy & Local Air-Gapping
- **Zero Raw Data Egress**: Raw row data never leaves the server. All calculations, variance math, and statistical modeling are computed locally.
- **Categorical Label Pseudonymization**: Entity names, customer identifiers, and categorical labels are pseudonymized before generating natural language summaries (`Category A`, `Entity B`), ensuring proprietary identifiers never touch external APIs.
- **Daily Budget Monitor**: Built-in daily API quota tracking with visual progress indicators prevents unexpected cloud costs.

---

## 🎬 Live Demo Video, Presentation Deck & Visual Showcase

Aivara includes an automated, high-definition **1080p Full HD live video demonstration** (101 seconds) showcasing real business dataset ingestion, elevated executive summaries, archetype switching, and the high-definition PowerPoint deck presentation:

- 📹 **Universal Demo Video (1080p MP4)**: [demo_output/aivara_v1_demo.mp4](demo_output/aivara_v1_demo.mp4)
- 📊 **Generated PowerPoint Presentation (.pptx)**: [demo_output/Aivara_Executive_Presentation.pptx](demo_output/Aivara_Executive_Presentation.pptx)
- 🖥️ **Interactive Slide Deck Carousel**: [demo_output/slide_viewer.html](demo_output/slide_viewer.html)

### Generated 16:9 Executive PowerPoint Presentation (.pptx) Slides
The presentation engine generates boardroom-grade 16:9 slides natively with zero external dependencies:

| Slide 1: Cover Title & Metadata | Slide 3: Primary KPI Scorecard |
| :---: | :---: |
| ![Executive Cover](docs/assets/screenshots/11_slide_1_presentation.png) | ![KPI Scorecards](docs/assets/screenshots/11_slide_3_presentation.png) |

| Slide 4: Domain Analytics Deep-Dive | Slide 5: Key Explanatory Drivers |
| :---: | :---: |
| ![Domain Analytics](docs/assets/screenshots/11_slide_4_presentation.png) | ![Key Drivers](docs/assets/screenshots/11_slide_5_presentation.png) |

| Slide 7: Enterprise Security & Sanitization | Export Completed Deck |
| :---: | :---: |
| ![Security Defense](docs/assets/screenshots/11_slide_7_presentation.png) | ![Export Ready](docs/assets/screenshots/08_pptx_export_ready.png) |

### Interactive Application Workflow
| 1. Landing Page & Universal Ingestion | 2. Data Quality Audit Panel |
| :---: | :---: |
| ![Landing Page](docs/assets/screenshots/01_landing_page.png) | ![Data Quality](docs/assets/screenshots/02_data_quality_summary.png) |

| 3. Semantic Schema Review Gate | 4. Elevated Executive Dashboard |
| :---: | :---: |
| ![Schema Review](docs/assets/screenshots/03_schema_review.png) | ![Executive Dashboard](docs/assets/screenshots/04_executive_dashboard.png) |

| 5. Operations Inventory Snapshot | 6. Security, Pseudonymization & Budget |
| :---: | :---: |
| ![Inventory Snapshot](docs/assets/screenshots/09_inventory_snapshot_view.png) | ![Security Settings](docs/assets/screenshots/10_security_and_privacy.png) |

---

## 🛠️ Step-by-Step Local Testing Guide for Interns (Batch Starting 19 Oct 2026)

Welcome to the **Aivara Engineering & Data Analytics Internship**. Follow this step-by-step verification guide to set up your local development environment, run test datasets, and validate functional behavior.

### 1. Prerequisites
- **Python**: Version **3.12+** installed on your workstation.
- **Git**: Installed and configured with your name and email.
- **OS**: Windows, macOS, or Linux supported.

### 2. Environment Setup
```bash
# 1. Clone your assigned repository fork
git clone https://github.com/Aivaratechinfomatics/Aivara.git
cd Aivara

# 2. Create and activate an isolated virtual environment
python -m venv .venv

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On macOS / Linux:
source .venv/bin/activate

# 3. Upgrade pip and install all pinned dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Safe Offline Configuration
Aivara is architected to run **100% offline** by default for local analytical computation and presentation deck generation without requiring external API keys:
```bash
# Create local environment file from example template
cp .env.example .env

# Verify default settings:
# AIVARA_ENV=dev
# AIVARA_DAILY_BUDGET=30
# AIVARA_LLM_REDACT_LABELS=true
```

### 4. Running the Local Application
```bash
streamlit run app.py
```
Open your browser to `http://localhost:8501`.

### 5. Verification Checklist for Interns
Follow this checklist when reviewing features and testing changes:
1. **Universal File Upload**:
   - Upload any sample dataset (e.g. `tests/fixtures/clean.csv`, `currency.csv`, or sample business Excel workbooks from your `Downloads` folder).
   - Verify that the system automatically detects encoding and skips leading decorative title blocks.
2. **Data Quality Audit**:
   - Expand the **📊 Data Quality & Ingestion Summary** panel to verify row counts, column counts, and duplicate detection.
3. **Schema Review Gate**:
   - Verify semantic column roles (e.g., `date`, `metric`, `dimension`). Ensure volumetric metrics default to `sum` while rates/scores default to `mean`.
   - Click **Confirm schema and build dashboard**.
4. **Elevated Viewport Verification**:
   - Confirm that the file upload form and schema table collapse, immediately bringing **Boardroom Executive Takeaways**, **KPI scorecards**, and **interactive Plotly charts** to the top of your screen.
5. **Interactive Analytics Tabs**:
   - Test date-range filtering and hover over chart points to verify reactive tooltips.
   - Explore domain tabs (`Survey, NPS & Support`, `Correlations & Drivers`, `Risk & Outliers`).
6. **Executive Presentation Deck Export**:
   - In the sidebar, click **Prepare PPTX export**.
   - Click **Download PPTX Deck** and open the resulting `.pptx` file in PowerPoint or Keynote to verify 16:9 layout formatting.
7. **Dataset Switching**:
   - Click **📂 Load New Dataset** in the sidebar to reset session state and upload a secondary dataset (e.g. `tests/fixtures/inventory_sample.csv`).

### 6. Executing the Quality & Regression Battery
Before submitting pull requests, interns must ensure all automated quality gates pass:
```bash
# Run complete test suite (all 305 tests must pass)
pytest tests/ -v

# Run headless UI AppTest verification
pytest tests/test_ui_apptest.py -v

# Run invariant number consistency tests
pytest tests/test_core_correctness.py -v

# Run code formatting and linter checks
python -m ruff check .
python -m ruff format --check .
```

---

## 🛡️ Anti-Reverse Engineering & Intellectual Property (IP) Protection

To safeguard core analytical algorithms, proprietary heuristic engines, and institutional client data against reverse engineering, unauthorized cloning, and IP exfiltration, all contributors, interns, and deployment engineers must strictly adhere to the following security protocols:

### 1. Proprietary Core IP & Trade Secrets
- **Proprietary Heuristic Engines**: Aivara's core heuristic classifiers, automated semantic role deduction, dimensional variance decomposition, rolling-baseline anomaly algorithms ($|z| \ge 2.5$), and air-gapped facts synthesis are proprietary intellectual property of **Aivara Technologies** and **DBERT AI Venture Studio**.
- **Strict Prohibition on Public LLM Uploads**: Interns and developers must **NEVER** copy, upload, or paste internal algorithms, proprietary prompt templates, or raw business logic into public LLM interfaces (e.g., public ChatGPT, Claude, or Gemini chats). Doing so compromises trade secrets and violates your Non-Disclosure Agreement (NDA).

### 2. Zero Raw Data Egress & Network Air-Gapping
- Under the **Compute-First Principle**, raw user rows and internal business datasets are **never transmitted over external networks**.
- Regression tests in `tests/test_export_no_network.py` continuously enforce that the presentation export package contains zero external network dependencies and cannot be weaponized as an exfiltration vector.

### 3. Code Hardening & Anti-Tamper Invariants
- **Runtime Invariant Testing**: The test suite enforces strict mathematical regression invariants (`test_core_correctness.py`) ensuring that calculation engines cannot be modified, weakened, or silently tampered with.
- **Binary Packaging & Protected Bytecode**: For enterprise customer distribution, core modules are packaged via compiled CPython bytecode / Cython binary extensions (`.pyd`/`.so`) and deployed as hardened non-root container images without source files.
- **Formula Injection Defense**: All generated exports enforce sanitization against spreadsheet formula injection attacks (CWE-1236), neutralizing untrusted user inputs with prepended characters.

### 4. Legal Compliance & Contributor IP Assignment
- Contributions made during the **DBERT Internship Program** and **Aivara Technologies Development Cohorts** are governed by formal Intellectual Property Assignment and Confidentiality agreements.
- Unauthorized disassembly, reverse engineering, unauthorized public forks, or exfiltration of proprietary analytical assets will result in immediate termination, revocation of completion credentials, and legal enforcement under applicable copyright and trade secret laws.

---

## 🏛️ Built by DBERT AI Venture Studio

Gayatri School OS was architected and built by the engineering squad at [DBERT](https://dbert.online/startups/portfolio/gayatri-ai) — India's premier AI Venture Studio, Delhi.

DBERT (Digital Blinc Education Research & Technology) incubates transformative AI products, ships institutional enterprise platforms, and trains top-tier engineers. Gayatri is developed under the DBERT Internship Program, Batch Aug–Oct 2026.

- 🌐 **Website**: [dbert.online](https://dbert.online/)
- 📂 **Startup Portfolio**: [dbert.online/startups/portfolio](https://dbert.online/startups/portfolio)
- 🎓 **DBERT Fellowship Program**: [dbert.online/learners/fellowship](https://dbert.online/learners/fellowship)
- 💼 **Internship Portal**: [internship.dbert.online](https://internship.dbert.online/)

---

## License

Aivara is open-source software licensed under the [Apache License, Version 2.0](LICENSE).
