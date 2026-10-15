#!/usr/bin/env python3
"""
scripts/record_demo_video.py — Automated High-Resolution Live Demo Video Director.

Launches the Aivara v1.0.0 Streamlit application, connects via Playwright in 1080p,
and conducts a guided, live walkthrough of every system capability:
- Universal spreadsheet ingestion (Call Center XLSX from Downloads)
- Auto-header detection skipping leading title rows
- Ingestion Data Quality Audit panel
- Semantic column classification and schema review gate
- Executive scorecard with period-over-period delta badges
- Interactive Plotly trend chart with hover tooltips
- Boardroom Executive Takeaways
- Domain-specific views (Feedback/CSAT & Sentiment analytics)
- Key Drivers decomposition & Pearson correlation matrix heatmap
- Statistical risk signals & temporal rolling-baseline anomalies
- Archetype switching to Inventory Snapshot
- Branded 16:9 widescreen PowerPoint deck generation & download
- Privacy settings, API key masking, and daily budget monitor
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

# Ensure UTF-8 output encoding on Windows console
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from playwright.sync_api import Page, sync_playwright

OUTPUT_DIR = Path("demo_output").resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR = OUTPUT_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

DOWNLOADS_DIR = Path(os.path.expanduser("~/Downloads"))
CALL_CENTER_FILE = DOWNLOADS_DIR / "Call-Center-Sentiment-Sample-Data.xlsx"
INVENTORY_FILE = DOWNLOADS_DIR / "Inventory-Records-Sample-Data.xlsx"


def inject_hud(page: Page, title: str, subtitle: str) -> None:
    """Injects a modern, polished on-screen HUD pill describing the active feature."""
    hud_script = f"""
    (() => {{
        let hud = document.getElementById("aivara-demo-hud");
        if (!hud) {{
            hud = document.createElement("div");
            hud.id = "aivara-demo-hud";
            hud.style.position = "fixed";
            hud.style.top = "18px";
            hud.style.left = "50%";
            hud.style.transform = "translateX(-50%)";
            hud.style.zIndex = "9999999";
            hud.style.background = "linear-gradient(135deg, rgba(13, 43, 92, 0.95), rgba(20, 30, 60, 0.95))";
            hud.style.color = "#FFFFFF";
            hud.style.padding = "10px 24px";
            hud.style.borderRadius = "30px";
            hud.style.boxShadow = "0 10px 30px rgba(0, 0, 0, 0.35), 0 0 15px rgba(0, 139, 139, 0.3)";
            hud.style.fontFamily = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
            hud.style.display = "flex";
            hud.style.alignItems = "center";
            hud.style.gap = "14px";
            hud.style.backdropFilter = "blur(10px)";
            hud.style.border = "1px solid rgba(0, 139, 139, 0.6)";
            hud.style.transition = "all 0.4s ease";
            document.body.appendChild(hud);
        }}
        hud.innerHTML = `
            <span style="background: #008B8B; color: #FFFFFF; padding: 4px 12px; border-radius: 12px; font-weight: 700; font-size: 13px; letter-spacing: 0.5px; text-transform: uppercase;">Aivara v1.0</span>
            <span style="font-size: 15px; font-weight: 600; color: #FFFFFF;">{title}</span>
            <span style="color: #64D2D2; font-size: 13.5px; font-weight: 400;">• {subtitle}</span>
        `;
    }})();
    """
    page.evaluate(hud_script)


def smooth_scroll(page: Page, y_offset: int, steps: int = 6) -> None:
    """Smoothly scroll the page to simulate natural operator browsing."""
    current_y = page.evaluate("window.scrollY")
    diff = y_offset - current_y
    step_diff = diff / steps
    for i in range(steps):
        page.evaluate(f"window.scrollTo(0, {current_y + (i + 1) * step_diff})")
        time.sleep(0.08)


def wait_for_server(url: str, timeout: float = 30.0) -> bool:
    """Wait for the Streamlit web server to become healthy."""
    import urllib.request

    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(f"{url}/_stcore/health", timeout=2.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.8)
    return False


def run_recording() -> Path:
    print("=" * 70)
    print("        AIVARA v1.0.0 — AUTOMATED LIVE DEMO VIDEO DIRECTOR           ")
    print("=" * 70)

    # 1. Start Streamlit server in headless mode
    print("🚀 Launching Streamlit application server on port 8501...")
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "app.py",
        "--server.port=8501",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
    ]
    env = os.environ.copy()
    env["AIVARA_ENV"] = "prod"
    env["AIVARA_LLM_REDACT_LABELS"] = "true"

    server_proc = subprocess.Popen(
        cmd,
        cwd=Path(__file__).parent.parent,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        if not wait_for_server("http://localhost:8501"):
            raise RuntimeError("Streamlit server failed to start within 30 seconds.")
        print("✅ Streamlit server online at http://localhost:8501")

        # 2. Launch Playwright with 1080p Full HD video recording
        print("🎥 Initializing Playwright Chromium Director (1920x1080 Full HD)...")
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--start-maximized", "--no-sandbox", "--disable-infobars"],
            )
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                record_video_dir=str(OUTPUT_DIR),
                record_video_size={"width": 1920, "height": 1080},
            )
            page = context.new_page()

            # -------------------------------------------------------------
            # Scene 1: Welcome & Landing Page
            # -------------------------------------------------------------
            print("🎬 Scene 1: Welcome & Universal Ingestion Landing Page...")
            page.goto("http://localhost:8501")
            page.wait_for_selector('text="Upload your data"', timeout=15000)
            time.sleep(1.0)

            inject_hud(
                page,
                "Welcome to Aivara",
                "Autonomous Tabular Intelligence & Executive Presentation Engine",
            )
            page.screenshot(path=str(SCREENSHOTS_DIR / "01_landing_page.png"))
            time.sleep(2.5)

            # -------------------------------------------------------------
            # Scene 2: Ingestion & Auto-Header Detection (Row 6 Bypassed)
            # -------------------------------------------------------------
            print("🎬 Scene 2: Ingesting Call-Center-Sentiment-Sample-Data.xlsx from Downloads...")
            inject_hud(
                page,
                "Universal Ingestion Engine",
                "Ingesting unformatted Excel workbook from Downloads folder",
            )

            file_input = page.locator('input[type="file"]')
            file_input.set_input_files(str(CALL_CENTER_FILE))
            time.sleep(3.0)

            # Let ingestion finish and confirm button appear
            confirm_btn = page.locator('button:has-text("Confirm schema and build dashboard")')
            confirm_btn.wait_for(state="visible", timeout=25000)
            inject_hud(
                page,
                "Smart Ingestion Audit",
                "Auto-detected header at row 6 • Stripped decorative metadata",
            )
            time.sleep(1.5)

            # Expand Data Quality Summary
            summary_expander = page.locator('text="📊 Data Quality & Ingestion Summary"')
            if summary_expander.is_visible():
                summary_expander.click()
                time.sleep(2.0)
                page.screenshot(path=str(SCREENSHOTS_DIR / "02_data_quality_summary.png"))
                time.sleep(2.0)

            # -------------------------------------------------------------
            # Scene 3: Schema Review & Statistical Aggregation Assignment
            # -------------------------------------------------------------
            print("🎬 Scene 3: Reviewing semantic column roles & statistical aggregations...")
            inject_hud(
                page,
                "Schema Review Gate",
                "Semantic role inference • Mean aggregation for CSAT Score • Verified",
            )
            smooth_scroll(page, 300)
            time.sleep(2.0)
            page.screenshot(path=str(SCREENSHOTS_DIR / "03_schema_review.png"))

            # Click Confirm Schema button
            confirm_btn = page.locator('button:has-text("Confirm schema and build dashboard")')
            confirm_btn.scroll_into_view_if_needed()
            confirm_btn.click()

            # Wait for dashboard to compute and display tabs
            page.locator('[data-testid="stTab"]').first.wait_for(state="visible", timeout=25000)
            time.sleep(2.5)

            # -------------------------------------------------------------
            # Scene 4: Executive Scorecard & Interactive Plotly Trend
            # -------------------------------------------------------------
            print("🎬 Scene 4: Executive Dashboard & Boardroom Takeaways...")
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(1.0)
            inject_hud(
                page,
                "Executive Dashboard",
                "Live KPI Scorecards • Period-over-Period Deltas • Boardroom Takeaways",
            )
            page.screenshot(path=str(SCREENSHOTS_DIR / "04_executive_dashboard.png"))
            time.sleep(2.5)

            # Smooth scroll down to examine KPI cards and Plotly chart
            smooth_scroll(page, 450)
            time.sleep(1.5)

            # Hover over Plotly trend chart to demonstrate interactivity
            chart_container = page.locator(".js-plotly-plot").first
            if chart_container.is_visible():
                box = chart_container.bounding_box()
                if box:
                    page.mouse.move(box["x"] + box["width"] * 0.35, box["y"] + box["height"] * 0.45)
                    time.sleep(1.0)
                    page.mouse.move(box["x"] + box["width"] * 0.65, box["y"] + box["height"] * 0.40)
                    time.sleep(1.2)

            time.sleep(2.0)

            # -------------------------------------------------------------
            # Scene 5: Domain Analytics View (Customer Feedback & CSAT)
            # -------------------------------------------------------------
            print("🎬 Scene 5: Deep-Dive into Domain Feedback Analytics...")
            page.evaluate("window.scrollTo(0, 100)")
            time.sleep(1.0)
            inject_hud(
                page,
                "Domain Analytics Pack",
                "Customer Feedback & Sentiment • CSAT Distribution & Channel Breakdown",
            )

            feedback_tab = page.locator('button[data-testid="stTab"]').filter(has_text="Feedback")
            if feedback_tab.is_visible():
                feedback_tab.click()
                time.sleep(2.5)
                smooth_scroll(page, 400)
                page.screenshot(path=str(SCREENSHOTS_DIR / "05_feedback_domain_tab.png"))
                time.sleep(3.0)

            # -------------------------------------------------------------
            # Scene 6: Key Drivers View & Pearson Correlation Matrix
            # -------------------------------------------------------------
            print("🎬 Scene 6: Key Drivers & Correlation Heatmap...")
            inject_hud(
                page,
                "Key Drivers Engine",
                "Dimensional Explanatory Power • Pearson Correlation Matrix (n ≥ 5)",
            )

            drivers_tab = page.locator('button[data-testid="stTab"]').filter(has_text="Drivers")
            if drivers_tab.is_visible():
                drivers_tab.click()
                time.sleep(2.5)
                smooth_scroll(page, 450)
                page.screenshot(path=str(SCREENSHOTS_DIR / "06_key_drivers_tab.png"))
                time.sleep(3.0)

            # -------------------------------------------------------------
            # Scene 7: Risk Signals & Temporal Rolling-Baseline Anomalies
            # -------------------------------------------------------------
            print("🎬 Scene 7: Risk Signals & Anomaly Detection...")
            inject_hud(
                page,
                "Risk & Anomaly Radar",
                "Temporal Rolling-Baseline Anomalies (|z| ≥ 2.5) • Concentration Index",
            )

            risk_tab = page.locator('button[data-testid="stTab"]').filter(has_text="Risk Signals")
            if risk_tab.is_visible():
                risk_tab.click()
                time.sleep(2.5)
                smooth_scroll(page, 400)
                page.screenshot(path=str(SCREENSHOTS_DIR / "07_risk_signals_tab.png"))
                time.sleep(3.0)

            # -------------------------------------------------------------
            # Scene 8: PowerPoint Presentation Generation & Export
            # -------------------------------------------------------------
            print("🎬 Scene 8: Executive PowerPoint Deck Export (.pptx)...")
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(1.0)
            inject_hud(
                page,
                "Executive Presentation Export",
                "Compiling 16:9 Widescreen PowerPoint Deck • Formula Injection Defense",
            )

            prepare_export_btn = page.locator('button:has-text("Prepare PPTX export")')
            prepare_export_btn.scroll_into_view_if_needed()
            prepare_export_btn.click()
            time.sleep(3.5)

            # Download generated PPTX deck
            download_btn = page.locator('button:has-text("Download PPTX Deck")')
            if download_btn.is_visible():
                with page.expect_download(timeout=15000) as download_info:
                    download_btn.click()
                download = download_info.value
                download_path = OUTPUT_DIR / "Aivara_Executive_Presentation.pptx"
                download.save_as(str(download_path))
                print(f"✅ Downloaded PowerPoint presentation to {download_path}")

                inject_hud(
                    page,
                    "PowerPoint Deck Ready",
                    f"Generated 16:9 deck ({download_path.stat().st_size // 1024} KB) with zero network calls",
                )
                time.sleep(2.5)
                page.screenshot(path=str(SCREENSHOTS_DIR / "08_pptx_export_ready.png"))

            # -------------------------------------------------------------
            # Scene 9: Archetype Switching (Inventory Records Snapshot)
            # -------------------------------------------------------------
            print("🎬 Scene 9: Archetype Switching to Inventory Snapshot...")
            inject_hud(
                page,
                "Dynamic Archetype Adaptation",
                "Ingesting Inventory Records • Adapting to Snapshot Archetype",
            )

            file_input = page.locator('input[type="file"]')
            file_input.set_input_files(str(INVENTORY_FILE))
            time.sleep(3.0)

            # Confirm schema for Inventory dataset
            confirm_btn = page.locator('button:has-text("Confirm schema and build dashboard")')
            confirm_btn.wait_for(state="visible", timeout=25000)
            confirm_btn.scroll_into_view_if_needed()
            confirm_btn.click()
            page.locator('[data-testid="stTab"]').first.wait_for(state="visible", timeout=25000)
            time.sleep(2.0)

            inject_hud(
                page,
                "Operations Snapshot View",
                "Inventory balance, units sold, and stock-level metrics computed instantly",
            )
            smooth_scroll(page, 350)
            time.sleep(2.5)
            page.screenshot(path=str(SCREENSHOTS_DIR / "09_inventory_snapshot_view.png"))

            # -------------------------------------------------------------
            # Scene 10: Security, Privacy & Configuration Transparency
            # -------------------------------------------------------------
            print("🎬 Scene 10: Privacy, Security & Budget Transparency...")
            page.evaluate("window.scrollTo(0, 0)")

            # Open Settings expander in sidebar
            settings_expander = page.locator('[data-testid="stSidebar"]').get_by_text("Settings")
            if settings_expander.is_visible():
                settings_expander.click()
                time.sleep(1.5)

            inject_hud(
                page,
                "Enterprise Security & Privacy",
                "Label Pseudonymization ON • Zero Raw Data on Disk • Daily Budget Cap",
            )
            time.sleep(3.0)
            page.screenshot(path=str(SCREENSHOTS_DIR / "10_security_and_privacy.png"))

            # -------------------------------------------------------------
            # Scene 11: Grand Finale & Outro
            # -------------------------------------------------------------
            print("🎬 Scene 11: Production Release v1.0.0 Outro...")
            inject_hud(
                page,
                "Aivara v1.0.0 Production Release",
                "All 13 Phases Complete • Fully Tested & Hardened",
            )
            time.sleep(3.5)

            # Close page and context to finish video
            page.close()
            context.close()
            browser.close()

            # Identify the generated video file
            video_files = list(OUTPUT_DIR.glob("*.webm"))
            if not video_files:
                raise FileNotFoundError("Playwright did not generate a .webm video file.")

            # Pick newest .webm
            newest_video = max(video_files, key=lambda f: f.stat().st_mtime)
            target_webm = OUTPUT_DIR / "aivara_v1_demo.webm"
            if newest_video != target_webm:
                if target_webm.exists():
                    target_webm.unlink()
                newest_video.rename(target_webm)

            print(
                f"✅ Native 1080p WebM recording saved: {target_webm} ({target_webm.stat().st_size // (1024 * 1024)} MB)"
            )
            return target_webm

    finally:
        print("🛑 Terminating Streamlit server process...")
        server_proc.terminate()
        server_proc.wait(timeout=5)


if __name__ == "__main__":
    video_path = run_recording()
    print("=" * 70)
    print(f"Video Recording Successfully Completed: {video_path}")
    print("=" * 70)
