#!/usr/bin/env python3
"""
i18n Translation Validator

This script validates translation files for:
- Correct JSON syntax
- Required keys existence
- Proper key naming conventions
- Duplicate key detection
- Empty translation values

Usage:
    python scripts/validate_i18n.py
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict


def validate_json_syntax(file_path: Path) -> Tuple[bool, List[str]]:
    """Validate JSON syntax"""
    errors = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json.load(f)
        return True, errors
    except json.JSONDecodeError as e:
        errors.append(f"JSON syntax error at line {e.lineno}, column {e.colno}: {e.msg}")
        return False, errors


def validate_required_keys(data: Dict, locale: str) -> List[str]:
    """Check for required keys"""

    errors = []

    # Define required keys
    required_keys = [
        'meta',
        'common',
        'nav',
        'errors',
    ]

    for key in required_keys:
        if key not in data:
            errors.append(f"Missing required key: {key}")

    return errors


def validate_key_naming(data: Dict, prefix: str = '') -> List[str]:
    """Validate key naming conventions"""

    errors = []

    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key

        # Check for forbidden patterns
        if ' ' in key:
            errors.append(f"Key contains spaces: {full_key}")

        if key[0].isdigit():
            errors.append(f"Key starts with digit: {full_key}")

        # Check camelCase vs snake_case consistency
        # (Optional - currently just warning)

        if isinstance(value, dict):
            errors.extend(validate_key_naming(value, full_key))

    return errors


def find_duplicate_keys(data: Dict, prefix: str = '') -> Set[str]:
    """Find duplicate keys (case-insensitive)"""

    seen = defaultdict(int)
    duplicates = set()

    def collect_keys(obj, parent=''):
        for key, value in obj.items():
            full_key = f"{parent}.{key}".lower() if parent else key.lower()
            seen[full_key] += 1
            if seen[full_key] > 1:
                duplicates.add(full_key)
            if isinstance(value, dict):
                collect_keys(value, f"{parent}.{key}" if parent else key)

    collect_keys(data)
    return duplicates


def validate_empty_values(data: Dict, prefix: str = '') -> List[str]:
    """Find empty translation values"""

    errors = []

    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key

        if isinstance(value, str):
            if not value or value.strip() == '':
                errors.append(f"Empty translation value: {full_key}")
        elif isinstance(value, dict):
            errors.extend(validate_empty_values(value, full_key))

    return errors


def validate_interpolation_syntax(data: Dict, prefix: str = '') -> List[str]:
    """Validate interpolation syntax consistency"""

    errors = []

    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key

        if isinstance(value, str):
            # Check for mixed interpolation styles
            has_double_brace = '{{' in value
            has_single_brace = '{' in value and not '{{' in value

            # Both styles in same string is confusing
            if '{{' in value and '{' in value and '{{' not in value.replace('{{', ''):
                # Has both {{}} and {} (but not just {{}})
                if has_double_brace and has_single_brace:
                    # Count actual single braces (not part of double)
                    single_count = value.count('{') - 2 * value.count('{{')
                    if single_count > 0:
                        errors.append(f"Mixed interpolation styles: {full_key}")

        elif isinstance(value, dict):
            errors.extend(validate_interpolation_syntax(value, full_key))

    return errors


def validate_file(file_path: Path, locale: str) -> Dict:
    """Validate a single translation file"""

    result = {
        'valid': True,
        'errors': [],
        'warnings': [],
    }

    # Check JSON syntax
    syntax_valid, syntax_errors = validate_json_syntax(file_path)
    if not syntax_valid:
        result['valid'] = False
        result['errors'].extend(syntax_errors)
        return result

    # Load data
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Validate required keys
    required_errors = validate_required_keys(data, locale)
    if required_errors:
        result['errors'].extend(required_errors)
        result['valid'] = False

    # Validate key naming
    naming_errors = validate_key_naming(data)
    if naming_errors:
        result['errors'].extend(naming_errors)
        result['valid'] = False

    # Find duplicate keys
    duplicates = find_duplicate_keys(data)
    if duplicates:
        result['errors'].extend([f"Duplicate key (case-insensitive): {dup}" for dup in duplicates])
        result['valid'] = False

    # Validate empty values
    empty_errors = validate_empty_values(data)
    if empty_errors:
        result['warnings'].extend(empty_errors)

    # Validate interpolation syntax
    interp_errors = validate_interpolation_syntax(data)
    if interp_errors:
        result['warnings'].extend(interp_errors)

    return result


def main():
    """Main execution"""

    print("=" * 80)
    print("i18n Translation Validator")
    print("=" * 80)

    # Setup paths
    project_root = Path(__file__).parent.parent
    messages_dir = project_root / 'messages'
    locales = ['en', 'zh']

    all_valid = True

    for locale in locales:
        file_path = messages_dir / f'{locale}.json'

        print(f"\nValidating: {file_path.name}")
        print("-" * 80)

        if not file_path.exists():
            print(f"✗ File not found")
            all_valid = False
            continue

        result = validate_file(file_path, locale)

        if result['errors']:
            print(f"\n✗ Errors ({len(result['errors'])}):")
            for error in result['errors']:
                print(f"  - {error}")
            all_valid = False

        if result['warnings']:
            print(f"\n⚠ Warnings ({len(result['warnings'])}):")
            for warning in result['warnings']:
                print(f"  - {warning}")

        if result['valid'] and not result['warnings']:
            print("✓ Valid")

    print("\n" + "=" * 80)

    if all_valid:
        print("✓ All translation files are valid")
        return 0
    else:
        print("✗ Validation failed")
        print("\nPlease fix the errors above and run again")
        return 1


if __name__ == '__main__':
    sys.exit(main())
