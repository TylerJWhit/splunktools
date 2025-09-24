#!/opt/splunk/bin/splunk cmd python3
"""
Splunk Configuration Checker

This script validates Splunk configurations against golden/recommended values
using Splunk's btool utility and bash commands.

IMPORTANT: This script uses Splunk's packaged Python interpreter to ensure
compatibility with the Splunk environment and avoid path/dependency issues.

Usage:
    /opt/splunk/bin/splunk cmd python3 splunk_config_checker.py --config-file /path/to/config.txt
    /opt/splunk/bin/splunk cmd python3 splunk_config_checker.py --role search-head --splunk-home /opt/splunk
    /opt/splunk/bin/splunk cmd python3 splunk_config_checker.py --diag-file /path/to/diag.tar.gz
"""

import argparse
import subprocess
import sys
import os
import re
import tempfile
import tarfile
import shutil
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import json
import glob

class SplunkRole(Enum):
    """Enum for different Splunk server roles"""
    SEARCH_HEAD = "search-head"
    INDEXER = "indexer"
    CLUSTER_MANAGER = "cluster-manager"
    SHC_DEPLOYER = "shc-deployer"
    HTTP_EVENT_COLLECTOR = "http-event-collector"

@dataclass
class ConfigCheck:
    """Data class to represent a configuration check"""
    config_file: str
    stanza: str
    setting: str
    expected_value: str
    actual_value: Optional[str] = None
    status: str = "UNKNOWN"
    role: Optional[SplunkRole] = None

