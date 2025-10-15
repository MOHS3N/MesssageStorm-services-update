# services/database.py

import sqlite3
import os
from config import config # <-- ایمپورت کانفیگ مرکزی

class DatabaseManager:
    """
    A class to manage all interactions with the SQLite database.
    """
    def __init__(self):
        self.db_file = None

    def _initialize_path(self):
        if self.db_file is None:
            if config.APP_DATA_PATH is None:
                raise Exception("Database path cannot be initialized. APP_DATA_PATH is not set in config.")
            self.db_file = os.path.join(config.APP_DATA_PATH, "msgstorm.db")
            print(f"Database path initialized to: {self.db_file}")

    def _get_connection(self):
        self._initialize_path()
        return sqlite3.connect(self.db_file)

    def initialize_database(self):
        self._initialize_path()
        
        create_tables_meta_query = """
        CREATE TABLE IF NOT EXISTS tables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL UNIQUE,
            unique_name TEXT NOT NULL UNIQUE
        );
        """
        # --- تغییر: افزودن ستون platform ---
        create_messages_template_query = """
        CREATE TABLE IF NOT EXISTS message_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL UNIQUE,
            body TEXT NOT NULL,
            attachment_type TEXT,
            attachment_path TEXT,
            source_table_unique_name TEXT,
            platform TEXT
        );
        """
        create_posting_status_query = """
        CREATE TABLE IF NOT EXISTS posting_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL UNIQUE,
            row INTEGER NOT NULL
        );
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(create_tables_meta_query)
                cursor.execute(create_messages_template_query)
                cursor.execute(create_posting_status_query)
            print("Database tables ('tables', 'message_templates', and 'posting_status') are ready.")
        except sqlite3.Error as e:
            print(f"Error while initializing database: {e}")

    # ... سایر متدها ...
    def add_table_metadata(self, title: str, unique_name: str) -> bool:
        sql = "INSERT INTO tables (title, unique_name) VALUES (?, ?)"
        try:
            with self._get_connection() as conn:
                conn.cursor().execute(sql, (title, unique_name))
            return True
        except sqlite3.IntegrityError:
            return False
        except sqlite3.Error as e:
            print(f"DB Error in add_table_metadata: {e}")
            return False

    def check_title_exists(self, title: str) -> bool:
        sql = "SELECT 1 FROM tables WHERE title = ?"
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (title,))
                return cursor.fetchone() is not None
        except sqlite3.Error as e:
            print(f"DB Error in check_title_exists: {e}")
            return False

    def get_all_tables_with_names(self, platform_filter: str = None, type_filter: str = None) -> list[dict]:
        sql = "SELECT id, title, unique_name FROM tables"
        params = []
        where_clauses = []
        if platform_filter:
            where_clauses.append("unique_name LIKE ?")
            params.append(f"{platform_filter}_%")
        if type_filter == "tbl_":
            where_clauses.append("unique_name LIKE ? AND unique_name NOT LIKE ?")
            params.extend(["%_tbl_%", "%_contact_tbl_%"])
        elif type_filter == "contact_tbl_":
            where_clauses.append("unique_name LIKE ?")
            params.append(f"%_{type_filter}%")
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        sql += " ORDER BY title ASC"
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(sql, params)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"DB Error in get_all_tables_with_names: {e}")
            return []

    def delete_table_by_unique_name(self, unique_name: str) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("BEGIN TRANSACTION;")
                cursor.execute(f'DROP TABLE IF EXISTS "{unique_name}";')
                cursor.execute("DELETE FROM tables WHERE unique_name = ?;", (unique_name,))
                conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"DB Error in delete_table_by_unique_name: {e}")
            if conn: conn.rollback()
            return False

    def execute_dynamic_query(self, query: str, data: list = None) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if data:
                    cursor.executemany(query, data)
                else:
                    cursor.execute(query)
            return True
        except sqlite3.Error as e:
            print(f"DB Error in execute_dynamic_query: {e}")
            return False
        
    def get_table_data(self, table_unique_name: str) -> tuple[list, list[tuple]]:
        headers = []
        data = []
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f'PRAGMA table_info("{table_unique_name}")')
                headers = [row[1] for row in cursor.fetchall()]
                cursor.execute(f'SELECT * FROM "{table_unique_name}"')
                data = cursor.fetchall()
        except sqlite3.Error as e:
            print(f"DB Error in get_table_data for table '{table_unique_name}': {e}")
        return headers, data
    
    def update_cell_data(self, table_unique_name: str, column_name: str, new_value: any, row_id: int) -> bool:
        sql = f'UPDATE "{table_unique_name}" SET "{column_name}" = ? WHERE id = ?'
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (new_value, row_id))
            return True
        except sqlite3.Error as e:
            print(f"DB Error in update_cell_data: {e}")
            return False
        
    def insert_new_row(self, table_unique_name: str, column_names: list[str]) -> int | None:
        cols_to_insert = [f'"{col}"' for col in column_names if col != 'id']
        placeholders = ", ".join(["?"] * len(cols_to_insert))
        sql = f'INSERT INTO "{table_unique_name}" ({", ".join(cols_to_insert)}) VALUES ({placeholders})'
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, tuple([''] * len(cols_to_insert)))
                return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"DB Error in insert_new_row: {e}")
            return None
        
    def delete_row_by_id(self, table_unique_name: str, row_id: int) -> bool:
        sql = f'DELETE FROM "{table_unique_name}" WHERE id = ?'
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (row_id,))
            return True
        except sqlite3.Error as e:
            print(f"DB Error in delete_row_by_id: {e}")
            return False

    # --- تغییر: افزودن فیلتر پلتفرم و خواندن ستون جدید ---
    def get_all_message_templates(self, platform_filter: str = None) -> list[dict]:
        sql = "SELECT id, title, body, attachment_type, attachment_path, source_table_unique_name, platform FROM message_templates"
        params = []
        if platform_filter:
            sql += " WHERE platform = ?"
            params.append(platform_filter)
        sql += " ORDER BY title ASC"
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                return [dict(row) for row in conn.cursor().execute(sql, params).fetchall()]
        except sqlite3.Error as e:
            print(f"DB Error in get_all_message_templates: {e}")
            return []

    # --- تغییر: افزودن پارامتر platform ---
    def add_new_message_template(self, title: str, body: str, attachment_type: str = None, attachment_path: str = None, source_table: str = None, platform: str = None) -> bool:
        sql = "INSERT INTO message_templates (title, body, attachment_type, attachment_path, source_table_unique_name, platform) VALUES (?, ?, ?, ?, ?, ?)"
        try:
            with self._get_connection() as conn:
                conn.cursor().execute(sql, (title, body, attachment_type, attachment_path, source_table, platform))
            return True
        except sqlite3.IntegrityError:
            return False
        except sqlite3.Error as e:
            print(f"DB Error in add_new_message_template: {e}")
            return False

    # --- تغییر: افزودن پارامتر platform ---
    def update_message_template_by_id(self, template_id: int, new_title: str, new_body: str, attachment_type: str = None, attachment_path: str = None, source_table: str = None, platform: str = None) -> bool:
        sql = "UPDATE message_templates SET title = ?, body = ?, attachment_type = ?, attachment_path = ?, source_table_unique_name = ?, platform = ? WHERE id = ?"
        try:
            with self._get_connection() as conn:
                conn.cursor().execute(sql, (new_title, new_body, attachment_type, attachment_path, source_table, platform, template_id))
            return True
        except sqlite3.IntegrityError:
            return False
        except sqlite3.Error as e:
            print(f"DB Error in update_message_template_by_id: {e}")
            return False
        
    def delete_message_template_by_id(self, template_id: int) -> bool:
        sql = "DELETE FROM message_templates WHERE id = ?"
        try:
            with self._get_connection() as conn:
                conn.cursor().execute(sql, (template_id,))
            return True
        except sqlite3.Error as e:
            print(f"DB Error in delete_message_template_by_id: {e}")
            return False
        
    def get_message_template_by_id(self, template_id: int) -> dict | None:
        sql = "SELECT id, title, body, attachment_type, attachment_path, source_table_unique_name, platform FROM message_templates WHERE id = ?"
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                row = conn.cursor().execute(sql, (template_id,)).fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            print(f"DB Error in get_message_template_by_id: {e}")
            return None

    def update_posting_status(self, table_name: str, row: int) -> bool:
        sql = """
            INSERT INTO posting_status (table_name, row) VALUES (?, ?)
            ON CONFLICT(table_name) DO UPDATE SET row = excluded.row;
        """
        try:
            with self._get_connection() as conn:
                conn.cursor().execute(sql, (table_name, row))
            return True
        except sqlite3.Error as e:
            print(f"DB Error in update_posting_status: {e}")
            return False
            
    def delete_posting_status(self, table_name: str) -> bool:
        sql = "DELETE FROM posting_status WHERE table_name = ?"
        try:
            with self._get_connection() as conn:
                conn.cursor().execute(sql, (table_name,))
            return True
        except sqlite3.Error as e:
            print(f"DB Error in delete_posting_status: {e}")
            return False

    def get_posting_status(self, table_name: str) -> int | None:
        sql = "SELECT row FROM posting_status WHERE table_name = ?"
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (table_name,))
                result = cursor.fetchone()
                return result[0] if result else None
        except sqlite3.Error as e:
            print(f"DB Error in get_posting_status: {e}")
            return None

db_manager = DatabaseManager()