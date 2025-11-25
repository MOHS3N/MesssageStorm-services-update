# services/bale_auth.py

import os
import shutil
import json
import tempfile
from playwright.sync_api import sync_playwright

class BaleAuthService:
    def login(self, session_dir_path, status_callback=None):
        playwright = None
        browser = None
        temp_user_dir = tempfile.mkdtemp()
        profile_data = None
        
        try:
            playwright = sync_playwright().start()
            browser = playwright.chromium.launch_persistent_context(
                temp_user_dir, headless=False, slow_mo=100
            )
            if status_callback:
                status_callback()
            
            page = browser.new_page()
            page.goto("https://web.bale.ai/", timeout=90000)

            avatar_selector = "div.MainBar-module__AvatarWrapper--PoFW1Z"
            page.wait_for_selector(avatar_selector, timeout=180000)
            
            # رفتن به پروفایل
            page.locator(avatar_selector).click()
            page.wait_for_url("**/profile", timeout=20000)

            # اسکرپ هوشمند
            user_info_selector = "div.UserGroupInfo-module__userInfoWrapper--unOuPx"
            user_info_locator = page.locator(user_info_selector)
            combined_text = ""
            for _ in range(20):
                combined_text = user_info_locator.text_content()
                if combined_text and combined_text.strip():
                    break
                page.wait_for_timeout(500)

            combined_text = combined_text.strip() if combined_text else ""
            
            if "|" in combined_text:
                parts = combined_text.split("|")
                profile_phone = parts[0].strip()
                profile_name = parts[1].strip()
            else:
                profile_phone = combined_text
                profile_name = "کاربر بله"

            profile_data = {"name": profile_name, "phone": profile_phone}

            # ذخیره کوکی هدلس
            cookies = page.context.cookies()
            with open(os.path.join(temp_user_dir, "cookies.json"), "w", encoding="utf-8") as f:
                json.dump(cookies, f)

            browser.close()
            playwright.stop()

            if os.path.exists(session_dir_path):
                shutil.rmtree(session_dir_path)
            shutil.copytree(temp_user_dir, session_dir_path)
            
            return True, "اتصال به بله برقرار شد.", profile_data

        except Exception as e:
            if browser: browser.close()
            if playwright: playwright.stop()
            return False, f"خطا بله: {str(e)}", None
        finally:
            if os.path.exists(temp_user_dir):
                shutil.rmtree(temp_user_dir, ignore_errors=True)