class SplunkConfigChecker:
    """Main class for checking Splunk configurations"""
    
    def __init__(self, splunk_home: str = None, diag_file: str = None):
        """
        Initialize the configuration checker
        
        Args:
            splunk_home: Path to Splunk installation directory
            diag_file: Path to Splunk diag file (.tar.gz) for offline analysis
        """
        self.diag_mode = diag_file is not None
        self.diag_temp_dir = None
        self.config_checks: List[ConfigCheck] = []
        
        if self.diag_mode:
            self.diag_file = diag_file
            self._extract_diag_file()
            # In diag mode, we don't need a live Splunk installation
            self.splunk_home = self._find_splunk_home_in_diag()
            self.btool_path = None  # No btool in diag mode
        else:
            self.splunk_home = splunk_home or self.find_splunk_home()
            self.btool_path = os.path.join(self.splunk_home, "bin", "splunk")
            # Validate Splunk installation only in live mode
            if not self.validate_splunk_installation():
                raise Exception(f"Invalid Splunk installation at {self.splunk_home}")
    
    def find_splunk_home(self) -> str:
        """
        Attempt to find Splunk home directory
        
        Returns:
            Path to Splunk home directory
        """
        common_paths = [
            "/opt/splunk",
            "/Applications/Splunk",
            "/usr/local/splunk",
            os.path.expanduser("~/splunk")
        ]
        
        # Check environment variable first
        if "SPLUNK_HOME" in os.environ:
            return os.environ["SPLUNK_HOME"]
        
        # Check common installation paths
        for path in common_paths:
            if os.path.exists(os.path.join(path, "bin", "splunk")):
                return path
        
        raise Exception("Could not find Splunk installation. Please specify --splunk-home")
    
    def _extract_diag_file(self) -> None:
        """
        Extract the diag file to a temporary directory
        """
        if not os.path.exists(self.diag_file):
            raise FileNotFoundError(f"Diag file not found: {self.diag_file}")
        
        try:
            # Create temporary directory
            self.diag_temp_dir = tempfile.mkdtemp(prefix="splunk_diag_")
            print(f"Extracting diag file to: {self.diag_temp_dir}")
            
            # Extract the tar.gz file
            with tarfile.open(self.diag_file, 'r:gz') as tar:
                tar.extractall(self.diag_temp_dir)
                
        except Exception as e:
            if self.diag_temp_dir and os.path.exists(self.diag_temp_dir):
                shutil.rmtree(self.diag_temp_dir)
            raise Exception(f"Failed to extract diag file: {e}")
    
    def _find_splunk_home_in_diag(self) -> str:
        """
        Find the Splunk home directory structure within the extracted diag
        
        Returns:
            Path to the Splunk configuration directory in the extracted diag
        """
        # Look for common diag directory patterns
        for root, dirs, files in os.walk(self.diag_temp_dir):
            # Look for etc/system directory which indicates Splunk config structure
            if 'etc' in dirs:
                etc_path = os.path.join(root, 'etc')
                if os.path.exists(os.path.join(etc_path, 'system')):
                    return root
        
        # If not found, return the temp directory and hope for the best
        return self.diag_temp_dir
    
    def __del__(self):
        """Cleanup temporary directories when object is destroyed"""
        if hasattr(self, 'diag_temp_dir') and self.diag_temp_dir and os.path.exists(self.diag_temp_dir):
            try:
                shutil.rmtree(self.diag_temp_dir)
            except Exception:
                pass  # Ignore cleanup errors
    
    def validate_splunk_installation(self) -> bool:
        """
        Validate that Splunk is properly installed
        
        Returns:
            True if valid installation, False otherwise
        """
        # Check if splunk binary exists and is executable
        if not os.path.exists(self.btool_path):
            print(f"Error: Splunk binary not found at {self.btool_path}")
            return False
            
        if not os.access(self.btool_path, os.X_OK):
            print(f"Error: Splunk binary at {self.btool_path} is not executable")
            return False
        
        # Try to run a simple btool command to verify it works
        try:
            result = subprocess.run(
                [self.btool_path, "btool", "server", "list", "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            print(f"Warning: Could not verify btool functionality")
            return True  # Continue anyway, we'll handle errors in run_btool_command
    
    def run_btool_command(self, config_file: str, stanza: str = None, setting: str = None) -> str:
        """
        Run splunk btool command to get configuration values, or read from diag files
        
        Args:
            config_file: Configuration file name (e.g., 'server', 'limits')
            stanza: Configuration stanza name (optional)
            setting: Specific setting name (optional)
            
        Returns:
            Command output as string
        """
        if self.diag_mode:
            return self._read_config_from_diag(config_file, stanza, setting)
        
        cmd = [self.btool_path, "btool", config_file, "list"]
        
        if stanza:
            cmd.append(stanza)
        
        try:
            # Check if we can run as the splunk user, otherwise try as current user
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                # If the command failed, try with different approaches
                if "Permission denied" in result.stderr or "cannot access" in result.stderr:
                    print(f"Warning: Permission denied accessing Splunk. Trying alternative methods...")
                    return self._try_alternative_config_access(config_file, stanza, setting)
                else:
                    print(f"Warning: btool command failed: {result.stderr}")
                    return ""
                
        except subprocess.TimeoutExpired:
            print(f"Warning: btool command timed out for {config_file}")
            return ""
        except subprocess.CalledProcessError as e:
            print(f"Error running btool command: {e}")
            print(f"Command: {' '.join(cmd)}")
            print(f"Error output: {e.stderr}")
            return ""
        except FileNotFoundError:
            print(f"Error: Splunk btool not found at {self.btool_path}")
            return ""
    
    def _try_alternative_config_access(self, config_file: str, stanza: str = None, setting: str = None) -> str:
        """
        Try alternative methods to access configuration when btool fails
        
        Args:
            config_file: Configuration file name
            stanza: Configuration stanza name
            setting: Specific setting name
            
        Returns:
            Configuration content or empty string
        """
        # Try to read configuration files directly from etc/system/default and etc/system/local
        config_paths = [
            os.path.join(self.splunk_home, "etc", "system", "local", f"{config_file}.conf"),
            os.path.join(self.splunk_home, "etc", "system", "default", f"{config_file}.conf"),
            os.path.join(self.splunk_home, "etc", "apps", "*", "local", f"{config_file}.conf"),
            os.path.join(self.splunk_home, "etc", "apps", "*", "default", f"{config_file}.conf")
        ]
        
        import glob
        combined_content = []
        
        for path_pattern in config_paths:
            for config_path in glob.glob(path_pattern):
                if os.path.exists(config_path) and os.access(config_path, os.R_OK):
                    try:
                        with open(config_path, 'r') as f:
                            content = f.read()
                            combined_content.append(f"# From: {config_path}")
                            combined_content.append(content)
                    except Exception as e:
                        print(f"Warning: Could not read {config_path}: {e}")
        
        return '\n'.join(combined_content)
    
    def _read_config_from_diag(self, config_file: str, stanza: str = None, setting: str = None) -> str:
        """
        Read configuration from extracted diag files
        
        Args:
            config_file: Configuration file name
            stanza: Configuration stanza name
            setting: Specific setting name
            
        Returns:
            Configuration content or empty string
        """
        config_paths = []
        
        # Look for configuration files in the diag extraction
        for root, dirs, files in os.walk(self.diag_temp_dir):
            for file in files:
                if file == f"{config_file}.conf":
                    config_paths.append(os.path.join(root, file))
        
        combined_content = []
        
        # Read all matching config files
        for config_path in config_paths:
            if os.path.exists(config_path) and os.access(config_path, os.R_OK):
                try:
                    with open(config_path, 'r') as f:
                        content = f.read()
                        combined_content.append(f"# From: {config_path}")
                        combined_content.append(content)
                        combined_content.append("")  # Add blank line between files
                except Exception as e:
                    print(f"Warning: Could not read {config_path}: {e}")
        
        return '\n'.join(combined_content)
    
    def parse_btool_output(self, output: str, target_stanza: str, target_setting: str) -> Optional[str]:
        """
        Parse btool output to extract specific setting value
        
        Args:
            output: Raw btool command output
            target_stanza: Stanza to look for
            target_setting: Setting to extract
            
        Returns:
            Setting value if found, None otherwise
        """
        current_stanza = None
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Check for stanza header
            if line.startswith('[') and line.endswith(']'):
                current_stanza = line[1:-1]  # Remove brackets
                continue
            
            # Check for setting in current stanza
            if current_stanza == target_stanza and '=' in line:
                setting, value = line.split('=', 1)
                setting = setting.strip()
                value = value.strip()
                
                if setting == target_setting:
                    return value
        
        return None
    
    def parse_config_file(self, config_file_path: str) -> None:
        """
        Parse the configuration file and extract expected values by role
        
        Args:
            config_file_path: Path to the configuration file
        """
        if not os.path.exists(config_file_path):
            raise FileNotFoundError(f"Configuration file not found: {config_file_path}")
        
        with open(config_file_path, 'r') as f:
            content = f.read()
        
        # Parse sections by role
        sections = self._split_by_roles(content)
        
        for role, section_content in sections.items():
            self._parse_role_section(role, section_content)
    
    def _split_by_roles(self, content: str) -> Dict[SplunkRole, str]:
        """
        Split configuration content by Splunk roles
        
        Args:
            content: Raw configuration file content
            
        Returns:
            Dictionary mapping roles to their configuration sections
        """
        sections = {}
        
        # Define role markers and their corresponding enum values
        role_markers = {
            "SEARCH HEADS": SplunkRole.SEARCH_HEAD,
            "INDEXERS": SplunkRole.INDEXER,
            "CLUSTER MANAGER": SplunkRole.CLUSTER_MANAGER,
            "SHC DEPLOYER": SplunkRole.SHC_DEPLOYER,
            "HTTP EVENT COLLECTOR RECEVIER INSTANCE": SplunkRole.HTTP_EVENT_COLLECTOR
        }
        
        lines = content.split('\n')
        current_role = None
        current_section = []
        
        for line in lines:
            line = line.strip()
            
            # Check for role start markers
            for marker, role in role_markers.items():
                if f"###BEGIN {marker}###" in line:
                    current_role = role
                    current_section = []
                    break
            
            # Check for role end markers
            if current_role and "###END" in line:
                if current_role not in sections:
                    sections[current_role] = []
                sections[current_role] = '\n'.join(current_section)
                current_role = None
                current_section = []
            elif current_role and line:
                current_section.append(line)
        
        return sections
    
    def _parse_role_section(self, role: SplunkRole, section_content: str) -> None:
        """
        Parse a role-specific configuration section
        
        Args:
            role: Splunk role enum
            section_content: Configuration content for the role
        """
        lines = section_content.split('\n')
        current_config_file = None
        current_stanza = None
        
        for line in lines:
            line = line.strip()
            
            if not line or line.startswith('#'):
                continue
            
            # Check for config file markers (e.g., ###distsearch.conf###)
            if line.startswith('###') and line.endswith('###') and '.conf' in line:
                current_config_file = line.strip('#').strip()
                continue
            
            # Check for stanza markers (e.g., [distributedSearch])
            if line.startswith('[') and line.endswith(']'):
                current_stanza = line[1:-1]  # Remove brackets
                continue
            
            # Check for setting = value pairs
            if '=' in line and current_config_file and current_stanza:
                setting, expected_value = line.split('=', 1)
                setting = setting.strip()
                expected_value = expected_value.strip()
                
                # Handle special cases like comments in expected values
                if '#' in expected_value:
                    expected_value = expected_value.split('#')[0].strip()
                
                # Skip empty values
                if not expected_value:
                    continue
                
                # Create configuration check object
                config_check = ConfigCheck(
                    config_file=current_config_file,
                    stanza=current_stanza,
                    setting=setting,
                    expected_value=expected_value,
                    role=role
                )
                
                self.config_checks.append(config_check)
    
    def check_configurations(self) -> None:
        """
        Check all parsed configurations against current Splunk settings
        """
        print(f"Checking {len(self.config_checks)} configuration settings...")
        
        for check in self.config_checks:
            # Get the base config filename (remove .conf extension)
            config_base = check.config_file.replace('.conf', '')
            
            # Run btool to get current value
            btool_output = self.run_btool_command(config_base, check.stanza)
            
            if btool_output:
                actual_value = self.parse_btool_output(btool_output, check.stanza, check.setting)
                check.actual_value = actual_value
                
                # Compare values
                if actual_value is None:
                    check.status = "MISSING"
                elif self._compare_values(actual_value, check.expected_value):
                    check.status = "OK"
                else:
                    check.status = "MISMATCH"
            else:
                check.status = "ERROR"
    
    def _compare_values(self, actual: str, expected: str) -> bool:
        """
        Compare actual and expected configuration values
        
        Args:
            actual: Actual configuration value
            expected: Expected configuration value
            
        Returns:
            True if values match, False otherwise
        """
        # Handle special cases
        if expected.lower() in ['auto', 'true', 'false']:
            return actual.lower() == expected.lower()
        
        # Handle numeric comparisons
        try:
            if '.' in actual or '.' in expected:
                return float(actual) == float(expected)
            else:
                return int(actual) == int(expected)
        except (ValueError, TypeError):
            pass
        
        # Default string comparison
        return actual.strip() == expected.strip()
    
    def print_results(self, output_format: str = "table") -> None:
        """
        Print configuration check results
        
        Args:
            output_format: Output format (table, json, csv)
        """
        if output_format == "json":
            self._print_json_results()
        elif output_format == "csv":
            self._print_csv_results()
        else:
            self._print_table_results()
    
    def _print_table_results(self) -> None:
        """Print results in table format"""
        if not self.config_checks:
            print("No configuration checks found.")
            return
        
        # Group by role for better organization
        by_role = {}
        for check in self.config_checks:
            role_name = check.role.value if check.role else "unknown"
            if role_name not in by_role:
                by_role[role_name] = []
            by_role[role_name].append(check)
        
        # Print results by role
        for role_name, checks in by_role.items():
            print(f"\n{'='*60}")
            print(f"ROLE: {role_name.upper()}")
            print(f"{'='*60}")
            
            # Print header
            print(f"{'Config File':<20} {'Stanza':<25} {'Setting':<30} {'Status':<10}")
            print(f"{'-'*20} {'-'*25} {'-'*30} {'-'*10}")
            
            for check in checks:
                status_color = {
                    'OK': '✓',
                    'MISMATCH': '✗',
                    'MISSING': '?',
                    'ERROR': '!',
                    'UNKNOWN': '-'
                }.get(check.status, '-')
                
                print(f"{check.config_file:<20} {check.stanza:<25} {check.setting:<30} {status_color} {check.status}")
                
                if check.status in ['MISMATCH', 'MISSING'] and check.actual_value is not None:
                    print(f"{'':>20} {'':>25} Expected: {check.expected_value}")
                    print(f"{'':>20} {'':>25} Actual:   {check.actual_value}")
                    print()
        
        # Print summary
        summary = self._get_summary()
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        for status, count in summary.items():
            print(f"{status}: {count}")
    
    def _print_json_results(self) -> None:
        """Print results in JSON format"""
        results = []
        for check in self.config_checks:
            results.append({
                'role': check.role.value if check.role else None,
                'config_file': check.config_file,
                'stanza': check.stanza,
                'setting': check.setting,
                'expected_value': check.expected_value,
                'actual_value': check.actual_value,
                'status': check.status
            })
        
        print(json.dumps(results, indent=2))
    
    def _print_csv_results(self) -> None:
        """Print results in CSV format"""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Role', 'Config File', 'Stanza', 'Setting', 'Expected Value', 'Actual Value', 'Status'])
        
        # Write data
        for check in self.config_checks:
            writer.writerow([
                check.role.value if check.role else '',
                check.config_file,
                check.stanza,
                check.setting,
                check.expected_value,
                check.actual_value or '',
                check.status
            ])
        
        print(output.getvalue())
    
    def _get_summary(self) -> Dict[str, int]:
        """Get summary statistics of check results"""
        summary = {'OK': 0, 'MISMATCH': 0, 'MISSING': 0, 'ERROR': 0, 'UNKNOWN': 0}
        
        for check in self.config_checks:
            if check.status in summary:
                summary[check.status] += 1
        
        return summary

def main():
    """Main function to run the configuration checker"""
    parser = argparse.ArgumentParser(
        description="Check Splunk configurations against golden/recommended values",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Check configurations from a golden config file (live environment)
    /opt/splunk/bin/splunk cmd python3 splunk_config_checker.py --config-file golden_config.txt

    # Check configurations from a Splunk diag file (offline analysis)
    /opt/splunk/bin/splunk cmd python3 splunk_config_checker.py --config-file golden_config.txt --diag-file /path/to/diag.tar.gz

    # Check configurations for a specific role only
    /opt/splunk/bin/splunk cmd python3 splunk_config_checker.py --config-file golden_config.txt --role search-head

    # Use specific Splunk installation
    /opt/splunk/bin/splunk cmd python3 splunk_config_checker.py --config-file golden_config.txt --splunk-home /opt/splunk

    # Output results in JSON format
    /opt/splunk/bin/splunk cmd python3 splunk_config_checker.py --config-file golden_config.txt --output-format json
        """
    )
    
    parser.add_argument(
        "--config-file",
        required=True,
        help="Path to configuration file with golden/expected values"
    )
    
    parser.add_argument(
        "--diag-file",
        help="Path to Splunk diag file (.tar.gz) for offline analysis (alternative to live environment)"
    )
    
    parser.add_argument(
        "--role",
        choices=[role.value for role in SplunkRole],
        help="Filter checks for specific Splunk server role only"
    )
    
    parser.add_argument(
        "--splunk-home",
        help="Path to Splunk installation directory (default: auto-detect)"
    )
    
    parser.add_argument(
        "--output-format",
        choices=["table", "json", "csv"],
        default="table",
        help="Output format for results (default: table)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse configuration file but don't run btool checks"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.diag_file and args.splunk_home:
        print("Warning: --splunk-home is ignored when using --diag-file")
    
    if args.diag_file and not args.diag_file.endswith(('.tar.gz', '.tgz')):
        print("Warning: Diag file should typically be a .tar.gz file")
    
    try:
        # Initialize the checker
        if args.diag_file:
            print(f"Initializing checker with diag file: {args.diag_file}")
            checker = SplunkConfigChecker(diag_file=args.diag_file)
        else:
            checker = SplunkConfigChecker(args.splunk_home)
        
        if args.verbose:
            if checker.diag_mode:
                print(f"Using diag file: {checker.diag_file}")
                print(f"Extracted to: {checker.diag_temp_dir}")
                print(f"Config directory: {checker.splunk_home}")
            else:
                print(f"Using Splunk installation at: {checker.splunk_home}")
                print(f"btool path: {checker.btool_path}")
        
        # Parse configuration file
        print(f"Parsing configuration file: {args.config_file}")
        checker.parse_config_file(args.config_file)
        
        # Filter by role if specified
        if args.role:
            role_filter = SplunkRole(args.role)
            checker.config_checks = [
                check for check in checker.config_checks 
                if check.role == role_filter
            ]
            print(f"Filtered to {len(checker.config_checks)} checks for role: {args.role}")
        
        if not checker.config_checks:
            print("No configuration checks found after parsing and filtering.")
            return
        
        if args.verbose:
            print(f"Found {len(checker.config_checks)} configuration checks")
        
        # Run checks (unless dry run)
        if not args.dry_run:
            mode_str = "diag file" if checker.diag_mode else "live environment"
            print(f"Running configuration checks against {mode_str}...")
            checker.check_configurations()
        else:
            print("Dry run mode - skipping configuration checks")
        
        # Print results
        print("\nResults:")
        checker.print_results(args.output_format)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()