#!/usr/bin/env python3
"""
修复前端缺失的翻译键
使用方法: python3 fix_missing_translations.py
"""

import json
import os
import re
from pathlib import Path

FRONTEND_DIR = Path(__file__).parent / "frontend"
MESSAGES_DIR = FRONTEND_DIR / "messages"

# 扫描所有tsx文件中的翻译键使用
def scan_translation_keys():
    """扫描前端代码中使用的所有翻译键"""
    keys = set()
    
    # 扫描所有tsx文件
    for tsx_file in FRONTEND_DIR.rglob("*.tsx"):
        content = tsx_file.read_text()
        # 匹配 t('xxx.yyy') 或 t("xxx.yyy")
        pattern = r"t\(['\"]([^'\"]+)['\"]\)"
        matches = re.findall(pattern, content)
        keys.update(matches)
    
    return keys

# 检查并添加缺失的键
def check_and_fix_translations():
    keys = scan_translation_keys()
    
    for locale in ["zh", "en"]:
        msg_file = MESSAGES_DIR / f"{locale}.json"
        with open(msg_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 找出缺失的键
        missing = []
        for key in keys:
            # 只检查以 aiAssistant 开头的键
            if key.startswith("aiAssistant."):
                # 检查键是否存在
                parts = key.split(".")
                current = data
                exists = True
                for part in parts:
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        exists = False
                        break
                if not exists:
                    missing.append(key)
        
        if missing:
            print(f"\n{locale}.json 缺失 {len(missing)} 个键:")
            for k in missing[:10]:  # 只显示前10个
                print(f"  - {k}")
            if len(missing) > 10:
                print(f"  ... 还有 {len(missing)-10} 个")
        else:
            print(f"\n{locale}.json 没有缺失 aiAssistant 相关键 ✓")

if __name__ == "__main__":
    check_and_fix_translations()
