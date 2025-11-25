# services/rubika_adder_service.py

import time
import random
import os
from config import config

def get_user_data_dir():
    return os.path.join(config.APP_DATA_PATH, "rubika_session")

RUBIKA_WEB_URL = "https://web.rubika.ir"

class RubikaAdderService:
    def __init__(self, headless=True):
        from playwright.sync_api import sync_playwright
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch_persistent_context(
            get_user_data_dir(), headless=headless, slow_mo=250
        )
        self.page = self.browser.pages[0] if self.browser.pages else self.browser.new_page()

    def _add_single_contact(self, name: str, phone: str):
        name_input_selector = 'input[name="first_name"]'
        phone_input_selector = 'input[name="phone"][type="tel"]'
        save_button_selector = "div.popup-header button.btn-primary.btn-color-primary.rp"
        self.page.wait_for_selector(name_input_selector, timeout=5000)
        time.sleep(1)
        self.page.locator(name_input_selector).fill(name)
        self.page.locator(phone_input_selector).fill(phone)
        self.page.locator(save_button_selector).click()

    def run(self, contacts_to_add: list[dict], progress_callback=None):
        try:
            if progress_callback and len(contacts_to_add) > 0:
                progress_callback(0, "processing", "در حال بارگذاری روبیکا...")

            total = len(contacts_to_add)
            successful_adds = 0
            
            self.page.goto(RUBIKA_WEB_URL, timeout=90000)
            
            for i, contact in enumerate(contacts_to_add):
                if progress_callback:
                    progress_callback(i, "processing", f"در حال افزودن {contact.get('name')}...")

                try:
                    main_menu_selector = "div.sidebar-header__btn-container"
                    new_contact_option_selector = "div.btn-menu-item.rbico-user"
                    add_contact_button_selector = "button.btn-circle"
                    form_ready_selector = 'input[name="first_name"]'
                    
                    # سلکتور خطای "کاربر یافت نشد" (پاپ‌آپ)
                    error_popup_selector = "div.popup.popup-peer.popup-error.active"
                    
                    # +++ سلکتور خطای "شماره نادرست" (متن داخل فرم) +++
                    invalid_number_selector = "span[rb-localize='login_incorrect_number']"

                    # اطمینان از بسته بودن فرم‌های قبلی
                    if not self.page.locator(main_menu_selector).is_visible():
                        self.page.keyboard.press("Escape")
                        time.sleep(0.5)
                        if not self.page.locator(main_menu_selector).is_visible():
                             self.page.goto(RUBIKA_WEB_URL, timeout=90000)

                    self.page.wait_for_selector(main_menu_selector, timeout=20000)
                    self.page.locator(main_menu_selector).click()
                    self.page.wait_for_selector(new_contact_option_selector, timeout=5000)
                    self.page.locator(new_contact_option_selector).click()
                    self.page.wait_for_selector(add_contact_button_selector, timeout=10000)
                    self.page.locator(add_contact_button_selector).click()
                    self.page.wait_for_selector(form_ready_selector, timeout=5000)
                    
                    self._add_single_contact(contact.get('name', ''), contact.get('phone', ''))
                    
                    time.sleep(2)
                    
                    # +++ بررسی خطاها +++
                    
                    # ۱. بررسی خطای فرمت شماره (شماره نادرست)
                    if self.page.locator(invalid_number_selector).is_visible():
                        # چون ارور داخل فرم است، باید فرم را با Escape ببندیم
                        try: self.page.keyboard.press("Escape")
                        except: pass
                        
                        if progress_callback:
                            progress_callback(i, "failure", "شماره نادرست است") # قرمز

                    # ۲. بررسی خطای وجود نداشتن کاربر (پاپ‌آپ)
                    elif self.page.locator(error_popup_selector).is_visible():
                        # بستن پاپ‌آپ ارور
                        try:
                             close_btn = self.page.locator("div.popup-header .btn-icon.rbico-close")
                             if close_btn.is_visible(): close_btn.click()
                             else: self.page.keyboard.press("Escape")
                        except: pass
                        
                        time.sleep(0.5)
                        # بستن خود فرم افزودن مخاطب
                        try: self.page.keyboard.press("Escape")
                        except: pass

                        if progress_callback:
                            progress_callback(i, "failure", "کاربر یافت نشد") # قرمز
                    
                    # ۳. موفقیت
                    else:
                        successful_adds += 1
                        if progress_callback:
                            progress_callback(i, "success", "مخاطب افزوده شد") # سبز

                except Exception as inner_e:
                    if progress_callback:
                        progress_callback(i, "failure", str(inner_e))
                    try: self.page.goto(RUBIKA_WEB_URL)
                    except: pass

            return True, f"عملیات تمام شد. {successful_adds} از {total} مخاطب افزوده شدند."
        except Exception as e:
            return False, f"خطا: {e}"
        
    def close(self):
        if self.browser: self.browser.close()
        if self.playwright: self.playwright.stop()