#!/usr/bin/env python3
"""
Backend Error Code Migration Script

This script:
1. Scans all Python files for HTTPException usage
2. Analyzes error patterns and suggests error code mappings
3. Generates migration report
4. Can apply automatic migrations where safe
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict


def find_http_exceptions(file_path: Path) -> List[Dict]:
    """Find all HTTPException usages in a file"""
    content = file_path.read_text()
    exceptions = []

    # Split by lines for processing
    lines = content.split('\n')

    i = 0
    while i < len(lines):
        line = lines[i]

        # Look for "raise HTTPException"
        if 'raise HTTPException' in line:
            # Collect multiline until we find the closing ")"
            exception_lines = [line]
            j = i + 1
            parenthesis_open = line.count('(') - line.count(')')

            while j < len(lines) and parenthesis_open > 0:
                exception_lines.append(lines[j])
                parenthesis_open += lines[j].count('(') - lines[j].count(')')
                j += 1

            full_exception = '\n'.join(exception_lines)

            # Extract status_code and detail
            status_match = re.search(r'status_code\s*=\s*(\d+)', full_exception)
            detail_match = re.search(r'detail\s*=\s*["\']([^"\']+)["\']', full_exception, re.DOTALL)

            if status_match:
                status_code = status_match.group(1)
                message = detail_match.group(1) if detail_match else ""

                exceptions.append({
                    'type': 'full',
                    'status_code': status_code,
                    'message': message.strip(),
                    'line': i + 1,
                    'context': full_exception.strip(),
                })

        i += 1

    return exceptions


def suggest_error_code(status_code: int, message: str) -> str:
    """Suggest appropriate error code based on status and message"""
    msg_lower = message.lower()

    # 401 Unauthorized
    if status_code == 401:
        if 'token' in msg_lower:
            if 'expired' in msg_lower:
                return 'AuthError.TOKEN_EXPIRED'
            if 'invalid' in msg_lower:
                return 'AuthError.INVALID_TOKEN'
            if 'missing' in msg_lower:
                return 'AuthError.TOKEN_MISSING'
        if 'credential' in msg_lower:
            return 'AuthError.INVALID_CREDENTIALS'
        return 'AuthError.UNAUTHORIZED'

    # 403 Forbidden
    if status_code == 403:
        if 'permission' in msg_lower:
            return 'AuthError.INSUFFICIENT_PERMISSIONS'
        return 'AuthError.FORBIDDEN'

    # 404 Not Found
    if status_code == 404:
        if 'definition' in msg_lower:
            return 'DefinitionError.NOT_FOUND'
        if 'execution' in msg_lower:
            return 'ExecutionError.NOT_FOUND'
        if 'trigger' in msg_lower:
            return 'TriggerError.NOT_FOUND'
        if 'user' in msg_lower:
            return 'AuthError.USER_NOT_FOUND'
        return 'ResourceError.NOT_FOUND'

    # 409 Conflict
    if status_code == 409:
        if 'already' in msg_lower or 'exists' in msg_lower:
            return 'ResourceError.ALREADY_EXISTS'
        return 'ResourceError.CONFLICT'

    # 422 Unprocessable Entity
    if status_code == 422:
        if 'invalid' in msg_lower:
            return 'ValidationError.INVALID_INPUT'
        if 'missing' in msg_lower:
            return 'ValidationError.MISSING_REQUIRED_FIELD'
        return 'ValidationError.INVALID_FORMAT'

    # 500 Internal Server Error
    if status_code == 500:
        if 'service' in msg_lower or 'connection' in msg_lower:
            return 'ServiceError.CONNECTION_FAILED'
        if 'database' in msg_lower:
            return 'DatabaseError.QUERY_FAILED'
        return 'GeneralError.INTERNAL_ERROR'

    # 503 Service Unavailable
    if status_code == 503:
        return 'ServiceError.UNAVAILABLE'

    # Default fallback
    return 'GeneralError.UNKNOWN_ERROR'


def analyze_directory(directory: Path) -> Dict:
    """Analyze all Python files in directory"""
    results = {
        'files': {},
        'total_exceptions': 0,
        'by_status_code': defaultdict(int),
        'by_suggested_code': defaultdict(int),
    }

    for py_file in directory.rglob('*.py'):
        if 'venv' in str(py_file) or '__pycache__' in str(py_file):
            continue

        exceptions = find_http_exceptions(py_file)
        if exceptions:
            results['files'][str(py_file)] = exceptions
            results['total_exceptions'] += len(exceptions)

            for exc in exceptions:
                status = exc.get('status_code', '500')
                results['by_status_code'][status] += 1

                suggested = suggest_error_code(int(status), exc.get('message', ''))
                results['by_suggested_code'][suggested] += 1

    return results


def generate_migration_report(results: Dict, output_path: Path):
    """Generate migration report"""
    with open(output_path, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("Backend Error Code Migration Report\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"Total files with HTTPException: {len(results['files'])}\n")
        f.write(f"Total HTTPException usages: {results['total_exceptions']}\n\n")

        f.write("Breakdown by HTTP Status Code:\n")
        f.write("-" * 40 + "\n")
        for status, count in sorted(results['by_status_code'].items()):
            f.write(f"  {status}: {count}\n")

        f.write("\nSuggested Error Code Mappings:\n")
        f.write("-" * 40 + "\n")
        for code, count in sorted(results['by_suggested_code'].items(), key=lambda x: -x[1])[:20]:
            f.write(f"  {code}: {count}\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("Detailed File Analysis\n")
        f.write("=" * 80 + "\n\n")

        for file_path, exceptions in sorted(results['files'].items()):
            f.write(f"\n{file_path}\n")
            f.write("-" * 80 + "\n")

            for exc in exceptions:
                line = exc.get('line', '?')
                status = exc.get('status_code', exc.get('status_name', '?'))
                message = exc.get('message', '')
                suggested = suggest_error_code(int(status) if status.isdigit() else 500, message)

                f.write(f"  Line {line}: status_code={status}\n")
                f.write(f"    Message: {message[:60]}...\n" if len(message) > 60 else f"    Message: {message}\n")
                f.write(f"    Suggested: {suggested}\n\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("Migration Instructions\n")
        f.write("=" * 80 + "\n\n")
        f.write("""
