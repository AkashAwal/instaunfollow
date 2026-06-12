import os
import time
import random
import json
from instagrapi import Client
from instagrapi.exceptions import ClientError, LoginRequired, ChallengeRequired

USERNAME = os.environ["INSTAGRAM_USERNAME"]
PASSWORD = os.environ["INSTAGRAM_PASSWORD"]
SESSION_FILE = "session.json"
BATCH_SIZE = 100
MIN_DELAY = 5
MAX_DELAY = 15


def login():
    cl = Client()
    cl.delay_range = [1, 3]

    if os.path.exists(SESSION_FILE):
        try:
            cl.load_settings(SESSION_FILE)
            cl.login(USERNAME, PASSWORD)
            cl.get_timeline_feed()  # verify session is valid
            print("Resumed existing session.")
            return cl
        except (LoginRequired, Exception):
            print("Session expired, logging in fresh...")

    cl = Client()
    cl.delay_range = [1, 3]
    cl.login(USERNAME, PASSWORD)
    cl.dump_settings(SESSION_FILE)
    print("Logged in and session saved.")
    return cl


def main():
    try:
        cl = login()
    except ChallengeRequired:
        print("Instagram is asking for a challenge (e.g. email/SMS verify). Try logging in manually once from a browser first.")
        raise
    except Exception as e:
        print(f"Login failed: {e}")
        raise

    user_id = cl.user_id
    print("Fetching following list...")

    try:
        following = cl.user_following(user_id, amount=BATCH_SIZE + 20)
    except Exception as e:
        print(f"Failed to fetch following list: {e}")
        raise

    if not following:
        print("No one left to unfollow! You're done.")
        return

    batch = list(following.items())[:BATCH_SIZE]
    print(f"Fetched {len(following)} accounts. Unfollowing {len(batch)} this run...\n")

    unfollowed = 0
    for i, (uid, user_info) in enumerate(batch):
        try:
            cl.user_unfollow(uid)
            unfollowed += 1
            print(f"[{unfollowed}/{len(batch)}] Unfollowed @{user_info.username}")
        except ClientError as e:
            error_msg = str(e)
            if "feedback_required" in error_msg or "rate" in error_msg.lower():
                print(f"Rate limited by Instagram after {unfollowed} unfollows. Stopping early.")
                break
            print(f"  Skipping @{user_info.username}: {e}")

        if i < len(batch) - 1:
            delay = random.uniform(MIN_DELAY, MAX_DELAY)
            print(f"  Waiting {delay:.1f}s...")
            time.sleep(delay)

    cl.dump_settings(SESSION_FILE)
    print(f"\nRun complete. Unfollowed {unfollowed} accounts.")


if __name__ == "__main__":
    main()
