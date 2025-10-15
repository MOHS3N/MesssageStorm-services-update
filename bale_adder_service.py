# services/bale_adder_service.py

import time
import random
import os
from config import config

def get_user_data_dir():
    return os.path.join(config.APP_DATA_PATH, "bale_session")

class BaleAdderService:
    def __init__(self, headless=False):
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
        phone_to_enter = phone[2:] if phone.startswith('98') else phone
        self.page.wait_for_selector(name_selector, timeout=5000)
        self.page.locator(name_selector).fill(name)
        self.page.locator(phone_selector).fill(phone_to_enter)
        self.page.locator(save_button_selector).click()

    def run(self, contacts_to_add: list[dict]):
        try:
            self.page.goto("https://web.bale.ai", timeout=90000)
            contacts_menu_selector = "div.Navigation-module__NavItem--mROrNt[style='order: 4;']"
            add_contact_button_selector = "div[title='افزودن مخاطب']"
            form_ready_selector = 'input[aria-label="نام"]'
            success_toast_selector = "div.Toastify__toast-body:has-text('مخاطب مورد نظر به مخاطبین اضافه شد.')"
            error_toast_selector = "div.Toastify__toast-body:has-text('مخاطب مورد نظر در «بله» حساب کاربری ندارد.')"
            self.page.wait_for_selector(contacts_menu_selector, timeout=20000)
            self.page.locator(contacts_menu_selector).click()
            total = len(contacts_to_add)
            successful_adds = 0
            for i, contact in enumerate(contacts_to_add):
                self.page.wait_for_selector(add_contact_button_selector, timeout=10000)
                self.page.locator(add_contact_button_selector).click()
                self.page.wait_for_selector(form_ready_selector, timeout=5000)
                self._add_single_contact(contact.get('name', ''), contact.get('phone', ''))
                self.page.wait_for_selector(form_ready_selector, state='hidden', timeout=10000)
                success_toast = self.page.locator(success_toast_selector)
                error_toast = self.page.locator(error_toast_selector)
                status_determined = False
                for _ in range(6):
                    if success_toast.is_visible():
                        successful_adds += 1
                        status_determined = True
                        break
                    if error_toast.is_visible():
                        status_determined = True
                        break
                    time.sleep(0.5)
                if not status_determined:
                    successful_adds += 1
                time.sleep(2)
            final_message = f"عملیات تمام شد. {successful_adds} از {total} مخاطب با موفقیت اضافه شدند."
            return True, final_message
        except Exception as e:
            return False, f"خطا: {e}"
        
    def close(self):
        if self.browser: self.browser.close()
        if self.playwright: self.playwright.stop()