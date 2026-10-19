"""
scripts/record_demo.py — Autonomous High-Definition Demo Video Recorder for Aivara
Uses Playwright with video recording to demonstrate all capabilities of the
Business Intelligence Executive Canvas and Boardroom PPTX Deck Studio.
"""

import os
import shutil

import cv2
from playwright.sync_api import sync_playwright

OUTPUT_DIR = os.path.abspath("demo_output")
ARTIFACT_DIR = r"C:\Users\user\.gemini\antigravity\brain\259a461e-5345-4572-9c84-c1b5803acf2a"


def record_full_demo():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-web-security", "--allow-file-access-from-files"],
        )

        # 16:9 high definition canvas
        context = browser.new_context(
            viewport={"width": 1600, "height": 900},
            record_video_dir=OUTPUT_DIR,
            record_video_size={"width": 1600, "height": 900},
        )

        page = context.new_page()

        # 1. Navigate to Executive Canvas
        print("[NAV] Navigating to http://localhost:3000...")
        page.goto("http://localhost:3000", wait_until="networkidle")
        page.wait_for_timeout(2000)

        # Inject mouse follower and executive chapter banner HUD
        page.evaluate("""() => {
            // Elegant chapter banner HUD
            const b = document.createElement('div');
            b.id = 'demo-hud-banner';
            b.style.cssText = `
                position: fixed;
                bottom: 48px;
                right: 24px;
                z-index: 999999;
                background: rgba(15, 23, 42, 0.94);
                backdrop-filter: blur(12px);
                border: 1px solid rgba(0, 120, 212, 0.5);
                border-radius: 12px;
                padding: 14px 20px;
                color: white;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                box-shadow: 0 16px 36px rgba(0, 0, 0, 0.45);
                max-width: 480px;
                pointer-events: none;
                transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
            `;
            document.body.appendChild(b);

            // Glowing cursor dot
            const c = document.createElement('div');
            c.id = 'demo-cursor-dot';
            c.style.cssText = `
                position: fixed;
                width: 22px;
                height: 22px;
                border-radius: 50%;
                background: rgba(0, 120, 212, 0.7);
                border: 2px solid #ffffff;
                box-shadow: 0 0 12px rgba(0, 120, 212, 0.8);
                pointer-events: none;
                z-index: 1000000;
                transform: translate(-50%, -50%);
                transition: transform 0.08s ease, width 0.12s ease, height 0.12s ease, background 0.12s ease;
                display: block;
                top: 450px;
                left: 800px;
            `;
            document.body.appendChild(c);

            window.__showHud = (chapter, title, description) => {
                b.style.transform = 'translateY(10px) scale(0.97)';
                b.style.opacity = '0';
                setTimeout(() => {
                    b.innerHTML = `
                        <div style="display:flex;align-items:center;gap:8px;margin-bottom:5px;">
                            <span style="background:#0078D4;color:#fff;font-size:10px;font-weight:800;padding:3px 9px;border-radius:9999px;text-transform:uppercase;letter-spacing:0.06em;">${chapter}</span>
                            <span style="font-size:13px;font-weight:700;color:#f8fafc;">${title}</span>
                        </div>
                        <div style="font-size:11px;color:#cbd5e1;line-height:1.45;">${description}</div>
                    `;
                    b.style.transform = 'translateY(0) scale(1)';
                    b.style.opacity = '1';
                }, 120);
            };

            window.__moveCursor = (x, y, click=false) => {
                c.style.left = x + 'px';
                c.style.top = y + 'px';
                if (click) {
                    c.style.width = '30px';
                    c.style.height = '30px';
                    c.style.background = 'rgba(239, 68, 68, 0.85)';
                    setTimeout(() => {
                        c.style.width = '22px';
                        c.style.height = '22px';
                        c.style.background = 'rgba(0, 120, 212, 0.7)';
                    }, 220);
                }
            };
        }""")

        def hud(chapter, title, desc):
            page.evaluate(f"window.__showHud({repr(chapter)}, {repr(title)}, {repr(desc)})")

        def cursor_to(selector, click=False, timeout=2500):
            try:
                loc = page.locator(selector).first
                if loc.is_visible(timeout=timeout):
                    box = loc.bounding_box(timeout=timeout)
                    if box:
                        cx = box["x"] + box["width"] / 2
                        cy = box["y"] + box["height"] / 2
                        page.evaluate(f"window.__moveCursor({cx}, {cy}, {str(click).lower()})")
                        if click:
                            loc.click(timeout=timeout)
            except Exception as e:
                print(f"[WARN] cursor_to({selector}) skipped: {e}")

        # =========================================================================
        # CHAPTER 1: Business Intelligence Executive Canvas Overview & KPI Cockpit
        # =========================================================================
        print("[CHAPTER 1] Overview & KPI Cockpit")
        hud(
            "CHAPTER 1",
            "Business Intelligence Executive Canvas",
            "Autonomous tabular intelligence with strict 100vh desktop ergonomics, pinned ribbon, and real-time KPI scorecards.",
        )
        page.wait_for_timeout(2000)

        # Highlight top ribbon
        cursor_to("text=BUSINESS INTELLIGENCE EXECUTIVE CANVAS")
        page.wait_for_timeout(1500)

        # Highlight KPI tiles
        cursor_to("#kpi1Value")
        page.wait_for_timeout(1000)
        cursor_to("#kpi2Value")
        page.wait_for_timeout(1000)
        cursor_to("#kpi4Value")
        page.wait_for_timeout(1500)

        # =========================================================================
        # CHAPTER 2: Dynamic Slicers & Instant In-Memory Re-Aggregation
        # =========================================================================
        print("[CHAPTER 2] Dynamic Slicers")
        hud(
            "CHAPTER 2",
            "Interactive Temporal Slicers",
            "Instant recalculation across 30D, 90D, and All-Time analytical windows with delta variances.",
        )
        cursor_to("button:has-text('30D')", click=True)
        page.wait_for_timeout(2000)

        cursor_to("button:has-text('90D')", click=True)
        page.wait_for_timeout(2000)

        cursor_to("button:has-text('All')", click=True)
        page.wait_for_timeout(2000)

        # =========================================================================
        # CHAPTER 3: Preloaded Industry Archetypes
        # =========================================================================
        print("[CHAPTER 3] Industry Archetypes")
        hud(
            "CHAPTER 3",
            "Enterprise Industry Archetypes",
            "Switching instantaneously between Commerce, Warehouse Inventory, P&L Finance, and Customer Feedback.",
        )
        cursor_to("#pbiArchetypeSelector")
        page.select_option("#pbiArchetypeSelector", "inventory")
        page.wait_for_timeout(2500)

        page.select_option("#pbiArchetypeSelector", "finance")
        page.wait_for_timeout(2500)

        page.select_option("#pbiArchetypeSelector", "commerce")
        page.wait_for_timeout(2000)

        # =========================================================================
        # CHAPTER 4: Page 2 — Hierarchical Decomposition Tree (Root-Cause Engine)
        # =========================================================================
        print("[CHAPTER 4] Decomposition Tree")
        hud(
            "CHAPTER 4",
            "Decomposition Tree Root-Cause Explorer",
            "Explore multi-level categorical drivers dynamically with visual contribution bars and zero interruptions.",
        )
        cursor_to("#pbiTabBtn-decomp", click=True)
        page.wait_for_timeout(2000)

        # Click on branch nodes to expand sub-branches
        page.evaluate(
            "() => { if (typeof toggleDecompBranch === 'function') toggleDecompBranch(0); }"
        )
        page.wait_for_timeout(2000)

        page.evaluate(
            "() => { if (typeof toggleDecompBranch === 'function') toggleDecompBranch(1); }"
        )
        page.wait_for_timeout(2500)

        # =========================================================================
        # CHAPTER 5: Page 3 — Multi-Level Financial Matrix Table
        # =========================================================================
        print("[CHAPTER 5] Financial Matrix Table")
        hud(
            "CHAPTER 5",
            "Financial Matrix Table & In-Cell Data Bars",
            "Hierarchical collapsible rows with in-cell gradient data bars and YoY variance tracking.",
        )
        cursor_to("#pbiTabBtn-matrix", click=True)
        page.wait_for_timeout(2000)

        # Collapse & Expand
        cursor_to("button:has-text('Collapse All')", click=True)
        page.wait_for_timeout(1800)

        cursor_to("button:has-text('Expand All Levels')", click=True)
        page.wait_for_timeout(2500)

        # =========================================================================
        # CHAPTER 6: Page 4 — Statistical Anomaly Detector
        # =========================================================================
        print("[CHAPTER 6] Statistical Anomaly Detector")
        hud(
            "CHAPTER 6",
            "Statistical Anomaly Detector",
            "Rolling-baseline |z| ≥ 2.50σ outlier detection with severity triage and automated risk scorecards.",
        )
        cursor_to("#pbiTabBtn-anomaly", click=True)
        page.wait_for_timeout(2500)

        # =========================================================================
        # CHAPTER 7: Page 5 — Data Schema & Query Gate
        # =========================================================================
        print("[CHAPTER 7] Data Schema & Query Gate")
        hud(
            "CHAPTER 7",
            "Data Schema & Query Gate",
            "Inspect semantic column deductions, volumetric vs rate aggregation guardrails, and data hygiene audits.",
        )
        cursor_to("#pbiTabBtn-transform", click=True)
        page.wait_for_timeout(2500)

        # =========================================================================
        # CHAPTER 8: Page 6 — Boardroom Presentation Studio & Deck Customizer
        # =========================================================================
        print("[CHAPTER 8] Boardroom Presentation Studio")
        hud(
            "CHAPTER 8",
            "Boardroom Presentation Studio & Deck Customizer",
            "Customize deck metadata, rearrange slide sequence, assign dashboard visuals, and edit narrative notes.",
        )
        cursor_to("#pbiTabBtn-export", click=True)
        page.wait_for_timeout(2000)

        # Edit Presentation Title
        cursor_to("#deckStudioTitle")
        page.evaluate(
            "() => { document.getElementById('deckStudioTitle').value = 'Q3 Global Executive Performance Review'; deckStudioUpdateMeta(); }"
        )
        page.wait_for_timeout(1200)

        # Edit Enterprise Client
        cursor_to("#deckStudioOrg")
        page.evaluate(
            "() => { document.getElementById('deckStudioOrg').value = 'Acme Global Enterprise'; deckStudioUpdateMeta(); }"
        )
        page.wait_for_timeout(1200)

        # Edit Reporting Period
        cursor_to("#deckStudioPeriod")
        page.evaluate(
            "() => { document.getElementById('deckStudioPeriod').value = 'FY 2026 Q3 / Full Quarter'; deckStudioUpdateMeta(); }"
        )
        page.wait_for_timeout(1200)

        # Select Slide 2
        page.evaluate("() => deckStudioSelectSlide(1)")
        page.wait_for_timeout(1500)

        # Move Slide 2 Down and then Up
        page.evaluate("() => deckStudioMoveSlide(1, 1)")
        page.wait_for_timeout(1500)

        page.evaluate("() => deckStudioMoveSlide(2, -1)")
        page.wait_for_timeout(1500)

        # Add a custom slide
        hud(
            "CUSTOM SLIDES",
            "Dynamic Slide Builder",
            "Add custom slides, reassign dashboard visuals, and tailor executive takeaway commentary.",
        )
        page.evaluate("() => deckStudioAddSlide()")
        page.wait_for_timeout(1500)

        # Select the newly added slide and update graph placement
        page.evaluate("""() => {
            const lastIdx = DECK_STUDIO_STATE.slides.length - 1;
            deckStudioSelectSlide(lastIdx);
            deckStudioUpdateSlide(lastIdx, 'title', 'Predictive Anomaly & Risk Governance');
            deckStudioUpdateSlide(lastIdx, 'graphType', 'anomaly_radar');
            deckStudioUpdateSlide(lastIdx, 'narrative', 'Automated anomaly watchdog detected zero high-severity variances.\\nStandard deviation baseline holds steady across operating facilities.\\nBoardroom recommendation: Maintain existing governance framework.');
        }""")
        page.wait_for_timeout(2500)

        # Live 16:9 Presentation Preview Carousel
        hud(
            "LIVE 16:9 CAROUSEL",
            "Real-Time Slide Deck Preview",
            "Widescreen 16:9 preview updates in real time with headers, visual placement, and narrative cards.",
        )
        page.evaluate("() => deckStudioNavSlide(1)")
        page.wait_for_timeout(1500)

        page.evaluate("() => deckStudioNavSlide(1)")
        page.wait_for_timeout(1500)

        page.evaluate("() => deckStudioNavSlide(1)")
        page.wait_for_timeout(1500)

        page.evaluate("() => deckStudioNavSlide(-2)")
        page.wait_for_timeout(1500)

        # One-Click Air-Gapped PPTX Download
        hud(
            "AIR-GAPPED EXPORT",
            "Native PowerPoint Export",
            "Compiling custom 16:9 .pptx presentation deck with 0 external network requests.",
        )
        cursor_to("button:has-text('Download Customized Presentation')", click=True)
        page.evaluate(
            "() => { if (typeof deckStudioDownloadPptx === 'function') deckStudioDownloadPptx(); }"
        )
        page.wait_for_timeout(4000)

        # Finale
        hud(
            "DEMO COMPLETE",
            "Aivara Business Intelligence Executive Canvas",
            "100% Offline • Industrial-Grade Precision • Boardroom Presentation Ready.",
        )
        page.wait_for_timeout(3500)

        # Finalize Video
        video = page.video
        context.close()
        browser.close()

        video_path = video.path()
        print(f"[SUCCESS] Playwright video recorded to: {video_path}")
        return video_path


def convert_webm_to_mp4(webm_path, mp4_path):
    print(f"[CONVERT] Transcoding {webm_path} -> {mp4_path} via OpenCV...")
    cap = cv2.VideoCapture(webm_path)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open {webm_path} with OpenCV")
        return False

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Video Info: {width}x{height} @ {fps:.1f} fps, {total_frames} frames")

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(mp4_path, fourcc, fps, (width, height))

    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)
        frame_count += 1
        if frame_count % 150 == 0:
            print(f"Processed {frame_count}/{total_frames} frames...")

    cap.release()
    out.release()
    print(f"[SUCCESS] Transcoded MP4 saved to: {mp4_path}")
    return True


if __name__ == "__main__":
    raw_video = record_full_demo()

    # Destination paths
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    target_webm = os.path.join(ARTIFACT_DIR, "demo_video.webm")
    target_mp4 = os.path.join(ARTIFACT_DIR, "demo_video.mp4")

    # Copy webm
    shutil.copy2(raw_video, target_webm)
    print(f"[SAVED] Copied webm to: {target_webm}")

    # Transcode to mp4
    convert_webm_to_mp4(target_webm, target_mp4)
    print("Demo recording and transcoding finished successfully!")
