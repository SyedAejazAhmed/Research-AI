#!/usr/bin/env python3
"""
LaTeX Log Parser
Extracts errors and warnings from LaTeX compilation logs.
"""
import re
from typing import Dict, List


def parse_latex_log(log_content: str) -> Dict[str, List[str]]:
    """
    Parse LaTeX log file and extract errors and warnings.
    
    Args:
        log_content: Raw content of the .log file
    
    Returns:
        Dict with 'errors' and 'warnings' lists
    """
    errors = []
    warnings = []
    
    lines = log_content.split('\n')
    
    for i, line in enumerate(lines):
        # Match LaTeX errors
        if line.startswith('!'):
            error_msg = line[1:].strip()
            
            # Get additional context (next few lines)
            context = []
            for j in range(i + 1, min(i + 4, len(lines))):
                if lines[j].startswith('l.'):  # Line number indicator
                    context.append(lines[j])
                    break
                elif lines[j].strip():
                    context.append(lines[j])
            
            full_error = error_msg
            if context:
                full_error += " | " + " ".join(context)
            
            errors.append(full_error)
        
        # Match warnings
        elif 'Warning:' in line or 'warning:' in line:
            warnings.append(line.strip())
        
        # Match undefined references
        elif 'Undefined control sequence' in line:
            errors.append(f"Undefined control sequence: {line.strip()}")
        
        # Match missing files
        elif re.search(r'! LaTeX Error.*File.*not found', line):
            errors.append(line.strip())
    
    # Check for fatal errors in the summary
    if 'Fatal error occurred' in log_content:
        errors.append("Fatal error occurred during compilation")
    
    # Check if compilation was successful
    if '(see the transcript file for additional information)' in log_content:
        # This usually indicates errors were present
        pass
    
    return {
        "errors": errors,
        "warnings": warnings
    }


def format_error_report(parsed_log: Dict[str, List[str]]) -> str:
    """
    Format parsed log into human-readable error report.
    
    Args:
        parsed_log: Output from parse_latex_log()
    
    Returns:
        Formatted error report string
    """
    report = []
    
    if parsed_log["errors"]:
        report.append("=== ERRORS ===")
        for i, error in enumerate(parsed_log["errors"], 1):
            report.append(f"{i}. {error}")
        report.append("")
    
    if parsed_log["warnings"]:
        report.append("=== WARNINGS ===")
        for i, warning in enumerate(parsed_log["warnings"], 1):
            report.append(f"{i}. {warning}")
        report.append("")
    
    if not parsed_log["errors"] and not parsed_log["warnings"]:
        report.append("✅ No errors or warnings found")
    
    return "\n".join(report)


def extract_line_number(error: str) -> int:
    """
    Extract line number from LaTeX error message.
    
    Args:
        error: Error message string
    
    Returns:
        Line number or -1 if not found
    """
    match = re.search(r'l\.(\d+)', error)
    if match:
        return int(match.group(1))
    return -1


def categorize_error(error: str) -> str:
    """
    Categorize error into types for better handling.
    
    Args:
        error: Error message
    
    Returns:
        Error category string
    """
    error_lower = error.lower()
    
    if 'undefined control sequence' in error_lower:
        return 'undefined_command'
    elif 'file' in error_lower and 'not found' in error_lower:
        return 'missing_file'
    elif 'missing' in error_lower:
        return 'missing_character'
    elif 'environment' in error_lower:
        return 'environment_error'
    elif 'math' in error_lower:
        return 'math_error'
    elif 'reference' in error_lower or 'citation' in error_lower:
        return 'reference_error'
    else:
        return 'general_error'


def suggest_fix(error: str) -> str:
    """
    Suggest potential fixes based on error type.
    
    Args:
        error: Error message
    
    Returns:
        Suggestion string
    """
    category = categorize_error(error)
    
    suggestions = {
        'undefined_command': 'Check if the command is spelled correctly or if required package is loaded',
        'missing_file': 'Verify the file path and ensure the file exists in the workspace',
        'missing_character': 'Check for missing brackets, braces, or special characters',
        'environment_error': 'Ensure environment is properly opened and closed (\\begin{} and \\end{})',
        'math_error': 'Check math mode delimiters ($ or \\[ \\])',
        'reference_error': 'Run compilation again or check if \\label{} exists',
        'general_error': 'Review the LaTeX syntax around the error location'
    }
    
    return suggestions.get(category, 'Review the error and check LaTeX documentation')


if __name__ == "__main__":
    # Test with sample log content
    sample_log = """
This is pdfTeX, Version 3.141592653-2.6-1.40.25 (TeX Live 2023)
! Undefined control sequence.
l.12 \\invalidcommand
                     {test}
LaTeX Warning: Reference `fig:test' on page 1 undefined on input line 45.
! LaTeX Error: File `missing.sty' not found.
    """
    
    parsed = parse_latex_log(sample_log)
    print(format_error_report(parsed))
    
    for error in parsed["errors"]:
        print(f"\nError: {error}")
        print(f"Category: {categorize_error(error)}")
        print(f"Suggestion: {suggest_fix(error)}")
