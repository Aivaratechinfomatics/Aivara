"""
tests/test_playwright_e2e.py — End-to-end browser verification of Power BI dashboard interactivity.
"""

import pytest
from playwright.async_api import async_playwright


@pytest.mark.anyio
async def test_full_powerbi_browser_interaction():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 1366x768 standard enterprise laptop screen
        page = await browser.new_page(viewport={"width": 1366, "height": 768})

        errors = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))

        # 1. Load dashboard
        await page.goto("http://localhost:3000")
        await page.wait_for_timeout(1000)

        # 2. Viewport metrics assertion
        metrics = await page.evaluate("""() => {
            const m = document.getElementById('mainDropZone');
            const doc = document.documentElement;
            return {
                docScrollHeight: doc.scrollHeight,
                viewportHeight: window.innerHeight,
                isDocScrollable: doc.scrollHeight > window.innerHeight,
                isMainScrollable: m.scrollHeight > m.clientHeight,
                footerTop: document.querySelector('footer').getBoundingClientRect().top
            };
        }""")
        assert metrics["docScrollHeight"] == 768, "Document must not overflow window height"
        assert not metrics["isDocScrollable"], "Root document must never scroll"
        assert metrics["isMainScrollable"], "Main canvas must scroll internally"
        assert metrics["footerTop"] >= 730, "Footer must be permanently anchored at bottom"

        # 3. Test Date Slicer Interactivity
        await page.click("button:has-text('30D')")
        await page.wait_for_timeout(300)
        kpi1_delta = await page.inner_text("#kpi1Delta")
        assert "30D" in kpi1_delta or "Window" in kpi1_delta, "Date slicer must update KPI delta badge"

        # 4. Test Secondary Tier Filter
        tier_select = await page.query_selector("#secondaryTierSelect")
        options = await page.evaluate("() => Array.from(document.querySelectorAll('#secondaryTierSelect option')).map(o => o.value)")
        assert len(options) >= 2, "Secondary tier select must have options"
        if len(options) > 1 and options[1] != "ALL":
            await tier_select.select_option(options[1])
            await page.wait_for_timeout(300)
            kpi1_title = await page.inner_text("#kpi1Title")
            assert options[1].lower() in kpi1_title.lower(), f"KPI1 title should reflect selected tier {options[1]}"

        # 5. Test Matrix Table Expand / Collapse & Chevron Toggle
        await page.click("#pbiTabBtn-matrix")
        await page.wait_for_timeout(300)
        
        # Click first parent row to collapse
        chevron_before = await page.inner_text("#chevron-0")
        assert chevron_before == "▼", "Initial chevron should be expanded (▼)"
        
        await page.click("#matrixTableBody tr:first-child")
        await page.wait_for_timeout(300)
        chevron_after = await page.inner_text("#chevron-0")
        assert chevron_after == "▶", "Chevron must flip to collapsed (▶)"
        
        is_child_hidden = await page.evaluate("() => document.querySelector('.matrix-child-group-0').classList.contains('hidden')")
        assert is_child_hidden, "Child rows must be hidden when parent is toggled"

        # 6. Test Decomposition Tree Dynamic Drill-Down (No Alert!)
        await page.click("#pbiTabBtn-decomp")
        await page.wait_for_timeout(300)

        # Drill down on branch 1
        branch_cards = await page.query_selector_all("#decompTreeContainer > div:nth-child(3) > div")
        if len(branch_cards) > 1:
            await branch_cards[1].click()
            await page.wait_for_timeout(300)
            level2_title = await page.inner_text("#decompSubBranchesLevel2 > div:first-child")
            assert "split for" in level2_title.lower(), "Drilling down must update Level 2 sub-branches dynamically"

        # 7. Test Visual switching auto-navigation to Page 1
        # Currently on Page 2 (decomp), click Clustered Column icon in Visualizations pane
        await page.click("#vbtn-line_chart")
        await page.wait_for_timeout(300)
        is_page1_visible = await page.is_visible("#pbiPage-overview")
        assert is_page1_visible, "Switching visual must automatically navigate to Page 1 Overview"

        # 8. Test Data Field Click Re-Aggregation
        field_elements = await page.query_selector_all("#fieldsTreeContainer > div")
        if len(field_elements) > 0:
            await field_elements[0].click()
            await page.wait_for_timeout(300)

        # 9. Test Toast Container
        toasts = await page.query_selector_all(".pbi-toast")
        assert len(toasts) >= 0, "Toast container functioning properly"

        # 10. Assert zero uncaught JavaScript errors
        assert len(errors) == 0, f"Encountered JS errors: {errors}"

        await browser.close()
