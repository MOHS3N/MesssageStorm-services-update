# services/eitaa_auth.py

import os
import shutil
import json
import tempfile
from playwright.sync_api import sync_playwright, TimeoutError

class EitaaAuthService:
    def login(self, session_dir_path, status_callback=None):
        playwright = None
        browser = None
        temp_user_dir = tempfile.mkdtemp()
        profile_data = None
        
        try:
            playwright = sync_playwright().start()
            browser = playwright.chromium.launch_persistent_context(
                temp_user_dir, headless=False, slow_mo=50
            )
            if status_callback:
                status_callback()
            
            page = browser.pages[0] if browser.pages else browser.new_page()
            page.goto("https://web.eitaa.com", timeout=90000)
            
            # لاگین دتکشن
            print("Waiting for Eitaa Login...")
            page.wait_for_selector("div.tabs-tab.sidebar-slider-item.item-main.active", timeout=180000)
            
            # --- شروع اسکرپ اطلاعات ---
            print("Scraping Eitaa profile data...")
            try:
                # 1. باز کردن منو
                page.locator("div.btn-icon.btn-menu-toggle").click()
                # کمی صبر برای باز شدن انیمیشن منو
                page.wait_for_timeout(1000) 
                
                # 2. کلیک روی تنظیمات (با فورس کلیک که اگر انیمیشن گیر کرد هم کلیک شود)
                settings_btn = page.locator("div.btn-menu-item.tgico-settings")
                settings_btn.wait_for(state="visible", timeout=1000)
                settings_btn.click(force=True)
                
                # 3. انتظار هوشمند برای شماره تلفن (با زمان بیشتر: 15 ثانیه)
                phone_selector = "div.row-title.tgico-phone"
                print("Waiting for phone element...")
                
                # اینجا منتظر می‌مانیم تا المنت حتماً در صفحه "وجود" داشته باشد
                page.wait_for_selector(phone_selector, timeout=25000)
                
                # 4. حلقه تلاش برای خواندن متن (چون ممکن است المنت باشد ولی متنش هنوز لود نشده باشد)
                phone = ""
                for i in range(20): # 20 بار تلاش (حدود 10 ثانیه)
                    txt = page.locator(phone_selector).inner_text()
                    if txt and txt.strip():
                        phone = txt.strip()
                        break
                    page.wait_for_timeout(500)
                
                print(f"PHONE FOUND: {phone}")
                
                if not phone:
                    phone = "نامشخص"

                # 5. تلاش برای نام کاربری (اختیاری)
                display_name = "کاربر ایتا"
                try:
                    username_selector = "div.row-title.tgico-username"
                    if page.locator(username_selector).is_visible(timeout=3000):
                        display_name = page.locator(username_selector).inner_text()
                    else:
                        display_name = phone
                except:
                    display_name = phone

            except Exception as e:
                print(f"Error during scraping: {e}")
                # اگر به هر دلیلی (مثل تایم‌اوت) نتوانست بخواند، لاگین را خراب نمی‌کنیم
                # یک پروفایل موقت می‌سازیم تا کاربر وارد شود
                phone = "متصل شده"
                display_name = "کاربر ایتا"
            
            # --------------------------

            profile_data = {'name': display_name, 'phone': phone}
            
            browser.close()
            playwright.stop()
            
            if os.path.exists(session_dir_path):
                shutil.rmtree(session_dir_path)
            shutil.copytree(temp_user_dir, session_dir_path)
            
            return True, "اتصال به ایتا برقرار شد.", profile_data

        except Exception as e:
            if browser: browser.close()
            if playwright: playwright.stop()
            return False, f"خطا: {str(e)}", None
        finally:
            if os.path.exists(temp_user_dir):
                shutil.rmtree(temp_user_dir, ignore_errors=True)