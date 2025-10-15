# services/rubika_adder_service.py

import time
import random
import os
from config import config

def get_user_data_dir():
    return os.path.join(config.APP_DATA_PATH, "rubika_session")

RUBIKA_WEB_URL = "https://web.rubika.ir"

class RubikaAdderService:
    def __init__(self, headless=False):
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

    def run(self, contacts_to_add: list[dict]):
        try:
            total = len(contacts_to_add)
            successful_adds = 0
            for i, contact in enumerate(contacts_to_add):
                self.page.goto(RUBIKA_WEB_URL, timeout=90000)
                main_menu_selector = "div.sidebar-header__btn-container"
                new_contact_option_selector = "div.btn-menu-item.rbico-user"
                add_contact_button_selector = "button.btn-circle"
                form_ready_selector = 'input[name="first_name"]'
                error_popup_selector = "div.popup.popup-peer.popup-error.active"
                self.page.wait_for_selector(main_menu_selector, timeout=20000)
                self.page.locator(main_menu_selector).click()
                self.page.wait_for_selector(new_contact_option_selector, timeout=5000)
                self.page.locator(new_contact_option_selector).click()
                self.page.wait_for_selector(add_contact_button_selector, timeout=10000)
                self.page.locator(add_contact_button_selector).click()
                self.page.wait_for_selector(form_ready_selector, timeout=5000)
                self._add_single_contact(contact.get('name', ''), contact.get('phone', ''))
                time.sleep(3)
                if self.page.locator(error_popup_selector).is_visible():
                    print(f"  - INFO: Contact '{contact.get('name')}' was not added (User does not exist).")
                else:
                    successful_adds += 1
                    print(f"  - SUCCESS: Contact '{contact.get('name')}' was successfully added.")
            final_message = f"عملیات تمام شد. {successful_adds} از {total} مخاطب با موفقیت اضافه شدند."
            return True, final_message
        except Exception as e:
            return False, f"خطا: {e}"
        
    def close(self):
        if self.browser: self.browser.close()
        if self.playwright: self.playwright.stop()