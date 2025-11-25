# services/whatsapp_service.py

import os
import time
from config import config

def get_user_data_dir():
    return os.path.join(config.APP_DATA_PATH, "whatsapp_session")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/5.37.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/5.37.36"

class WhatsAppService:
    def __init__(self, headless=True):
        from playwright.sync_api import sync_playwright
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch_persistent_context(
            get_user_data_dir(),
            headless=True,
            user_agent=USER_AGENT,
            slow_mo=50,
            args=["--start-maximized"],
            no_viewport=True
        )
        self.page = self.browser.pages[0] if self.browser.pages else self.browser.new_page()

    def _wait_for_main_page(self):
        """Ensures the main WhatsApp page is loaded before proceeding."""
        if "web.whatsapp.com" in self.page.url and self.page.locator('div[aria-label="chat-list-filters"]').is_visible():
            return
        self.page.goto("https://web.whatsapp.com", wait_until="domcontentloaded", timeout=90000)
        self.page.wait_for_selector('div[aria-label="chat-list-filters"]', timeout=120000)

    def _wait_for_message_sent(self):
        """Waits for the 'sending' clock icon to disappear from the last message."""
        print("Waiting for send confirmation (clock icon to disappear)...")
        sending_clock_selector = "div[role='row']:last-child span[data-icon='msg-time']"
        self.page.wait_for_selector(sending_clock_selector, state='visible', timeout=10000)
        print(" - Sending clock appeared.")
        self.page.wait_for_selector(sending_clock_selector, state='hidden', timeout=60000)
        print(" - Sending clock disappeared. Send confirmed.")

    def send_message(self, phone_number: str, message: str, attachment_paths: list[str] | str | None = None) -> bool:
        """Sends a message with optional attachments, using a unified logic for all file sends."""
        try:
            self._wait_for_main_page()
            url = f"https://web.whatsapp.com/send?phone={phone_number}"
            self.page.goto(url, wait_until="load", timeout=60000)

            # تعریف سلکتورها در ابتدای متد
            message_box_selector = 'div[aria-placeholder="Type a message"]'

            paths = []
            if isinstance(attachment_paths, str):
                paths = [attachment_paths]
            elif isinstance(attachment_paths, list):
                paths = attachment_paths

            # --- START: UNIFIED SENDING LOGIC ---
            # اگر فایلی وجود داشت (چه یکی چه چندتا)، این منطق اجرا می‌شود
            if paths:
                print(f"Sending {len(paths)} file(s) without caption...")
                attach_button_selector = 'span[data-icon="plus-rounded"]'
                file_input_selector = 'input[type="file"][accept="*"]'
                send_button_selector = 'div[role="button"][aria-label="Send"]'
                
                # 1. ارسال فایل(ها) بدون کپشن
                self.page.locator(attach_button_selector).click()
                self.page.locator(file_input_selector).set_input_files(paths)
                self.page.locator(send_button_selector).click()
                self._wait_for_message_sent()
                print("File(s) sent successfully.")
                
                # 2. ارسال کپشن به عنوان پیام جداگانه (اگر وجود داشت)
                if message and message.strip():
                    print("Sending caption as a separate message...")
                    self.page.locator(message_box_selector).fill(message)
                    self.page.keyboard.press('Enter')
                    self._wait_for_message_sent()
            
            # اگر هیچ فایلی وجود نداشت، فقط پیام متنی ارسال می‌شود
            else:
                if not message or not message.strip(): return True
                self.page.wait_for_selector(message_box_selector, timeout=30000)
                self.page.locator(message_box_selector).fill(message)
                self.page.keyboard.press('Enter')
                self._wait_for_message_sent()
            # --- END: UNIFIED SENDING LOGIC ---
            
            return True
        except Exception as e:
            print(f"An error occurred during send_message for {phone_number}: {e}")
            return False

    def close(self):
        if self.browser: self.browser.close()
        if self.playwright: self.playwright.stop()