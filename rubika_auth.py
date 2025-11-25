# services/rubika_auth.py

import os
import shutil
import json
import tempfile
from playwright.sync_api import sync_playwright, TimeoutError

class RubikaAuthService:
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

            page = browser.pages[0] if browser.pages else browser.new_page()
            page.goto("https://web.rubika.ir/", timeout=90000)

            print("Waiting for Rubika login...")
            # سلکتور دقیق از کد قدیمی شما
            LOGGED_IN_SELECTOR = "sidebar-container[container-type='leftside']"
            page.wait_for_selector(LOGGED_IN_SELECTOR, timeout=180000)
            print("Rubika login detected.")

            # --- شروع اسکرپ هوشمند با سلکتورهای صحیح ---
            print("Scraping Rubika profile data...")
            try:
                # 1. باز کردن منو
                # استفاده از سلکتور دقیق قدیمی
                menu_btn = page.locator("div.btn-icon.btn-menu-toggle")
                menu_btn.wait_for(state="visible", timeout=5000)
                menu_btn.click()
                page.wait_for_timeout(1000) # صبر برای انیمیشن
                
                # 2. رفتن به تنظیمات (rbico)
                settings_selector = "div.rbico-settings"
                page.wait_for_selector(settings_selector, state="visible", timeout=5000)
                page.locator(settings_selector).click(force=True)
                
                # 3. انتظار هوشمند برای المنت شماره (rbico)
                phone_selector = "div.rbico-phone"
                print("Waiting for phone element...")
                page.wait_for_selector(phone_selector, timeout=15000)
                
                # 4. حلقه تلاش برای خواندن متن
                phone = ""
                for i in range(20): 
                    txt = page.locator(phone_selector).inner_text()
                    if txt and txt.strip():
                        phone = txt.strip()
                        print(f"Phone found: {phone}")
                        break
                    page.wait_for_timeout(500)
                
                if not phone:
                    print("Phone text was empty after retries.")
                    phone = "نامشخص"

                # 5. تلاش برای پیدا کردن نام (اول نام پروفایل، بعد یوزرنیم rbico)
                display_name = "کاربر روبیکا"
                try:
                    # تلاش اول: نام پروفایل (معمولاً کلاسش فرق نمیکنه ولی چک میکنیم)
                    name_locator = page.locator("div.profile-name")
                    if name_locator.count() > 0:
                        display_name = name_locator.first.inner_text()
                    else:
                        # تلاش دوم: استفاده از سلکتور یوزرنیم قدیمی (rbico)
                        username_selector = "div.rbico-username"
                        if page.locator(username_selector).is_visible(timeout=5000):
                            display_name = page.locator(username_selector).inner_text()
                        else:
                            display_name = phone
                except Exception:
                    pass
                
                if not display_name: display_name = "کاربر روبیکا"
                
                profile_data = {"name": display_name, "phone": phone}

            except Exception as e:
                print(f"Warning: Could not scrape Rubika profile fully: {e}")
                # پروفایل فال‌بک در صورت تغییر احتمالی کلاس‌ها در آینده
                profile_data = {"name": "کاربر روبیکا", "phone": "متصل شده"}

            # --- پایان اسکرپ ---

            # ذخیره کوکی‌ها
            cookies = page.context.cookies()
            with open(os.path.join(temp_user_dir, "cookies.json"), "w", encoding="utf-8") as f:
                json.dump(cookies, f)

            browser.close()
            playwright.stop()
            
            if os.path.exists(session_dir_path):
                shutil.rmtree(session_dir_path)
            shutil.copytree(temp_user_dir, session_dir_path)
            
            return True, "اتصال به روبیکا برقرار شد.", profile_data

        except Exception as e:
            if browser: browser.close()
            if playwright: playwright.stop()
            return False, f"خطا در روبیکا: {str(e)}", None
        finally:
            if os.path.exists(temp_user_dir):
                shutil.rmtree(temp_user_dir, ignore_errors=True)