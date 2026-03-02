#!/usr/bin/env python3
"""
i18n Sync Checker

This script checks that all locale files have the same translation keys.
It detects:
- Missing keys in specific locales
- Extra keys in specific locales
- Mismatches in translation key structure

Usage:
    python scripts/check_i18n_sync.py [--fix]

Options:
    --fix    Automatically add missing keys with placeholder values
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Set, List, Tuple
from collections import defaultdict


def load_translation_file(filepath: Path) -> Dict:
    """Load JSON translation file"""
    if not filepath.exists():
        raise FileNotFoundError(f"Translation file not found: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_all_keys(data: Dict, prefix: str = '') -> Set[str]:
    """Get all keys from nested dictionary"""
    keys = set()
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys.update(get_all_keys(value, full_key))
        else:
            keys.add(full_key)
    return keys


def get_nested_value(data: Dict, key_path: str):
    """Get value from nested dictionary using dot notation"""
    parts = key_path.split('.')
    value = data
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return None
    return value


def set_nested_value(data: Dict, key_path: str, value):
    """Set value in nested dictionary using dot notation"""
    parts = key_path.split('.')
    current = data
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def compare_translations(messages_dir: Path, locales: List[str]) -> Tuple[bool, Dict]:
    """Compare translation keys across all locales"""

    print("=" * 80)
    print("i18n Sync Check")
    print("=" * 80)
    print(f"\nChecking locales: {', '.join(locales)}")
    print(f"Messages directory: {messages_dir}\n")

    # Load all translation files
    translations = {}
    for locale in locales:
        file_path = messages_dir / f'{locale}.json'
        try:
            translations[locale] = load_translation_file(file_path)
            print(f"✓ Loaded {locale}.json")
        except FileNotFoundError as e:
            print(f"✗ Error: {e}")
            return False, {'error': str(e)}

    # Get all keys for each locale
    all_keys = {}
    for locale, data in translations.items():
        all_keys[locale] = get_all_keys(data)

    # Find the reference locale (most keys)
    reference_locale = max(all_keys.items(), key=lambda x: len(x[1]))[0]
    reference_keys = all_keys[reference_locale]

    print(f"\nReference locale: {reference_locale} ({len(reference_keys)} keys)")

    # Compare keys
    results = {
        'reference_locale': reference_locale,
        'reference_keys_count': len(reference_keys),
        'locales': {},
        'missing_keys': defaultdict(set),
        'extra_keys': defaultdict(set),
    }

    has_issues = False

    for locale in locales:
        if locale == reference_locale:
            continue

        locale_keys = all_keys[locale]

        # Find missing keys
        missing = reference_keys - locale_keys
        if missing:
            has_issues = True
            results['missing_keys'][locale] = missing
            print(f"\n✗ {locale}: Missing {len(missing)} keys")
            for key in sorted(missing)[:5]:
                print(f"    - {key}")
            if len(missing) > 5:
                print(f"    ... and {len(missing) - 5} more")

        # Find extra keys
        extra = locale_keys - reference_keys
        if extra:
            has_issues = True
            results['extra_keys'][locale] = extra
            print(f"\n⚠ {locale}: {len(extra)} extra keys (not in reference)")
            for key in sorted(extra)[:5]:
                print(f"    - {key}")
            if len(extra) > 5:
                print(f"    ... and {len(extra) - 5} more")

        results['locales'][locale] = {
            'total_keys': len(locale_keys),
            'missing': len(missing),
            'extra': len(extra),
        }

        if not missing and not extra:
            print(f"✓ {locale}: In sync ({len(locale_keys)} keys)")

    return not has_issues, results


def fix_missing_keys(messages_dir: Path, locales: List[str], results: Dict) -> int:
    """Add missing keys with placeholder values"""

    reference_locale = results['reference_locale']
    fixed_count = 0

    print(f"\n" + "=" * 80)
    print("Fixing Missing Keys")
    print("=" * 80)

    # Load reference translations
    reference_file = messages_dir / f'{reference_locale}.json'
    with open(reference_file, 'r', encoding='utf-8') as f:
        reference_data = json.load(f)

    for locale in locales:
        if locale == reference_locale:
            continue

        missing = results['missing_keys'].get(locale)
        if not missing:
            continue

        # Load current locale file
        locale_file = messages_dir / f'{locale}.json'
        with open(locale_file, 'r', encoding='utf-8') as f:
            locale_data = json.load(f)

        # Add missing keys
        for key in missing:
            # Get reference value
            ref_value = get_nested_value(reference_data, key)

            # Create placeholder
            if isinstance(ref_value, str):
                placeholder = f"[TODO: {ref_value}]"
            elif isinstance(ref_value, dict):
                placeholder = {k: f"[TODO: {v}]" for k, v in ref_value.items()}
            else:
                placeholder = f"[TODO: {key}]"

            set_nested_value(locale_data, key, placeholder)
            fixed_count += 1

        # Save updated file
        with open(locale_file, 'w', encoding='utf-8') as f:
            json.dump(locale_data, f, indent=2, ensure_ascii=False)

        print(f"✓ Fixed {len(missing)} keys in {locale}.json")

    return fixed_count


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(description='Check i18n translation sync')
    parser.add_argument('--fix', action='store_true', help='Automatically fix missing keys')
    args = parser.parse_args()

    # Setup paths
    project_root = Path(__file__).parent.parent
    messages_dir = project_root / 'messages'
    locales = ['en', 'zh']

    # Check sync
    in_sync, results = compare_translations(messages_dir, locales)

    if in_sync:
        print("\n" + "=" * 80)
        print("✓ All translations are in sync!")
        print("=" * 80)
        sys.exit(0)
    else:
        # Fix if requested
        if args.fix:
            fixed_count = fix_missing_keys(messages_dir, locales, results)
            print(f"\n✓ Fixed {fixed_count} missing keys")
            print("\n⚠ Please review the added placeholder translations and update them with proper values")
        else:
            print("\n" + "=" * 80)
            print("✗ Translation sync issues detected")
            print("=" * 80)
            print("\nTo automatically add missing keys, run:")
            print("  python scripts/check_i18n_sync.py --fix")

        sys.exit(1)


if __name__ == '__main__':
    main()
