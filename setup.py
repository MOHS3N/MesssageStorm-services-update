import os
import glob
from setuptools import setup
from Cython.Build import cythonize

# --- تنظیمات ---
SOURCE_DIR = "services"  # نام پوشه‌ای که فایل‌های py. داخلش هستند
BUILD_DIR = "build_output" # پوشه‌ای که فایل‌های موقت ساخت در آن قرار می‌گیرند

def get_py_files(source_dir):
    """پیدا کردن تمام فایل‌های py در پوشه و زیرپوشه‌ها"""
    py_files = []
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                # مسیر کامل فایل
                file_path = os.path.join(root, file)
                py_files.append(file_path)
    return py_files

# دریافت لیست فایل‌ها
files_to_compile = get_py_files(SOURCE_DIR)

if not files_to_compile:
    print(f"هیچ فایل .py در پوشه '{SOURCE_DIR}' پیدا نشد.")
else:
    print(f"فایل‌های زیر کامپایل خواهند شد: {files_to_compile}")

    setup(
        name="My Compiled Modules",
        ext_modules=cythonize(
            files_to_compile,
            build_dir=BUILD_DIR, # محل ذخیره فایل‌های C تولید شده
            compiler_directives={'language_level': "3", 'always_allow_keywords': True}
        ),
        script_args=["build_ext", "--inplace"] # سوییچ برای بیلد کردن و کپی در محل
    )
    
    print("\n✅ عملیات تمام شد. فایل‌های .pyd در کنار فایل‌های اصلی ایجاد شدند.")
    
    # (اختیاری) پاکسازی: حذف فایل‌های .c و پوشه بیلد
    # import shutil
    # if os.path.exists(BUILD_DIR): shutil.rmtree(BUILD_DIR)
    # for f in files_to_compile:
    #     c_file = f.replace(".py", ".c")
    #     if os.path.exists(c_file): os.remove(c_file)