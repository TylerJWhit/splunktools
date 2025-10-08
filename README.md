# Splunk Tools Collection

A collection of tools for Splunk administration, configuration management, and validation.

## Tools Overview

### KV Store Certificate Verifier (`kvcertverify/`)
A tool to verify KV Store certificate configurations for safe upgrades from Splunk KV Store 4/4.2 to 7.
- Checks SSL configuration settings
- Validates certificate chains
- Verifies compression settings
- Ensures upgrade compatibility

[Learn more about KV Store Certificate Verifier](kvcertverify/README.md)

### Splunk Config Checker (`splunk_config_checker/`)
A generic configuration checker for Splunk configurations that verifies settings across different conf files using rules defined in JSON.
- Flexible rule-based configuration validation
- Supports multiple Splunk configuration files
- Custom severity levels and messages
- Detailed reporting

[Learn more about Splunk Config Checker](splunk_config_checker/README.md)

### User Permissions Tools
- `splk_user_perms.py` - Check and manage Splunk user permissions
- `splk_user_perms_3.6.py` - Python 3.6 compatible version of the permissions tool

### Utility Scripts
- `find_duplicate_inputs.sh` - Identify duplicate input configurations
- `lookup_gen.sh` - Generate Splunk lookup files
- `testpeers.sh` - Test Splunk peer connections
- `New-LogEvent.ps1` - PowerShell script for creating Windows event log entries

## Installation

Most tools can be run directly from their respective directories. Some tools require Splunk's Python interpreter:

```bash
$SPLUNK_HOME/bin/python <script_name>.py [arguments]
```

## Requirements

- Splunk Enterprise installation
- Splunk's Python interpreter (for Python-based tools)
- PowerShell (for PS1 scripts)
- Bash shell (for shell scripts)

## Common Usage

### KV Store Certificate Verifier
```bash
cd kvcertverify
$SPLUNK_HOME/bin/python kv_cert_verifier.py $SPLUNK_HOME
```

### Configuration Checker
```python
from splunk_config_checker import SplunkConfigChecker
from pathlib import Path

checker = SplunkConfigChecker(
    splunk_home=Path("/opt/splunk"),
    rules_file=Path("splunk_config_checker/config_rules.json")
)
results = checker.check_configurations()
checker.print_results(results)
```

### User Permissions Check
```bash
$SPLUNK_HOME/bin/python splk_user_perms.py --user admin
```


## Authors

- Tyler Ezell - Initial work and maintenance