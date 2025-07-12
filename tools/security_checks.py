#!/usr/bin/env python3
"""
Security Checks for Amazon FBA Agent System v3.5

This module performs security validation including:
1. API key exposure detection
2. Sensitive data pattern scanning
3. Configuration security validation

Usage:
    python tools/security_checks.py --check-api-keys
    python tools/security_checks.py --scan-all
"""

import os
import re
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
import json


class SecurityChecker:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.absolute()
        
        # API key patterns to detect
        self.api_key_patterns = [
            # OpenAI API keys
            r'sk-[a-zA-Z0-9]{20}T3BlbkFJ[a-zA-Z0-9]{20}',
            r'sk-proj-[a-zA-Z0-9_-]{43,}',
            
            # GitHub tokens
            r'ghp_[a-zA-Z0-9]{36}',
            r'github_pat_[a-zA-Z0-9_]{82}',
            
            # AWS keys
            r'AKIA[0-9A-Z]{16}',
            r'aws_access_key_id\s*=\s*["\']?AKIA[0-9A-Z]{16}["\']?',
            
            # Generic API key patterns
            r'api[_-]?key["\'\s]*[:=]["\'\s]*[a-zA-Z0-9_-]{20,}',
            r'secret[_-]?key["\'\s]*[:=]["\'\s]*[a-zA-Z0-9_-]{20,}',
            r'private[_-]?key["\'\s]*[:=]["\'\s]*[a-zA-Z0-9_-]{20,}',
            
            # Database URLs with credentials
            r'[a-zA-Z][a-zA-Z0-9+.-]*://[a-zA-Z0-9_.-]+:[a-zA-Z0-9_.-]+@',
            
            # Email/password combinations
            r'password\s*[:=]\s*["\'][^"\']{8,}["\']',
        ]
        
        # Files to exclude from scanning
        self.exclude_patterns = [
            r'\.git/',
            r'archive/',
            r'archive_new/',
            r'logs/',
            r'OUTPUTS/',
            r'__pycache__/',
            r'\.pyc$',
            r'\.env$',  # .env files legitimately contain keys
            r'security_checks\.py$',  # This file contains patterns
        ]
        
        # Sensitive patterns for different contexts
        self.sensitive_patterns = {
            'credentials': [
                r'username\s*[:=]\s*["\'][^"\']+["\']',
                r'user\s*[:=]\s*["\'][^"\']+["\']',
                r'login\s*[:=]\s*["\'][^"\']+["\']',
            ],
            'urls': [
                r'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?',
            ],
            'file_paths': [
                r'[A-Za-z]:\\\\[^\\s"\'<>|?*]*',  # Windows paths
                r'/[a-zA-Z0-9._/-]+',  # Unix paths
            ]
        }
    
    def should_exclude_file(self, file_path: Path) -> bool:
        """Check if file should be excluded from scanning"""
        relative_path = file_path.relative_to(self.project_root)
        path_str = str(relative_path).replace('\\', '/')
        
        for pattern in self.exclude_patterns:
            if re.search(pattern, path_str):
                return True
        
        return False
    
    def scan_file_for_api_keys(self, file_path: Path) -> List[Dict]:
        """Scan a single file for API key patterns"""
        if self.should_exclude_file(file_path):
            return []
        
        findings = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            for line_num, line in enumerate(content.split('\n'), 1):
                for pattern in self.api_key_patterns:
                    matches = re.finditer(pattern, line, re.IGNORECASE)
                    for match in matches:
                        # Mask the key for reporting
                        matched_text = match.group()
                        if len(matched_text) > 10:
                            masked_key = matched_text[:4] + '*' * (len(matched_text) - 8) + matched_text[-4:]
                        else:
                            masked_key = '*' * len(matched_text)
                        
                        findings.append({
                            'file': str(file_path.relative_to(self.project_root)),
                            'line': line_num,
                            'pattern': pattern,
                            'matched_text': masked_key,
                            'context': line.strip()[:100] + '...' if len(line.strip()) > 100 else line.strip()
                        })
        
        except Exception as e:
            print(f"⚠️ Failed to scan {file_path}: {e}")
        
        return findings
    
    def scan_project_for_api_keys(self) -> Tuple[List[Dict], int]:
        """Scan entire project for API key exposure"""
        all_findings = []
        files_scanned = 0
        
        # Get all text files in the project
        for file_path in self.project_root.rglob('*'):
            if not file_path.is_file():
                continue
            
            # Skip binary files and large files
            if file_path.stat().st_size > 10 * 1024 * 1024:  # Skip files > 10MB
                continue
            
            # Check file extension
            if file_path.suffix in ['.exe', '.dll', '.so', '.dylib', '.bin', '.img', '.iso']:
                continue
            
            findings = self.scan_file_for_api_keys(file_path)
            all_findings.extend(findings)
            files_scanned += 1
        
        return all_findings, files_scanned
    
    def validate_env_file_security(self) -> List[Dict]:
        """Validate .env file security practices"""
        issues = []
        env_file = self.project_root / '.env'
        
        if not env_file.exists():
            return [{'severity': 'info', 'message': '.env file not found'}]
        
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for commented-out sensitive data
            for line_num, line in enumerate(content.split('\n'), 1):
                if line.strip().startswith('#') and any(pattern in line.lower() for pattern in ['key', 'secret', 'password', 'token']):
                    if len(line) > 50:  # Potentially commented-out real keys
                        issues.append({
                            'severity': 'warning',
                            'file': '.env',
                            'line': line_num,
                            'message': 'Potentially sensitive data in comment',
                            'context': line[:50] + '...'
                        })
            
            # Check for example values that might be real
            example_patterns = [
                r'your[_-]key[_-]here',
                r'replace[_-]with',
                r'example[_-]key',
            ]
            
            for line_num, line in enumerate(content.split('\n'), 1):
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.split('=', 1)
                    value = value.strip().strip('"\'')
                    
                    # Check if it looks like a real key (not an example)
                    is_example = any(re.search(pattern, value, re.IGNORECASE) for pattern in example_patterns)
                    
                    if 'key' in key.lower() and len(value) > 20 and not is_example:
                        # This might be a real key - validate format
                        if not any(re.match(pattern, value) for pattern in self.api_key_patterns):
                            issues.append({
                                'severity': 'info',
                                'file': '.env',
                                'line': line_num,
                                'message': f'Verify {key} is properly formatted',
                                'context': f'{key}=<{len(value)} chars>'
                            })
        
        except Exception as e:
            issues.append({
                'severity': 'error',
                'message': f'Failed to read .env file: {e}'
            })
        
        return issues
    
    def check_gitignore_coverage(self) -> List[Dict]:
        """Check if sensitive files are properly ignored"""
        issues = []
        gitignore_file = self.project_root / '.gitignore'
        
        required_patterns = [
            '.env',
            '*.log',
            '__pycache__/',
            '*.pyc',
            '.DS_Store',
            'Thumbs.db',
        ]
        
        sensitive_files = [
            '.env.local',
            '.env.production',
            'secrets.json',
            'credentials.json',
        ]
        
        if gitignore_file.exists():
            with open(gitignore_file, 'r', encoding='utf-8') as f:
                gitignore_content = f.read()
            
            # Check for required patterns
            for pattern in required_patterns:
                if pattern not in gitignore_content:
                    issues.append({
                        'severity': 'warning',
                        'message': f'Missing .gitignore pattern: {pattern}',
                        'recommendation': f'Add "{pattern}" to .gitignore'
                    })
        else:
            issues.append({
                'severity': 'error',
                'message': '.gitignore file not found',
                'recommendation': 'Create .gitignore with sensitive file patterns'
            })
        
        # Check if sensitive files exist and are tracked
        for sensitive_file in sensitive_files:
            file_path = self.project_root / sensitive_file
            if file_path.exists():
                # Check if it's tracked by git
                try:
                    result = os.system(f'cd "{self.project_root}" && git ls-files --error-unmatch "{sensitive_file}" 2>/dev/null')
                    if result == 0:  # File is tracked
                        issues.append({
                            'severity': 'critical',
                            'message': f'Sensitive file {sensitive_file} is tracked by git',
                            'recommendation': f'Add {sensitive_file} to .gitignore and remove from git history'
                        })
                except:
                    pass
        
        return issues
    
    def generate_security_report(self) -> Dict:
        """Generate comprehensive security report"""
        print("🔍 Running security checks...")
        
        # API key exposure scan
        print("📡 Scanning for API key exposure...")
        api_findings, files_scanned = self.scan_project_for_api_keys()
        
        # Environment file validation
        print("🔐 Validating environment file security...")
        env_issues = self.validate_env_file_security()
        
        # Git ignore coverage
        print("📝 Checking .gitignore coverage...")
        gitignore_issues = self.check_gitignore_coverage()
        
        report = {
            'scan_summary': {
                'files_scanned': files_scanned,
                'api_key_exposures': len(api_findings),
                'env_issues': len(env_issues),
                'gitignore_issues': len(gitignore_issues),
                'total_issues': len(api_findings) + len(env_issues) + len(gitignore_issues)
            },
            'api_key_findings': api_findings,
            'env_file_issues': env_issues,
            'gitignore_issues': gitignore_issues,
            'recommendations': self.generate_recommendations(api_findings, env_issues, gitignore_issues)
        }
        
        return report
    
    def generate_recommendations(self, api_findings: List, env_issues: List, gitignore_issues: List) -> List[str]:
        """Generate security recommendations based on findings"""
        recommendations = []
        
        if api_findings:
            recommendations.append("🚨 CRITICAL: API keys detected in code. Remove immediately and rotate affected keys.")
            recommendations.append("💡 Use environment variables or secure vaults for API keys")
            recommendations.append("📝 Add API key patterns to pre-commit hooks")
        
        if any(issue['severity'] == 'critical' for issue in gitignore_issues):
            recommendations.append("🚨 CRITICAL: Sensitive files are tracked by git. Remove from history immediately.")
        
        if env_issues:
            recommendations.append("🔐 Review .env file for security best practices")
            recommendations.append("📋 Ensure .env is in .gitignore")
        
        if not api_findings and not any(issue['severity'] == 'critical' for issue in gitignore_issues):
            recommendations.append("✅ No critical security issues detected")
            recommendations.append("🔄 Consider running security scans regularly")
        
        return recommendations
    
    def print_report(self, report: Dict):
        """Print formatted security report"""
        print("\n" + "="*60)
        print("🛡️ SECURITY SCAN REPORT")
        print("="*60)
        
        summary = report['scan_summary']
        print(f"📊 Files scanned: {summary['files_scanned']}")
        print(f"🔑 API key exposures: {summary['api_key_exposures']}")
        print(f"⚙️ Environment issues: {summary['env_issues']}")
        print(f"📝 Git ignore issues: {summary['gitignore_issues']}")
        print(f"📋 Total issues: {summary['total_issues']}")
        
        # API key findings
        if report['api_key_findings']:
            print(f"\n🚨 API KEY EXPOSURES ({len(report['api_key_findings'])})")
            print("-" * 40)
            for finding in report['api_key_findings']:
                print(f"📄 {finding['file']}:{finding['line']}")
                print(f"   Pattern: {finding['matched_text']}")
                print(f"   Context: {finding['context'][:80]}...")
                print()
        
        # Environment issues
        if report['env_file_issues']:
            print(f"\n🔐 ENVIRONMENT FILE ISSUES ({len(report['env_file_issues'])})")
            print("-" * 40)
            for issue in report['env_file_issues']:
                severity_icon = {'critical': '🚨', 'error': '❌', 'warning': '⚠️', 'info': 'ℹ️'}
                icon = severity_icon.get(issue['severity'], 'ℹ️')
                print(f"{icon} {issue['message']}")
                if 'context' in issue:
                    print(f"   Context: {issue['context']}")
                print()
        
        # Gitignore issues
        if report['gitignore_issues']:
            print(f"\n📝 GITIGNORE ISSUES ({len(report['gitignore_issues'])})")
            print("-" * 40)
            for issue in report['gitignore_issues']:
                severity_icon = {'critical': '🚨', 'error': '❌', 'warning': '⚠️', 'info': 'ℹ️'}
                icon = severity_icon.get(issue['severity'], 'ℹ️')
                print(f"{icon} {issue['message']}")
                if 'recommendation' in issue:
                    print(f"   Fix: {issue['recommendation']}")
                print()
        
        # Recommendations
        if report['recommendations']:
            print("\n💡 RECOMMENDATIONS")
            print("-" * 40)
            for rec in report['recommendations']:
                print(f"   {rec}")
        
        print("\n" + "="*60)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Security Checker for FBA Agent System')
    parser.add_argument('--check-api-keys', action='store_true',
                       help='Check for exposed API keys (exit 1 if found)')
    parser.add_argument('--scan-all', action='store_true',
                       help='Run comprehensive security scan')
    parser.add_argument('--output-json', help='Save report as JSON file')
    
    args = parser.parse_args()
    
    checker = SecurityChecker()
    
    if args.check_api_keys:
        # Quick API key check (for pre-commit hooks)
        findings, _ = checker.scan_project_for_api_keys()
        if findings:
            print(f"❌ {len(findings)} API key exposure(s) detected!")
            for finding in findings[:3]:  # Show first 3
                print(f"   {finding['file']}:{finding['line']}")
            if len(findings) > 3:
                print(f"   ... and {len(findings) - 3} more")
            sys.exit(1)
        else:
            print("✅ No API key exposures detected")
            sys.exit(0)
    
    elif args.scan_all or not any(vars(args).values()):
        # Full security scan
        report = checker.generate_security_report()
        checker.print_report(report)
        
        # Save JSON report if requested
        if args.output_json:
            with open(args.output_json, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
            print(f"\n📄 Report saved to: {args.output_json}")
        
        # Exit with error code if critical issues found
        has_critical = (
            report['scan_summary']['api_key_exposures'] > 0 or
            any(issue['severity'] == 'critical' for issue in report['gitignore_issues'])
        )
        
        sys.exit(1 if has_critical else 0)


if __name__ == "__main__":
    main()