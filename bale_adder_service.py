# services/bale_adder_service.py

import time
import random
import os
from config import config

def get_user_data_dir():
    return os.path.join(config.APP_DATA_PATH, "bale_session")

class BaleAdderService:
    def __init__(self, headless=True):
        from playwright.sync_api import sync_playwright, Page, TimeoutError
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch_persistent_context(
            get_user_data_dir(), headless=headless, slow_mo=150
        )
        self.page = self.browser.pages[0] if self.browser.pages else self.browser.new_page()

    def _add_single_contact(self, name: str, phone: str):
        name_selector = 'input[aria-label="نام"]'
        phone_selector = 'input[aria-label="شماره همراه"]'
        save_button_selector = "button[aria-label='افزودن']"
        
        # حذف پیش‌شماره ۹۸ اگر وجود داشته باشد
        phone_to_enter = phone[2:] if phone.startswith('98') else phone
        
        self.page.wait_for_selector(name_selector, timeout=5000)
        self.page.locator(name_selector).fill(name)
        self.page.locator(phone_selector).fill(phone_to_enter)
        self.page.locator(save_button_selector).click()

    def run(self, contacts_to_add: list[dict], progress_callback=None):
        try:
            if progress_callback and len(contacts_to_add) > 0:
                progress_callback(0, "processing", "در حال بارگذاری بله...")
            
            # آدرس وب‌اپلیکیشن بله
            BALE_WEB_URL = "https://web.bale.ai"
            
            # بارگذاری اولیه
            self.page.goto(BALE_WEB_URL, timeout=90000)
            
            total = len(contacts_to_add)
            successful_adds = 0
            
            for i, contact in enumerate(contacts_to_add):
                
                # +++ منطق رفرش اجباری (بجز نفر اول) +++
                if i > 0:
                    if progress_callback:
                        progress_callback(i, "processing", "در حال رفرش صفحه...")
                    try:
                        self.page.goto(BALE_WEB_URL, timeout=60000)
                    except Exception as e:
                        print(f"Refresh failed: {e}")

                if progress_callback:
                    progress_callback(i, "processing", f"در حال افزودن {contact.get('name')}...")

                try:
                    # سلکتورهای منو و دکمه‌ها
                    contacts_menu_selector = "div.Navigation-module__NavItem--mROrNt[style='order: 5;']"
                    add_contact_button_selector = "div[title='افزودن مخاطب']"
                    form_ready_selector = 'input[aria-label="نام"]'
                    
                    # سلکتورهای پیام‌های نتیجه (Toast)
                    success_toast_selector = "div.Toastify__toast-body:has-text('مخاطب مورد نظر به مخاطبین اضافه شد.')"
                    not_found_toast_selector = "div.Toastify__toast-body:has-text('مخاطب مورد نظر در «بله» حساب کاربری ندارد.')"
                    
                    # سلکتور کلی برای هر ارور دیگری (مثل فرمت اشتباه شماره)
                    # در بله کلاس Toastify__toast--error معمولا برای خطاهاست
                    any_error_toast_selector = "div.Toastify__toast--error"

                    # 1. ورود به منوی مخاطبین (چون صفحه رفرش شده، هر بار باید انجام شود)
                    self.page.wait_for_selector(contacts_menu_selector, timeout=30000)
                    self.page.locator(contacts_menu_selector).click()
                    
                    # 2. زدن دکمه افزودن مخاطب
                    self.page.wait_for_selector(add_contact_button_selector, timeout=10000)
                    self.page.locator(add_contact_button_selector).click()
                    
                    # 3. پر کردن فرم
                    self.page.wait_for_selector(form_ready_selector, timeout=5000)
                    self._add_single_contact(contact.get('name', ''), contact.get('phone', ''))
                    
                    # انتظار برای بسته شدن فرم (نشانه ارسال درخواست)
                    try:
                        self.page.wait_for_selector(form_ready_selector, state='hidden', timeout=5000)
                    except:
                        pass # اگر فرم بسته نشد، احتمالا ارور اعتبار سنجی داریم که پایین‌تر چک می‌کنیم

                    # 4. بررسی نتیجه (Toastها)
                    status_determined = False
                    is_success = False
                    error_message = "خطای نامشخص"

                    # حلقه انتظار برای ظاهر شدن پیام (تا ۳ ثانیه)
                    for _ in range(6):
                        # اگر موفق بود
                        if self.page.locator(success_toast_selector).is_visible():
                            successful_adds += 1
                            status_determined = True
                            is_success = True
                            break
                        
                        # اگر کاربر یافت نشد
                        if self.page.locator(not_found_toast_selector).is_visible():
                            status_determined = True
                            is_success = False
                            error_message = "کاربر یافت نشد"
                            break
                        
                        # اگر هر ارور دیگری داد (مثل فرمت شماره اشتباه)
                        if self.page.locator(any_error_toast_selector).is_visible():
                            status_determined = True
                            is_success = False
                            # سعی می‌کنیم متن ارور را بخوانیم
                            try:
                                error_text = self.page.locator(any_error_toast_selector).text_content()
                                error_message = error_text if error_text else "شماره نادرست است"
                            except:
                                error_message = "شماره نادرست است"
                            break
                            
                        time.sleep(0.5)
                    
                    # اگر هیچ پیامی نیامد، فرض بر موفقیت می‌گیریم (یا می‌توان سخت‌گیرتر بود)
                    if not status_determined:
                        # چک نهایی: اگر هنوز فرم باز است یعنی گیر کرده
                        if self.page.locator(form_ready_selector).is_visible():
                             is_success = False
                             error_message = "عدم پاسخ سرور (تایم‌اوت)"
                        else:
                             successful_adds += 1
                             is_success = True

                    # 5. گزارش وضعیت نهایی به UI
                    if progress_callback:
                        if is_success:
                            progress_callback(i, "success", "مخاطب افزوده شد") # سبز
                        else:
                            progress_callback(i, "failure", error_message) # قرمز
                            
                except Exception as inner_e:
                    if progress_callback:
                        progress_callback(i, "failure", f"خطا: {str(inner_e)[:30]}")

                time.sleep(1)

            return True, f"عملیات تمام شد. {successful_adds} از {total} مخاطب افزوده شدند."
        except Exception as e:
            return False, f"خطا: {e}"
        
    def close(self):
        if self.browser: self.browser.close()
        if self.playwright: self.playwright.stop()