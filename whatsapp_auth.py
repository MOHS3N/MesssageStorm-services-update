# services/whatsapp_auth.py

import os
import shutil
import json
import tempfile
from playwright.sync_api import sync_playwright, TimeoutError

class WhatsAppAuthService:
    def login(self, session_dir_path, status_callback=None):
        playwright = None
        browser = None
        temp_user_dir = tempfile.mkdtemp()
        profile_data = None
        
        try:
            playwright = sync_playwright().start()
            # واتساپ وب معمولاً نیاز به یوزر ایجنت واقعی دارد
            browser = playwright.chromium.launch_persistent_context(
                temp_user_dir,
                headless=False,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
            )

            if status_callback:
                status_callback()
            
            page = browser.pages[0] if browser.pages else browser.new_page()
            page.goto("https://web.whatsapp.com", timeout=90000)
            
            print("Waiting for WhatsApp login...")
            # سلکتور صفحه اصلی واتساپ بعد از لاگین
            page.wait_for_selector("div[contenteditable='true'][data-tab='3']", timeout=180000)
            print("WhatsApp login detected.")
            
            # --- استخراج پروفایل ---
            try:
                # کلیک روی عکس پروفایل
                logged_in_selector = 'div[aria-label="chat-list-filters"]'
                page.wait_for_selector(logged_in_selector, timeout=120000)
                profile_button_selector = 'button[aria-label="Profile"]'
                page.wait_for_selector(profile_button_selector, timeout=10000)
                page.locator(profile_button_selector).click()
                name_selector = "div._alcd span.selectable-text.copyable-text"
                page.wait_for_selector(name_selector, timeout=10000)
                account_name = page.locator(name_selector).first.inner_text()
                phone_selector = 'span[data-icon="phone"] + div span'
                page.wait_for_selector(phone_selector, timeout=5000)
                phone_number = page.locator(phone_selector).inner_text()
                profile_data = {'name': account_name, 'phone': phone_number}
            except Exception as e:
                print(f"Profile scrape error: {e}")
                profile_data = {"name": "کاربر واتساپ", "phone": "متصل شده"}

            browser.close()
            playwright.stop()
            
            if os.path.exists(session_dir_path):
                shutil.rmtree(session_dir_path)
            shutil.copytree(temp_user_dir, session_dir_path)
            
            return True, "لاگین واتساپ با موفقیت انجام شد.", profile_data

        except Exception as e:
            if browser: browser.close()
            if playwright: playwright.stop()
            return False, f"خطا در واتساپ: {str(e)}", None
        finally:
            if os.path.exists(temp_user_dir):
                shutil.rmtree(temp_user_dir, ignore_errors=True)