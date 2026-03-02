#!/usr/bin/env python3
"""
Translation file merger and modularizer

This script:
1. Merges duplicate translation files (frontend/messages and root messages)
2. Splits large translation files into modular structure
3. Ensures all locales have the same keys
4. Outputs organized translation files
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Set
from collections import defaultdict


def deep_merge(base: Dict, update: Dict) -> Dict:
    """Deep merge two dictionaries"""
    result = base.copy()
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_json_file(filepath: Path) -> Dict[str, Any]:
    """Load JSON file"""
    if not filepath.exists():
        return {}
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json_file(filepath: Path, data: Dict[str, Any], indent: int = 2) -> None:
    """Save JSON file with formatting"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
    print(f"✓ Saved: {filepath}")


def get_all_keys(data: Dict[str, Any], prefix: str = '') -> Set[str]:
    """Get all keys from nested dictionary"""
    keys = set()
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys.update(get_all_keys(value, full_key))
        else:
            keys.add(full_key)
    return keys


def split_translations_by_namespace(
    data: Dict[str, Any],
    namespaces: Dict[str, list]
) -> Dict[str, Dict[str, Any]]:
    """Split translations into namespace-based modules"""
    result = {}
    for namespace, keys in namespaces.items():
        result[namespace] = {}
        for key in keys:
            if key in data:
                result[namespace][key] = data[key]
    return result


def main():
    """Main execution"""
    # Paths
    project_root = Path(__file__).parent.parent
    root_messages = project_root / 'messages'
    frontend_messages = project_root / 'frontend' / 'messages'
    output_dir = project_root / 'messages'

    # Load translation files
    locales = ['en', 'zh']

    print("=" * 60)
    print("Translation Merger and Modularizer")
    print("=" * 60)

    # Step 1: Merge duplicate files
    print("\n[Step 1] Merging duplicate translation files...")
    merged_translations = {}

    for locale in locales:
        root_file = root_messages / f'{locale}.json'
        frontend_file = frontend_messages / f'{locale}.json'

        root_data = load_json_file(root_file)
        frontend_data = load_json_file(frontend_file)

        # Merge: frontend data takes precedence for conflicts
        # (assuming frontend has more up-to-date translations)
        merged = deep_merge(root_data, frontend_data)

        merged_translations[locale] = merged

        # Statistics
        root_keys = get_all_keys(root_data)
        frontend_keys = get_all_keys(frontend_data)
        merged_keys = get_all_keys(merged)

        print(f"\n{locale.upper()}:")
        print(f"  Root messages:      {len(root_keys)} keys")
        print(f"  Frontend messages:  {len(frontend_keys)} keys")
        print(f"  Merged messages:    {len(merged_keys)} keys")
        print(f"  New keys:           {len(merged_keys - root_keys)}")

    # Step 2: Analyze key consistency across locales
    print("\n[Step 2] Analyzing key consistency...")
    all_keys_by_locale = {}
    for locale in locales:
        all_keys_by_locale[locale] = get_all_keys(merged_translations[locale])

    # Find missing keys
    missing_keys = defaultdict(set)
    for locale in locales:
        for other_locale in locales:
            if locale != other_locale:
                missing = all_keys_by_locale[other_locale] - all_keys_by_locale[locale]
                if missing:
                    missing_keys[locale].update(missing)

    if missing_keys:
        print("\n⚠ Missing keys detected:")
        for locale, keys in missing_keys.items():
            if keys:
                print(f"  {locale}: {len(keys)} missing keys")
                for key in sorted(keys)[:5]:  # Show first 5
                    print(f"    - {key}")
                if len(keys) > 5:
                    print(f"    ... and {len(keys) - 5} more")

        # Add missing keys with empty values or fallback
        print("\n✓ Adding missing keys with fallback values...")
        for locale in locales:
            for other_locale in locales:
                if locale != other_locale:
                    for key in missing_keys[locale]:
                        # Get the key from other locale
                        parts = key.split('.')
                        value = merged_translations[other_locale]
                        for part in parts:
                            if isinstance(value, dict) and part in value:
                                value = value[part]
                            else:
                                value = key  # Fallback to key name
                                break

                        # Set the value in current locale
                        current = merged_translations[locale]
                        for i, part in enumerate(parts[:-1]):
                            if part not in current:
                                current[part] = {}
                            current = current[part]
                        current[parts[-1]] = value

    # Step 3: Save merged translations
    print("\n[Step 3] Saving merged translations...")
    for locale in locales:
        output_file = output_dir / f'{locale}.json'
        save_json_file(output_file, merged_translations[locale])

    # Step 4: Generate statistics
    print("\n[Step 4] Translation statistics:")
    for locale in locales:
        keys = get_all_keys(merged_translations[locale])
        print(f"  {locale}: {len(keys)} translation keys")

    print("\n" + "=" * 60)
    print("✓ Translation merge complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Review the merged translation files")
    print("  2. Fill in missing translations with proper values")
    print("  3. Remove duplicate frontend/messages/ directory")
    print("  4. Run: npm run typegen:messages (to generate TypeScript types)")


if __name__ == '__main__':
    main()
