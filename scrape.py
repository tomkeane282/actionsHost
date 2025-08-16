# scrape.py
# - Navigates to TARGET_URL
# - Collects innerHTML of all matching divs
# - Writes them to a Google Sheet (one cell per div)

import os, json
from playwright.sync_api import sync_playwright
import gspread
from google.oauth2.service_account import Credentials

TARGET_URL = os.environ.get("TARGET_URL", "https://example.com")  # <-- put your URL in repo secret later
SHEET_ID = os.environ["SHEET_ID"]
SHEET_TAB = os.environ.get("SHEET_TAB", "Scrapes")

# CSS selector that matches exactly your target:
# <div class="wp-block-column is-layout-flow wp-block-column-is-layout-flow" style="flex-basis:66.66%">
# We match both classes AND the style containing flex-basis 66.66%.
SELECTOR = (
    'div.wp-block-column.is-layout-flow.wp-block-column-is-layout-flow'
    '[style*="flex-basis"][style*="66.66%"]'
)

def fetch_div_inner_htmls(url: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        # If content loads a bit later, wait for selector (won't error if absent)
        try:
            page.wait_for_selector(SELECTOR, timeout=10000)
        except Exception:
            pass
        # Grab innerHTML of each matched element in one go
        html_list = page.eval_on_selector_all(SELECTOR, "els => els.map(el => el.innerHTML)")
        browser.close()
        return html_list

def write_to_sheet(html_list):
    # Auth with a Google service account passed as JSON string in env var
    creds_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
    gc = gspread.authorize(creds)

    sh = gc.open_by_key(SHEET_ID)
    try:
        ws = sh.worksheet(SHEET_TAB)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=SHEET_TAB, rows=1000, cols=2)

    # Clear the sheet and write one HTML snippet per row in column A
    ws.clear()
    if html_list:
        ws.update("A1", [[h] for h in html_list], value_input_option="RAW")
    else:
        ws.update("A1", [["NO MATCHES FOUND"]], value_input_option="RAW")

def main():
    htmls = fetch_div_inner_htmls(TARGET_URL)
    write_to_sheet(htmls)
    print(f"Wrote {len(htmls)} cell(s) to Google Sheets.")

if __name__ == "__main__":
    main()
