#!/usr/bin/env python3

file_path = "/Users/levent/Desktop/sec/frontend/app/[locale]/audit/page.tsx"

with open(file_path, 'r') as f:
    content = f.read()

# Fix the problematic template strings - they have \n inside the string instead of being line terminators
content = content.replace(
    "return `${tAuditPage('dateRange.custom')}: ${fromDate.toLocaleDateString()} - ${toDate.toLocaleDateString()}`;\n    }",
    "return `${tAuditPage('dateRange.custom')}: ${fromDate.toLocaleDateString()} - ${toDate.toLocaleDateString()}`;\n    }"
)
content = content.replace(
    "return `${tAuditPage('dateRange.from')} ${new Date(filterDateFrom).toLocaleDateString()}`;\n    }",
    "return `${tAuditPage('dateRange.from')} ${new Date(filterDateFrom).toLocaleDateString()}`;\n    }"
)
content = content.replace(
    "return `${tAuditPage('dateRange.to')} ${new Date(filterDateTo).toLocaleDateString()}`;",
    "return `${tAuditPage('dateRange.to')} ${new Date(filterDateTo).toLocaleDateString()}`;"
)

with open(file_path, 'w') as f:
    f.write(content)

print("✓ Fixed all template strings")
