# services/eitaa_adder_service.py

import time
import random
import os
from config import config

def get_user_data_dir():
    return os.path.join(config.APP_DATA_PATH, "eitaa_session")

class EitaaAdderService:
    def __init__(self, headless=False):
        from playwright.sync_api import sync_playwright
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch_persistent_context(
            get_user_data_dir(), headless=headless, slow_mo=100
        )
        self.page = self.browser.pages[0] if self.browser.pages else self.browser.new_page()

    def _add_single_contact(self, name: str, phone: str):
        name_selector = "div.name-fields div.input-field-input[contenteditable='true']"
        self.page.wait_for_selector(name_selector, timeout=5000)
        self.page.locator(name_selector).first.fill(name)
        phone_selector = "div.input-field-phone div.input-field-input[contenteditable='true']"
        self.page.wait_for_selector(phone_selector, timeout=5000)
        self.page.locator(phone_selector).fill("") 
        self.page.locator(phone_selector).fill(phone)
        self.page.keyboard.press('Enter')
        time.sleep(3)

    def run(self, contacts_to_add: list[dict]):
        try:
            self.page.goto("https://web.eitaa.com", timeout=90000)
            self.page.wait_for_selector("#new-menu", timeout=20000)
            self.page.locator("#new-menu").click()
            new_contact_selector = "div.tgico-newprivate" 
            self.page.wait_for_selector(new_contact_selector, timeout=5000)
            self.page.locator(new_contact_selector).click()
            total = len(contacts_to_add)
            for i, contact in enumerate(contacts_to_add):
                add_button_selector = "button.tgico-add"
                self.page.wait_for_selector(add_button_selector, timeout=5000)
                self.page.locator(add_button_selector).click()
                popup_selector = "div.popup-create-contact"
                self.page.wait_for_selector(popup_selector, timeout=5000)
                self._add_single_contact(contact.get('name', ''), contact.get('phone', ''))
                self.page.wait_for_selector(popup_selector, state='hidden', timeout=5000)
                time.sleep(random.uniform(1, 2))
            return True, f"عملیات افزودن {total} مخاطب با موفقیت انجام شد."
        except Exception as e:
            return False, f"خطا: {e}"
        
    def close(self):
        if self.browser: self.browser.close()
        if self.playwright: self.playwright.stop()