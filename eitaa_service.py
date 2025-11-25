# services/eitaa_service.py

import os
import time
from typing import List, Union
from config import config

USER_DATA_DIR = os.path.join(config.APP_DATA_PATH, "eitaa_session")

class EitaaService:
    def __init__(self, headless=False):
        from playwright.sync_api import sync_playwright
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch_persistent_context(
            USER_DATA_DIR, headless=True, slow_mo=100
        )
        self.page = self.browser.pages[0] if self.browser.pages else self.browser.new_page()
        self.page.goto("https://web.eitaa.com", timeout=90000)
        print("EitaaService: New instance created.")

    def _go_to_chat(self, contact_identifier: str):
        print(f"Navigating to chat with '{contact_identifier}'...")
        new_menu_selector = "#new-menu"
        self.page.wait_for_selector(new_menu_selector, timeout=20000)
        self.page.locator(new_menu_selector).click()

        new_chat_selector = "div.btn-menu-item.tgico-newprivate.rp"
        self.page.wait_for_selector(new_chat_selector, timeout=5000)
        self.page.locator(new_chat_selector).click()
        
        search_input_selector = "#contacts-container input.input-field-input.i18n.input-search-input"
        self.page.wait_for_selector(search_input_selector, timeout=5000)
        self.page.locator(search_input_selector).fill(contact_identifier)
        
        self.page.wait_for_timeout(1000)

        first_result_xpath = "(//ul[contains(@class, 'contacts-container')]/li)[1]"
        self.page.wait_for_selector(first_result_xpath, timeout=10000, state='attached')
        self.page.locator(first_result_xpath).click()
        print(f"Successfully entered chat with '{contact_identifier}'.")

    def _wait_for_message_sent(self):
        print("Waiting for send confirmation...")
        sending_bubble_selector = "div.bubble.is-sending"
        try:
            # سعی می‌کنه حباب "در حال ارسال" رو برای مدت کوتاهی ببینه
            # این حالت پیام‌هایی که کمی با تاخیر ارسال میشن رو پوشش میده
            self.page.wait_for_selector(sending_bubble_selector, state='visible', timeout=3000)
        except Exception:
            # اگر حباب دیده نشد (یعنی پیام خیلی سریع ارسال شده)، خطا رو نادیده می‌گیره
            print("Info: 'is-sending' bubble not detected or appeared briefly. Proceeding to confirmation.")
            pass

        # در نهایت، منتظر می‌مونه تا حباب "در حال ارسال" به طور کامل ناپدید بشه
        # این خط، ارسال موفق رو به طور قطعی تایید می‌کنه
        self.page.wait_for_selector(sending_bubble_selector, state='hidden', timeout=60000)
        print("Send confirmed.")

    def _send_text_message(self, message: str):
        if not message or not message.strip(): return
        print("Sending text message...")
        message_box_selector = 'div.input-message-input[data-placeholder="پیام"][dir="auto"]'
        self.page.locator(message_box_selector).fill(message)
        self.page.keyboard.press('Enter')
        self._wait_for_message_sent()

    def _send_media_files(self, file_paths: List[str]):
        """Helper method to upload and send files WITHOUT caption."""
        with self.page.expect_file_chooser() as fc_info:
            attach_button_selector = "div.btn-icon.btn-menu-toggle.attach-file.tgico-attach"
            self.page.locator(attach_button_selector).click()
            
            document_option_selector = "div.btn-menu-item.tgico-document.rp"
            self.page.locator(document_option_selector).click()

        file_chooser = fc_info.value
        file_chooser.set_files(file_paths)
        print(f"File(s) '{file_paths}' selected.")
        
        # --- START: THE FIX ---
        # به جای کلیک روی دکمه، از Enter استفاده می‌کنیم که قابل اعتمادتر است
        print("Sending file(s) by pressing Enter...")
        self.page.keyboard.press('Enter')
        # --- END: THE FIX ---
        
        self._wait_for_message_sent()

    def send_message(self, contact_identifier: str, message: str, attachment_paths: Union[str, List[str], None] = None) -> bool:
        """پیام متنی یا فایل را به مخاطب مشخص شده در ایتا ارسال می‌کند."""
        try:
            self._go_to_chat(contact_identifier)

            paths = []
            if isinstance(attachment_paths, str):
                paths = [attachment_paths]
            elif isinstance(attachment_paths, list):
                paths = attachment_paths
            
            if paths:
                print(f"Sending {len(paths)} file(s)...")
                self._send_media_files(paths)
                print("Files sent successfully.")

                if message and message.strip():
                    print("Sending caption as a separate message...")
                    self._send_text_message(message)
            else:
                self._send_text_message(message)

            return True
        except Exception as e:
            print(f"An error occurred during send_message for '{contact_identifier}': {e}")
            return False
        finally:
            print("State reset needed. Reloading page...")
            try:
                self.page.goto("https://web.eitaa.com", timeout=60000, wait_until='domcontentloaded')
                self.page.wait_for_selector("#new-menu", timeout=20000)
            except Exception as reload_e:
                print(f"Could not reload the page: {reload_e}")

    def send_file(self, contact_identifier: str, file_paths: Union[str, List[str]], caption: str = "") -> bool:
        # This method can now be a simple wrapper around send_message
        return self.send_message(contact_identifier, message=caption, attachment_paths=file_paths)

    def close(self):
        if self.browser: self.browser.close()
        if self.playwright: self.playwright.stop()
        print("EitaaService: Instance closed.")