1. Import the new exception classes:
   from backend.core.exceptions import NotFoundException, UnauthorizedException
   from backend.core.enums.error_codes import DefinitionError, AuthError

2. Replace HTTPException with new exception classes:

   OLD:
       raise HTTPException(status_code=404, detail="Definition not found")

   NEW:
       raise NotFoundException(DefinitionError.NOT_FOUND)

3. For errors with additional details:

   OLD:
       raise HTTPException(
           status_code=404,
           detail=f"Definition {definition_id} not found"
       )

   NEW:
       raise NotFoundException(
           DefinitionError.NOT_FOUND,
           details={"definition_id": definition_id}
       )

4. Run tests to verify all changes

5. Update frontend error handling:
   - Error responses now include "code" field
   - Use t(`errors.${error.code}`) for localized messages
""")


def main():
    """Main execution"""
    # Setup paths
    project_root = Path(__file__).parent.parent
    backend_dir = project_root / 'backend'
    report_path = project_root / 'docs' / 'ERROR_CODE_MIGRATION_REPORT.md'

    report_path.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("Backend Error Code Migration Analysis")
    print("=" * 80)
    print(f"\nScanning directory: {backend_dir}")

    # Analyze
    results = analyze_directory(backend_dir)

    print(f"\nFound {len(results['files'])} files with HTTPException")
    print(f"Total {results['total_exceptions']} HTTPException usages")

    # Generate report
    print(f"\nGenerating report: {report_path}")
    generate_migration_report(results, report_path)

    print("\n✓ Analysis complete!")
    print(f"\nNext steps:")
    print(f"  1. Review the migration report: {report_path}")
    print(f"  2. Update code to use new exception classes")
    print(f"  3. Update frontend to use error codes")


if __name__ == '__main__':
    main()
