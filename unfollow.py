import os
import time
import random
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

USERNAME = os.environ["INSTAGRAM_USERNAME"]
PASSWORD = os.environ["INSTAGRAM_PASSWORD"]
BATCH_SIZE = 100
MIN_DELAY = 8
MAX_DELAY = 18


def random_delay():
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))


def login(page):
    print("Navigating to Instagram...")
    page.goto("https://www.instagram.com/accounts/login/")
    page.wait_for_load_state("networkidle")

    page.fill('input[name="username"]', USERNAME)
    time.sleep(random.uniform(0.5, 1.5))
    page.fill('input[name="password"]', PASSWORD)
    time.sleep(random.uniform(0.5, 1.5))
    page.click('button[type="submit"]')

    try:
        page.wait_for_url("**/instagram.com/**", timeout=15000)
        # Dismiss "Save your login info?" popup if it appears
        try:
            page.click('button:has-text("Not Now")', timeout=5000)
        except PlaywrightTimeout:
            pass
        # Dismiss notifications popup if it appears
        try:
            page.click('button:has-text("Not Now")', timeout=5000)
        except PlaywrightTimeout:
            pass
        print("Logged in.")
    except PlaywrightTimeout:
        page.screenshot(path="login_failed.png")
        raise Exception("Login timed out — check login_failed.png for what happened")


def unfollow_batch(page):
    print(f"Opening following list for @{USERNAME}...")
    page.goto(f"https://www.instagram.com/{USERNAME}/following/")
    page.wait_for_load_state("networkidle")
    time.sleep(3)

    unfollowed = 0
    seen_usernames = set()

    while unfollowed < BATCH_SIZE:
        # Find all Following buttons currently visible
        buttons = page.query_selector_all('button:has-text("Following")')

        if not buttons:
            print("No more Following buttons found.")
            break

        # Pick the first button we haven't tried yet
        clicked = False
        for btn in buttons:
            try:
                label = btn.evaluate("el => el.closest('[role]')?.querySelector('span')?.textContent || ''")
                if label in seen_usernames:
                    continue

                btn.scroll_into_view_if_needed()
                time.sleep(0.5)
                btn.click()

                # Confirm unfollow in the dialog
                try:
                    page.click('button:has-text("Unfollow")', timeout=5000)
                    unfollowed += 1
                    print(f"[{unfollowed}/{BATCH_SIZE}] Unfollowed")
                    seen_usernames.add(label)
                    clicked = True
                    random_delay()
                    break
                except PlaywrightTimeout:
                    # Dialog didn't appear, skip
                    seen_usernames.add(label)
                    break
            except Exception as e:
                print(f"  Skipping button: {e}")
                continue

        if not clicked:
            # Scroll down to load more
            page.evaluate("window.scrollBy(0, 400)")
            time.sleep(2)

    print(f"\nRun complete. Unfollowed {unfollowed} accounts.")
    return unfollowed


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # visible so Instagram trusts it more
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        login(page)
        unfollow_batch(page)

        browser.close()


if __name__ == "__main__":
    main()
