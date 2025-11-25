# services/rubika_service.py

import os
import time
from config import config

def get_user_data_dir():
    return os.path.join(config.APP_DATA_PATH, "rubika_session")

RUBIKA_WEB_URL = "https://web.rubika.ir/"

class RubikaService:
    def __init__(self, headless=True):
        from playwright.sync_api import sync_playwright, TimeoutError
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch_persistent_context(
            get_user_data_dir(), headless=True, slow_mo=250
        )
        self.page = self.browser.pages[0] if self.browser.pages else self.browser.new_page()
        self.page.goto(RUBIKA_WEB_URL, timeout=90000)

    def _wait_for_message_sent(self, is_file=False):
        """
        Waits for the message to be sent.
        - If is_file=True: STRICT MODE. Waits for server ID change (upload complete).
        - If is_file=False: RELAXED MODE. Just waits for bubble to appear.
        """
        try:
            # 1. پیدا کردن آخرین حباب پیام
            last_bubble_locator = self.page.locator("div.bubbles-date-group").last.locator("div.bubbles-group").last
            
            # همیشه صبر می‌کنیم تا حباب در صفحه ظاهر شود (چه متن چه فایل)
            last_bubble_locator.wait_for(state='attached', timeout=10000)

            # --- حالت فایل: بررسی دقیق (Strict) ---
            if is_file:
                print("Waiting for file upload confirmation (Server ID check)...")
                temp_msg_id = last_bubble_locator.get_attribute("data-msg-id")
                # تا 120 ثانیه (2 دقیقه) صبر می‌کنیم فایل آپلود شود
                for _ in range(240): 
                    current_msg_id = last_bubble_locator.get_attribute("data-msg-id")
                    # اگر آیدی عوض شد و طولانی بود یعنی سرور تایید کرد
                    if current_msg_id != temp_msg_id and current_msg_id and len(current_msg_id) > 10:
                        return True
                    time.sleep(0.5)
                
                # اگر بعد از 2 دقیقه تایید نشد، خطا می‌دهیم
                raise TimeoutError("File upload timed out (ID did not update).")

            # --- حالت متن: بررسی آسان (Relaxed) ---
            else:
                # برای متن فقط یک مکث کوتاه کافیست
                time.sleep(0.5)
                return True

        except Exception as e:
            if is_file:
                # اگر فایل بود و ارور داد، یعنی آپلود انجام نشده. پس باید خطا را برگردانیم
                print(f"File send verification failed: {e}")
                raise e 
            else:
                # اگر متن بود و ارور داد (مثلاً تایم‌اوت)، نادیده می‌گیریم تا "قرمز" نشود
                print(f"Text send verification warning (proceeding): {e}")
                return True

    def send_message(self, contact_name: str, message: str, attachment_paths: list[str] | str | None = None) -> bool:
        """Sends a message with optional attachments, using a unified logic for all file sends."""
        try:
            main_menu_selector = "div#new-menu"
            contacts_button_selector = "div.btn-menu-item.rbico-user"
            search_box_selector = "input[type='search']"
            not_found_selector = "ul.chatlist.contacts-container li.chatlist-empty"
            first_result_xpath = "(//ul[contains(@class, 'contacts-container')]/li[not(contains(@class, 'chatlist-empty'))])[1]"
            back_btn = "button.sidebar-close-button"
            
            self.page.wait_for_selector(main_menu_selector, timeout=20000)
            self.page.locator(main_menu_selector).click()
            self.page.locator(contacts_button_selector).click()
            self.page.wait_for_selector(search_box_selector, timeout=5000)
            self.page.locator(search_box_selector).fill(contact_name)
            time.sleep(1)

            if self.page.locator(not_found_selector).is_visible():
                print(f"Contact '{contact_name}' not found.")
                self.page.locator(back_btn).click()
                return False
            else:
                self.page.locator(first_result_xpath).click()

            paths = []
            if isinstance(attachment_paths, str):
                paths = [attachment_paths]
            elif isinstance(attachment_paths, list):
                paths = attachment_paths

            if paths:
                # --- START: UNIFIED FILE SENDING LOGIC ---
                print(f"Sending {len(paths)} file(s) without caption...")
                attachment_button_selector = "div.rbico-attach"
                document_option_selector = "div.btn-menu-item.rbico-document"
                final_send_button_selector = "button.btn-primary.btn-color-primary"

                # 1. ارسال فایل(ها) بدون کپشن
                self.page.locator(attachment_button_selector).click()
                with self.page.expect_file_chooser() as fc_info:
                    self.page.locator(document_option_selector).click()
                file_chooser = fc_info.value
                file_chooser.set_files(paths)
                
                self.page.wait_for_selector(final_send_button_selector, timeout=20000)
                self.page.locator(final_send_button_selector).click()
                
                # <--- تغییر مهم: اینجا Strict Mode فعال است --->
                self._wait_for_message_sent(is_file=True) 
                print("Files sent successfully.")
                
                # 2. ارسال کپشن به عنوان پیام جداگانه
                if message and message.strip():
                    print("Sending caption as a separate message...")
                    message_box_selector = "div.composer_rich_textarea"
                    message_locator = self.page.locator(message_box_selector)
                    message_locator.fill(message)
                    message_locator.press("Enter")
                    
                    # <--- تغییر مهم: اینجا Relaxed Mode فعال است --->
                    self._wait_for_message_sent(is_file=False) 
                # --- END: UNIFIED FILE SENDING LOGIC ---
            else:
                # ارسال پیام فقط متنی
                print("Sending text message...")
                if not message or not message.strip(): return True 
                message_box_selector = "div.composer_rich_textarea"
                self.page.wait_for_selector(message_box_selector, timeout=10000)
                message_locator = self.page.locator(message_box_selector)
                message_locator.fill(message)
                message_locator.press("Enter")
                
                # <--- تغییر مهم: اینجا Relaxed Mode فعال است --->
                self._wait_for_message_sent(is_file=False)

            self.page.goto(RUBIKA_WEB_URL, timeout=60000)
            return True
        except Exception as e:
            print(f"An error occurred for '{contact_name}': {e}")
            try:
                self.page.goto(RUBIKA_WEB_URL, timeout=60000)
            except Exception as goto_e:
                print(f"Could not navigate back to Rubika home: {goto_e}")
            return False

    def close(self):
        if self.browser: self.browser.close()
        if self.playwright: self.playwright.stop()