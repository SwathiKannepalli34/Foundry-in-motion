"""Smoke test for dist/foundry-in-motion.html (scratch tool; run with the repo venv)."""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
PAGE = (ROOT / "dist" / "foundry-in-motion.html").as_uri()
SHOTS = ROOT / "shots"
SHOTS.mkdir(exist_ok=True)
report = {"errors": [], "checks": {}}

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.on("pageerror", lambda e: report["errors"].append("pageerror: " + str(e)))
    pg.on("console", lambda m: report["errors"].append("console: " + m.text) if m.type == "error" else None)
    pg.goto(PAGE)
    pg.wait_for_timeout(800)

    report["checks"]["sections"] = pg.locator("main .sec").count()
    report["checks"]["nav_links"] = pg.locator("#nav a").count()
    report["checks"]["ref_links"] = pg.locator("a.ref").count()
    pg.screenshot(path=str(SHOTS / "01-hero.png"))

    # motion toggle
    pg.click("#motionBtn")
    report["checks"]["motion_off_attr"] = pg.evaluate("document.documentElement.getAttribute('data-motion')")
    report["checks"]["motion_off_anim"] = pg.evaluate(
        "getComputedStyle(document.querySelector('svg .flow')).animationName")
    pg.click("#motionBtn")
    report["checks"]["motion_on_attr"] = pg.evaluate("document.documentElement.getAttribute('data-motion')")
    report["checks"]["motion_persisted"] = pg.evaluate("localStorage.getItem('fim-motion')")

    # theme toggle
    pg.click("#themeBtn")
    report["checks"]["theme_light"] = pg.evaluate("document.documentElement.getAttribute('data-theme')")
    pg.click("#themeBtn")

    # portal explorer
    pg.locator("#portal").scroll_into_view_if_needed()
    pg.wait_for_timeout(500)
    pg.click(".p-tab[data-k='Operate']")
    pg.click(".p-item:has-text('Compliance')")
    report["checks"]["portal_text"] = pg.inner_text("#portalExplorer .p-main h3")
    pg.click(".p-tab[data-k='Build']")
    report["checks"]["portal_build_items"] = pg.locator("#portalExplorer .p-item").count()
    pg.locator("#portalExplorer").screenshot(path=str(SHOTS / "02-portal.png"))

    # deployment chooser
    pg.locator("#deployChooser").scroll_into_view_if_needed()
    pg.click("#deployChooser .choice button:nth-child(4)")
    report["checks"]["chooser"] = pg.inner_text("#deployChooser .result b.big")

    # tabs
    pg.locator("#project").scroll_into_view_if_needed()
    pg.click("#project .tablist button:nth-child(2)")
    report["checks"]["project_tab_visible"] = pg.locator("#project .tabpanel:not([hidden])").inner_text()[:60].replace("\n", " ")

    # token calc
    pg.locator("#tokenCalc").scroll_into_view_if_needed()
    pg.fill("#tc-req", "10000")
    report["checks"]["token_total"] = pg.inner_text("#tc-total")
    pg.locator("#tokenCalc").screenshot(path=str(SHOTS / "03-tokencalc.png"))

    # ccu calc (tab 3)
    pg.locator("#claude").scroll_into_view_if_needed()
    pg.click("#claude .tablist button:nth-child(3)")
    report["checks"]["ccu_base"] = pg.inner_text("#cc-base")
    report["checks"]["ccu_save"] = pg.inner_text("#cc-save")
    pg.locator("#ccuCalc").screenshot(path=str(SHOTS / "04-ccu.png"))

    # hosted agent states
    pg.locator("#hosted").scroll_into_view_if_needed()
    pg.click("#hosted .tablist button:nth-child(2)")
    pg.click("#sessionStates .state:nth-child(2)")
    report["checks"]["state_on"] = pg.locator("#sessionStates .state.on > b").inner_text()
    pg.locator("#hosted").screenshot(path=str(SHOTS / "05-hosted.png"))

    # new sections: what's new + privacy
    pg.locator("#whats-new").scroll_into_view_if_needed()
    report["checks"]["readiness_rows"] = pg.locator("#whats-new .tbl tbody tr").count()
    report["checks"]["eyebrow_numbers"] = pg.evaluate(
        "[...document.querySelectorAll('main .sec')].map(s => { const e = s.querySelector('.sec-head .eyebrow'); return e ? e.textContent.trim().slice(0,2) : '--'; }).join(',')")
    pg.locator("#privacy").scroll_into_view_if_needed()
    pg.wait_for_timeout(400)
    privacy_tabs = pg.locator("#privacy .tablist button")
    report["checks"]["privacy_tabs"] = privacy_tabs.count()
    for i in range(privacy_tabs.count()):
        privacy_tabs.nth(i).click()
        report["checks"].setdefault("privacy_tab_text", []).append(
            pg.locator("#privacy .tabpanel:not([hidden])").inner_text()[:40].replace("\n", " "))
    privacy_tabs.nth(4).click()
    pg.locator("#privacy").screenshot(path=str(SHOTS / "07-privacy.png"))
    pg.locator("#whats-new").screenshot(path=str(SHOTS / "08-whatsnew.png"))

    # expand all
    pg.click("#expandAll")

    # scrollspy at the bottom
    pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    pg.wait_for_timeout(300)
    report["checks"]["crumb_bottom"] = pg.inner_text("#crumb")
    report["checks"]["progress"] = pg.evaluate("document.querySelector('#progress').style.width")

    # each section screenshot (first viewport) for visual review
    for sid in ["gateway", "guardrails", "governance"]:
        pg.evaluate(f"document.getElementById('{sid}').scrollIntoView()")
        pg.wait_for_timeout(700)
        pg.screenshot(path=str(SHOTS / f"sec-{sid}.png"))

    # mobile
    m = b.new_page(viewport={"width": 390, "height": 800})
    m.on("pageerror", lambda e: report["errors"].append("mobile pageerror: " + str(e)))
    m.goto(PAGE)
    m.wait_for_timeout(600)
    m.click("#burger")
    report["checks"]["mobile_nav_open"] = m.evaluate("document.getElementById('side').classList.contains('open')")
    m.screenshot(path=str(SHOTS / "06-mobile.png"))
    report["checks"]["mobile_hscroll"] = m.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
    b.close()

print(json.dumps(report, indent=2))
sys.exit(1 if report["errors"] else 0)
