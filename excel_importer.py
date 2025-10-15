# services/excel_importer.py

import pandas as pd
import re
import uuid
import time
from services.database import db_manager

def sanitize_name(name: str) -> str:
    name = re.sub(r'[^a-zA-Z0-9_]', '', name)
    return name.replace(' ', '_').lower()

def validate_excel_headers(file_path: str) -> tuple[bool, str]:
    try:
        df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)
        if df.columns.empty:
            return (False, "فایل انتخاب شده ستونی ندارد یا خالی است.")
        for header in df.columns:
            header_str = str(header).strip()
            if not header_str:
                return (False, "یکی از ستون‌ها عنوان (هدر) ندارد.")
            if not re.match(r'^[a-zA-Z0-9_ ]+$', header_str):
                return (False, f"ستون یا ستون‌هایی در این سند فاقد عنوان هستند\nدقت داشته باشید عنوان ستون‌ها حتما باید انگلیسی باشند.")
        return (True, "فایل معتبر است.")
    except Exception as e:
        return (False, f"خطا در خواندن فایل: {e}")

# --- تابع جدید برای تشخیص نوع فایل ---
def detect_import_type(file_path: str) -> str:
    """بر اساس هدرهای فایل، نوع واردات ('add_contact' یا 'send_message') را تشخیص می‌دهد."""
    try:
        df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)
        headers = list(df.columns)
        if len(headers) == 2 and headers[0] == 'new_name' and headers[1] == 'new_phone':
            return "add_contact"
        else:
            return "send_message"
    except Exception:
        return "send_message" # در صورت بروز خطا، حالت پیش‌فرض را برمی‌گردانیم

def process_excel_file(file_path: str, title: str, platform: str) -> tuple[bool, str, dict]:
    try:
        df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)
        
        # --- استفاده از تابع جدید برای تعیین پیشوند ---
        import_type = detect_import_type(file_path)
        table_prefix = "contact_tbl_" if import_type == "add_contact" else "tbl_"
        
        # بخش مربوط به تغییر نام ستون‌ها و پاک‌سازی آنها
        if import_type == "add_contact":
            df.rename(columns={'new_name': 'name', 'new_phone': 'phone'}, inplace=True)
            sanitized_columns = ['name', 'phone']
        else:
            sanitized_columns = [sanitize_name(col) for col in df.columns]

        unique_name = f"{platform}_{table_prefix}{str(uuid.uuid4()).replace('-', '_')}"

        if not db_manager.add_table_metadata(title, unique_name):
            return (False, "نام جدول تکراری است یا خطایی در ثبت اطلاعات رخ داد.", None)

        columns_sql = ", ".join([f'"{col}" TEXT' for col in sanitized_columns])
        create_table_sql = f'CREATE TABLE IF NOT EXISTS "{unique_name}" (id INTEGER PRIMARY KEY AUTOINCREMENT, {columns_sql});'
        if not db_manager.execute_dynamic_query(create_table_sql):
            return (False, f"خطا در ساختن جدول '{unique_name}'.", None)

        if not df.empty:
            data_to_insert = list(df.itertuples(index=False, name=None))
            column_names = ", ".join([f'"{col}"' for col in sanitized_columns])
            placeholders = ", ".join(["?"] * len(sanitized_columns))
            insert_sql = f'INSERT INTO "{unique_name}" ({column_names}) VALUES ({placeholders})'
            
            if not db_manager.execute_dynamic_query(insert_sql, data_to_insert):
                return (False, f"خطا در وارد کردن داده‌ها به جدول '{unique_name}'.", None)

        result_info = {"table_name": unique_name, "title": title}
        return (True, "داده‌های فایل با موفقیت وارد و ثبت شد.", result_info)

    except Exception as e:
        return (False, f"یک خطای پیش‌بینی نشده رخ داد: {e}", None)