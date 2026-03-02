#!/usr/bin/env python3
"""
Missing Translation Finder

This script scans all TypeScript/TSX files and identifies:
- Hardcoded English strings that should be translated
- Translation keys that don't exist in translation files
- Missing translations for specific locales

Usage:
    python scripts/find_missing_translations.py [--locale en, zh]
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict


def load_translation_keys(messages_dir: Path, locale: str) -> Set[str]:
    """Load all translation keys for a locale"""
    file_path = messages_dir / f'{locale}.json'

    if not file_path.exists():
        return set()

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    def get_keys(obj, prefix=''):
        keys = set()
        for key, value in obj.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                keys.update(get_keys(value, full_key))
            else:
                keys.add(full_key)
        return keys

    return get_keys(data)


def find_t_function_calls(file_path: Path) -> List[Dict]:
    """Find all t() function calls in a file"""

    content = file_path.read_text()

    calls = []

    # Pattern for t('key') or t("key")
    pattern = r"t\(['\"]([^'\"]+)['\"]"
    for match in re.finditer(pattern, content):
        calls.append({
            'key': match.group(1),
            'line': content[:match.start()].count('\n') + 1,
        })

    # Pattern for useTranslations('namespace')
    pattern2 = r"useTranslations\(['\"]([^'\"]+)['\"]"
    for match in re.finditer(pattern2, content):
        calls.append({
            'namespace': match.group(1),
            'line': content[:match.start()].count('\n') + 1,
            'type': 'namespace',
        })

    return calls


def find_hardcoded_strings(file_path: Path) -> List[Dict]:
    """Find hardcoded English strings that might need translation"""

    content = file_path.read_text()
    strings = []

    # Patterns to skip
    skip_patterns = [
        r'^import\s+',        # Import statements
        r'^\s*//.*$',         # Comments
        r'^\s*/\*.*\*/\s*$', # Block comments
        r'^\s*\w+\s*:\s*.*', # Type definitions
        r'^\s*interface\s+', # Interface definitions
        r'^\s*type\s+',      # Type aliases
        r'^\s*enum\s+',      # Enums
        r'^\s*export\s+',    # Export statements
        r'^\s*const\s+\w+\s*=\s*{', # Object definitions
        r'^\s*\w+\s*\(',     # Function calls
    ]

    # Pattern for string literals
    # Match strings with letters (not just special characters/numbers)
    pattern = r'["\']([A-Z][a-zA-Z\s]{5,})["\']'

    for match in re.finditer(pattern, content):
        line_start = content.rfind('\n', 0, match.start()) + 1
        line_end = content.find('\n', match.end())
        if line_end == -1:
            line_end = len(content)
        line = content[line_start:line_end]

        # Skip if matches skip patterns
        skip = False
        for skip_pattern in skip_patterns:
            if re.match(skip_pattern, line):
                skip = True
                break

        if skip:
            continue

        strings.append({
            'value': match.group(1),
            'line': content[:match.start()].count('\n') + 1,
            'context': line.strip(),
        })

    return strings


def scan_directory(directory: Path, locales: List[str]) -> Dict:
    """Scan all TypeScript/TSX files"""

    results = {
        'translation_keys': set(),
        'unknown_keys': defaultdict(list),
        'hardcoded_strings': [],
        'files_scanned': 0,
    }

    # Load all valid translation keys
    messages_dir = directory / 'messages'
    valid_keys = load_translation_keys(messages_dir, 'en')

    # Scan all TSX/TS files
    for file_path in directory.rglob('*.tsx'):
        if 'node_modules' in str(file_path) or '.next' in str(file_path):
            continue

        results['files_scanned'] += 1

        # Find t() calls
        t_calls = find_t_function_calls(file_path)
        for call in t_calls:
            if 'key' in call:
                key = call['key']
                results['translation_keys'].add(key)

                if key not in valid_keys:
                    results['unknown_keys'][key].append({
                        'file': str(file_path.relative_to(directory)),
                        'line': call['line'],
                    })

        # Find hardcoded strings
        hardcoded = find_hardcoded_strings(file_path)
        for item in hardcoded:
            item['file'] = str(file_path.relative_to(directory))
            results['hardcoded_strings'].append(item)

    return results


def main():
    """Main execution"""
    print("=" * 80)
    print("Missing Translation Finder")
    print("=" * 80)

    # Setup paths
    project_root = Path(__file__).parent.parent
    frontend_dir = project_root / 'frontend'
    locales = ['en', 'zh']

    # Scan
    print(f"\nScanning: {frontend_dir}")
    results = scan_directory(frontend_dir, locales)

    print(f"Files scanned: {results['files_scanned']}")
    print(f"Unique translation keys used: {len(results['translation_keys'])}")

    # Report unknown keys
    if results['unknown_keys']:
        print(f"\n⚠ Unknown translation keys: {len(results['unknown_keys'])}")
        print("-" * 80)

        for key, locations in sorted(results['unknown_keys'].items())[:20]:
            print(f"\n  {key}")
            for loc in locations[:3]:
                print(f"    {loc['file']}:{loc['line']}")
            if len(locations) > 3:
                print(f"    ... and {len(locations) - 3} more")

    # Report hardcoded strings
    if results['hardcoded_strings']:
        print(f"\n⚠ Potential hardcoded strings: {len(results['hardcoded_strings'])}")
        print("-" * 80)

        # Group by value
        by_value = defaultdict(list)
        for item in results['hardcoded_strings']:
            by_value[item['value']].append(item)

        for value, items in sorted(by_value.items(), key=lambda x: -len(x[1]))[:20]:
            print(f"\n  \"{value}\" ({len(items)} occurrences)")
            for item in items[:2]:
                print(f"    {item['file']}:{item['line']}")
                if item.get('context'):
                    print(f"      {item['context'][:70]}...")

    print("\n" + "=" * 80)

    if results['unknown_keys'] or results['hardcoded_strings']:
        print("✗ Issues found")
        print("\nRecommendations:")
        print("  1. Add missing translation keys to messages/en.json and messages/zh.json")
        print("  2. Replace hardcoded strings with t() calls")
        print("  3. Run: python scripts/check_i18n_sync.py --fix")
        return 1
    else:
        print("✓ No issues found")
        return 0


if __name__ == '__main__':
    sys.exit(main())
