import os
import time
import random
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

USERNAME = os.environ["INSTAGRAM_USERNAME"]
PASSWORD = os.environ["INSTAGRAM_PASSWORD"]

# Stored on the machine (not in repo) so it persists between runs
SESSION_FILE = Path.home() / ".instagram_session.json"

BATCH_SIZE = 100
MIN_DELAY = 8
MAX_DELAY = 18


def random_delay():
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))


def ensure_logged_in(page, context):
    page.goto("https://www.instagram.com/accounts/login/")
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    # Already logged in via saved session
    if "/accounts/login/" not in page.url:
        print("Session still valid — skipping login.")
        return

    # Dismiss cookie consent if present
    for text in ["Allow all cookies", "Accept All", "Allow essential and optional cookies"]:
        try:
            page.click(f'button:has-text("{text}")', timeout=3000)
            time.sleep(1)
            break
        except PlaywrightTimeout:
            pass

    print(">>> Please log in manually in the browser window. Take your time.")

    # Wait indefinitely for user to complete login (handles CAPTCHA, 2FA, etc.)
    print("Waiting for you to log in...")
    while True:
        url = page.url
        if "/accounts/login/" not in url and "/challenge/" not in url and "instagram.com" in url:
            print(f"Logged in! Current page: {url}")
            break
        time.sleep(2)

    # Dismiss popups after login
    for _ in range(2):
        try:
            page.click('button:has-text("Not Now")', timeout=4000)
            time.sleep(1)
        except PlaywrightTimeout:
            break

    # Save session so next run skips login
    context.storage_state(path=str(SESSION_FILE))
    print(f"Session saved to {SESSION_FILE}")


def unfollow_batch(page):
    print(f"Opening following list for @{USERNAME}...")
    page.goto(f"https://www.instagram.com/{USERNAME}/following/")
    page.wait_for_load_state("networkidle")
    time.sleep(3)

    unfollowed = 0
    stall_count = 0

    while unfollowed < BATCH_SIZE:
        buttons = page.query_selector_all('button:has-text("Following")')

        if not buttons:
            stall_count += 1
            if stall_count > 5:
                print("No more Following buttons after scrolling. Done.")
                break
            page.evaluate("window.scrollBy(0, 500)")
            time.sleep(2)
            continue

        stall_count = 0
        btn = buttons[0]

        try:
            btn.scroll_into_view_if_needed()
            time.sleep(0.5)
            btn.click()

            page.click('button:has-text("Unfollow")', timeout=5000)
            unfollowed += 1
            print(f"[{unfollowed}/{BATCH_SIZE}] Unfollowed")
            random_delay()
        except PlaywrightTimeout:
            # Dialog didn't appear — scroll and try next
            page.evaluate("window.scrollBy(0, 200)")
            time.sleep(1)
        except Exception as e:
            print(f"  Error: {e}")
            time.sleep(2)

    print(f"\nRun complete. Unfollowed {unfollowed} accounts this run.")


def main():
    storage = str(SESSION_FILE) if SESSION_FILE.exists() else None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            storage_state=storage,
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        ensure_logged_in(page, context)
        unfollow_batch(page)

        # Save updated session after each run
        context.storage_state(path=str(SESSION_FILE))
        browser.close()


if __name__ == "__main__":
    main()
