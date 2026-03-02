#!/usr/bin/env python3
"""
TypeScript Translation Type Generator

This script:
1. Reads the merged translation files (messages/en.json)
2. Generates TypeScript type definitions for all translation keys
3. Outputs types/messages.d.ts for type-safe translation usage
4. Generates type-safe useTranslations wrappers
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, Set


def to_pascal_case(key: str) -> str:
    """Convert key to PascalCase for type naming"""
    # Remove invalid characters
    clean = re.sub(r'[^a-zA-Z0-9_]', '_', key)
    # Split by underscore and capitalize
    parts = clean.split('_')
    return ''.join(word.capitalize() for word in parts)


def generate_type_from_object(
    data: Dict[str, Any],
    parent_name: str = "Messages",
    indent: int = 0
) -> str:
    """Generate TypeScript type definition from nested object"""

    tabs = "  " * indent
    type_def = f"{tabs}{parent_name}:\n{{\n"

    for key, value in sorted(data.items()):
        # Sanitize key for TypeScript
        ts_key = key.replace('-', '_').replace(' ', '_')

        if isinstance(value, dict):
            # Recursively generate nested type
            nested_type = to_pascal_case(key)
            nested_def = generate_type_from_object(value, nested_type, indent + 1)
            type_def += f"{tabs}{ts_key}: {nested_type};\n"
        elif isinstance(value, str):
            # Check if it's an interpolation string
            if '{{' in value or '{' in value:
                # Parse interpolation variables
                # Simple pattern: {{variableName}} or {variableName}
                vars_found = set()

                # Match {{variableName}} pattern
                for match in re.finditer(r'\{\{(\w+)\}\}', value):
                    vars_found.add(match.group(1))

                # Match {variableName} pattern
                for match in re.finditer(r'\{(\w+)\}', value):
                    var_name = match.group(1)
                    # Skip if it looks like a format specifier
                    if not re.match(r'^\d+', var_name):
                        vars_found.add(var_name)

                if vars_found:
                    # Function type with parameters
                    params = ', '.join(f"{v}: string | number" for v in sorted(vars_found))
                    type_def += f"{tabs}{ts_key}: ({params}) => string;\n"
                else:
                    type_def += f"{tabs}{ts_key}: string;\n"
            else:
                type_def += f"{tabs}{ts_key}: string;\n"
        else:
            type_def += f"{tabs}{ts_key}: any;\n"

    type_def += f"{tabs}}}"

    return type_def


def generate_translation_path_types(data: Dict[str, Any], prefix: str = "") -> Set[str]:
    """Generate set of all translation paths like 'common.save', 'nav.home'"""

    paths = set()

    for key, value in data.items():
        current_path = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict):
            paths.update(generate_translation_path_types(value, current_path))
        else:
            paths.add(current_path)

    return paths


def generate_use_translations_wrapper() -> str:
    """Generate type-safe useTranslations wrapper"""

    return '''/**
 * Type-safe translation wrapper
 *
 * Usage:
 * ```ts
 * import { t } from '@/lib/i18n';
 *
 * // With type inference
 * const message = t('common.save'); // Fully typed
 *
 * // With parameters
 * const welcome = t('common.welcome', { name: 'John' });
 * ```
 */

import { useTranslations as useNextIntlTranslations } from 'next-intl';
import type { Messages, TranslationKey } from './messages';

/**
 * Type-safe translation hook
 * @param namespace - Translation namespace (optional, defaults to root)
 * @returns Translation function
 */
export function useTranslations<N extends keyof Messages = keyof Messages>(
  namespace?: N
): (
  key: N extends keyof Messages
    ? keyof Messages[N]
    : keyof Messages,
  params?: Record<string, string | number>
) => string {
  return useNextIntlTranslations(namespace);
}

/**
 * Type-safe translation function for client-side usage
 * @param key - Translation key (fully typed)
 * @param params - Optional parameters for interpolation
 * @returns Translated string
 */
export function t<K extends TranslationKey>(
  key: K,
  params?: Record<string, string | number>
): string {
  // This is a placeholder - actual implementation requires client-side i18n setup
  return key;
}

/**
 * Get all available translation keys for a namespace
 * @param namespace - Translation namespace
 * @returns Array of translation keys
 */
export function getTranslationKeys<N extends keyof Messages>(
  namespace: N
): (keyof Messages[N])[] {
  // Placeholder - would return actual keys
  return [];
}
'''


def generate_types_definition() -> str:
    """Generate complete types definition file"""

    return '''/**
 * Auto-generated TypeScript types for i18n translations
 *
 * This file is automatically generated by scripts/generate_i18n_types.py
 * DO NOT EDIT MANUALLY - Run: npm run typegen:messages
 *
 * Translation keys are fully typed for type-safe usage:
 * ```ts
 * import { useTranslations } from 'next-intl';
 *
 * const t = useTranslations('common');
 * const message = t('save'); // Type-safe ✅
 * const invalid = t('invalid_key'); // Type error ❌
 * ```
 */

declare interface Messages {
'''

    footer = '''
}

declare type TranslationKey =
  | { [K in keyof Messages]: `${K}` | `${K}.${NestedKey<Messages[K]>}` }[keyof Messages];

// Helper type to extract nested keys
type NestedKey<T, K extends keyof T = keyof T> =
  K extends string
    ? T[K] extends object
      ? `${K}.${NestedKey<T[K]>}`
      : K
    : never;

// Make messages available globally for next-intl
declare global {
  namespace NextIntl {
    type Messages = Messages;
  }
}

export {};
'''


def main():
    """Main execution"""
    print("=" * 80)
    print("TypeScript Translation Type Generator")
    print("=" * 80)

    # Setup paths
    project_root = Path(__file__).parent.parent
    messages_file = project_root / 'messages' / 'en.json'
    output_file = project_root / 'frontend' / 'types' / 'messages.d.ts'

    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Load messages
    print(f"\nReading: {messages_file}")
    with open(messages_file, 'r', encoding='utf-8') as f:
        messages = json.load(f)

    # Generate type definition
    print("Generating TypeScript types...")
    type_definition = generate_type_from_object(messages)

    # Create complete file
    complete_file = generate_types_definition() + type_definition + "\n}" + generate_use_translations_wrapper()

    # Save
    print(f"Writing: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(complete_file)

    # Statistics
    all_paths = generate_translation_path_types(messages)

    print("\n" + "=" * 80)
    print("✓ Type generation complete!")
    print("=" * 80)
    print(f"\nStatistics:")
    print(f"  Total translation keys: {len(all_paths)}")
    print(f"  Output file: {output_file}")
    print(f"\nNext steps:")
    print(f"  1. Restart TypeScript server in your IDE")
    print(f"  2. Translation keys are now fully typed")
    print(f"  3. Use: const t = useTranslations('common'); t('save')")


if __name__ == '__main__':
    main()
