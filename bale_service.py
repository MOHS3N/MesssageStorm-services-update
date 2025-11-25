#test
import os
import time
import json
from config import config

def get_user_data_dir():
    return os.path.join(config.APP_DATA_PATH, "bale_session")

BALE_WEB_URL = "https://web.bale.ai/contacts"

class BaleService:
    def __init__(self, headless=True):
        from playwright.sync_api import sync_playwright, TimeoutError
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch_persistent_context(
            get_user_data_dir(),
            headless=True,  # حالا می‌تونه true باشه
            slow_mo=250,
        )

        # ✅ تلاش برای بازیابی سشن با کوکی‌ها
        cookies_path = os.path.join(get_user_data_dir(), "cookies.json")
        if os.path.exists(cookies_path):
            try:
                with open(cookies_path, "r", encoding="utf-8") as f:
                    cookies = json.load(f)
                self.browser.add_cookies(cookies)
            except Exception as e:
                print(f"Error loading cookies: {e}")

        self.page = self.browser.pages[0] if self.browser.pages else self.browser.new_page()
        self.page.goto(BALE_WEB_URL, timeout=90000)

    def send_message(self, contact_name: str, message: str, attachment_paths: list[str] | str | None = None) -> bool:
        """Sends a message with optional attachments, using a unified logic for all file sends."""
        try:
            open_search_button_xpath = '(//div[contains(@class, "RippleView-module__Wrapper--ZGzps0")])[1]'
            search_box_selector = "input.SearchBox-module__SearchInputbar--e8AzTv"
            first_result_xpath = '(//div[contains(@class, "DialogList-module__ContentWrapper--YgUC8J")])[1]'
            message_box_selector = "#editable-message-text[contenteditable='true'][style='direction: rtl;']"

            self.page.locator(open_search_button_xpath).click()
            self.page.locator(search_box_selector).fill(contact_name)
            self.page.keyboard.press("Enter")
            self.page.locator(first_result_xpath).click()

            paths = []
            if isinstance(attachment_paths, str):
                paths = [attachment_paths]
            elif isinstance(attachment_paths, list):
                paths = attachment_paths

            if paths:
                print(f"Sending {len(paths)} file(s) without caption...")
                attachment_button_selector = "div[data-sentry-element='IconButton'][data-sentry-source-file='Attachment.tsx']"
                file_option_locator = self.page.locator(
                    "p.Menu-module__Title--YPxpUY", has_text="فایل"
                ).locator("xpath=ancestor::li")
                send_button_selector = "button[aria-label='ارسال']"
                progress_bar_selector = "div.CircularProgress-module__CircularWrapper--MW8BSd"

                self.page.locator(attachment_button_selector).click()
                with self.page.expect_file_chooser() as fc_info:
                    file_option_locator.click()
                file_chooser = fc_info.value
                file_chooser.set_files(paths)
                self.page.locator(send_button_selector).click()

                self.page.wait_for_selector(progress_bar_selector, state="visible", timeout=10000)
                start_time = time.time()
                while self.page.locator(progress_bar_selector).count() > 0:
                    if time.time() - start_time > 120:
                        raise TimeoutError("Timed out waiting for all progress bars to disappear.")
                    time.sleep(0.5)
                print("Files sent successfully.")

                if message and message.strip():
                    print("Sending caption as a separate message...")
                    self.page.locator(message_box_selector).fill(message)
                    time.sleep(1)
                    self.page.keyboard.press("Enter")
                    time.sleep(2)
            else:
                if not message or not message.strip():
                    return True
                self.page.wait_for_selector(message_box_selector, timeout=10000)
                self.page.locator(message_box_selector).fill(message)
                time.sleep(1)
                self.page.keyboard.press("Enter")
                time.sleep(2)

            self.page.goto(BALE_WEB_URL, timeout=60000)
            return True
        except Exception as e:
            print(f"An error occurred for '{contact_name}': {e}")
            try:
                self.page.goto(BALE_WEB_URL, timeout=60000)
            except Exception as goto_e:
                print(f"Could not navigate back to Bale contacts: {goto_e}")
            return False

    def close(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
