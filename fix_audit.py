#!/usr/bin/env python3
import re

file_path = "/Users/levent/Desktop/sec/frontend/app/[locale]/audit/page.tsx"

with open(file_path, 'r') as f:
    content = f.read()

# Lines to fix
fixes = {
    'return tAuditPage(\'dateRange.custom\') + \': ${fromDate.toLocaleDateString()} - ${toDate.toLocaleDateString()}\';':
        'return `${tAuditPage(\'dateRange.custom\')}: ${fromDate.toLocaleDateString()} - ${toDate.toLocaleDateString()}`;',
    'return tAuditPage(\'dateRange.from\') + \'${new Date(filterDateFrom).toLocaleDateString()}\';':
        'return `${tAuditPage(\'dateRange.from\')} ${new Date(filterDateFrom).toLocaleDateString()}`;',
    'return tAuditPage(\'dateRange.to\') + \'${new Date(filterDateTo).toLocaleDateString()}\';':
        'return `${tAuditPage(\'dateRange.to\')} ${new Date(filterDateTo).toLocaleDateString()}`;',
}

for old, new in fixes.items():
    content = content.replace(old, new)

with open(file_path, 'w') as f:
    f.write(content)

print("✓ Fixed template strings")
