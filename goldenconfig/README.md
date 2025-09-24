# Splunk Configuration Checker

A Python script that validates Splunk configurations against golden/recommended values using Splunk's btool utility and bash commands.

## Features

- **Multi-role Support**: Check configurations for Search Heads, Indexers, Cluster Managers, SHC Deployers, and HTTP Event Collectors
- **Live and Offline Analysis**: Works with live Splunk environments or diag files for offline analysis
- **Automated Validation**: Uses Splunk btool to compare current configurations against expected values
- **Multiple Output Formats**: Table, JSON, and CSV output formats
- **Role Filtering**: Check configurations for specific Splunk roles only
- **Error Handling**: Graceful handling of permission issues and missing configurations
- **Alternative Access**: Falls back to direct config file reading when btool access is restricted

## Requirements

- Splunk Enterprise installation (for live analysis)
- Access to Splunk btool or diag files
- Splunk's packaged Python interpreter (recommended)

**Important**: This script should be run using Splunk's packaged Python interpreter to ensure compatibility with the Splunk environment and avoid path/dependency issues.

## Installation

1. Clone or download the script files
2. Ensure you have access to a Splunk installation or Splunk diag files
3. Script should be run using Splunk's packaged Python interpreter

## Usage

**Note**: All examples use Splunk's packaged Python interpreter. Replace `/opt/splunk` with your actual Splunk home directory.

### Basic Usage

Check all configurations from a golden config file (live environment):
```bash
/opt/splunk/bin/splunk cmd python3 splunk_config_checker.py --config-file golden_config.txt
```

### Offline Analysis with Diag Files

Check configurations using a Splunk diag file:
```bash
/opt/splunk/bin/splunk cmd python3 splunk_config_checker.py --config-file golden_config.txt --diag-file /path/to/diag.tar.gz
```

### Role-Specific Checks

Check configurations for search heads only:
```bash
/opt/splunk/bin/splunk cmd python3 splunk_config_checker.py --config-file golden_config.txt --role search-head
```

Check configurations for indexers:
```bash
/opt/splunk/bin/splunk cmd python3 splunk_config_checker.py --config-file golden_config.txt --role indexer
```

### Custom Splunk Installation

Specify custom Splunk home directory:
```bash
/opt/splunk/bin/splunk cmd python3 splunk_config_checker.py --config-file golden_config.txt --splunk-home /opt/splunk
```

### Different Output Formats

JSON output:
```bash
/opt/splunk/bin/splunk cmd python3 splunk_config_checker.py --config-file golden_config.txt --output-format json
```

CSV output:
```bash
/opt/splunk/bin/splunk cmd python3 splunk_config_checker.py --config-file golden_config.txt --output-format csv
```

### Dry Run Mode

Parse configuration file without running checks:
```bash
/opt/splunk/bin/splunk cmd python3 splunk_config_checker.py --config-file golden_config.txt --dry-run
```

### Verbose Output

Enable detailed logging:
```bash
/opt/splunk/bin/splunk cmd python3 splunk_config_checker.py --config-file golden_config.txt --verbose
```

## Command Line Options

- `--config-file`: **Required**. Path to configuration file with golden/expected values
- `--diag-file`: Path to Splunk diag file (.tar.gz) for offline analysis (alternative to live environment)
- `--role`: Filter checks for specific Splunk server role (`search-head`, `indexer`, `cluster-manager`, `shc-deployer`, `http-event-collector`)
- `--splunk-home`: Path to Splunk installation directory (auto-detected if not specified, ignored when using `--diag-file`)
- `--output-format`: Output format (`table`, `json`, `csv`). Default: `table`
- `--verbose`: Enable verbose output
- `--dry-run`: Parse configuration file but don't run checks

## Configuration File Format

The configuration file should follow this format:

```
###BEGIN SEARCH HEADS###

###server.conf###
[httpServer]
busyKeepAliveIdleTimeout = 120
streamInWriteTimeout = 30

[sslConfig]
useClientSSLCompression = false

###limits.conf###
[search]
remote_timeline_connection_timeout = 30
remote_timeline_send_timeout = 30

###END SEARCH HEADS###

###BEGIN INDEXERS###

###server.conf###
[clustering]
heartbeat_period = 10
cxn_timeout = 300

###END INDEXERS###
```

### Supported Roles

- `search-head`: Search Head configurations
- `indexer`: Indexer configurations
- `cluster-manager`: Cluster Manager configurations
- `shc-deployer`: Search Head Cluster Deployer configurations
- `http-event-collector`: HTTP Event Collector configurations

## Output

The script provides detailed output showing:

- ✓ **OK**: Configuration matches expected value
- ✗ **MISMATCH**: Configuration differs from expected value
- ? **MISSING**: Configuration setting not found
- ! **ERROR**: Error accessing configuration
- - **UNKNOWN**: Unable to determine status

For mismatches, both expected and actual values are displayed.

## Error Handling

The script handles various error conditions:

- **Permission Issues**: Falls back to direct config file reading
- **Missing Splunk Installation**: Clear error messages with suggestions
- **Invalid Configuration Files**: Detailed parsing error information
- **Network Timeouts**: Timeout handling for btool commands
- **Missing Configurations**: Distinguishes between missing settings and files

## Examples

### Example Output (Table Format)

```
============================================================
ROLE: SEARCH-HEAD
============================================================
Config File          Stanza                    Setting                        Status    
-------------------- ------------------------- ------------------------------ ----------
server.conf          httpServer                busyKeepAliveIdleTimeout       ✓ OK
server.conf          httpServer                streamInWriteTimeout           ✗ MISMATCH
                                              Expected: 30
                                              Actual:   60

server.conf          sslConfig                 useClientSSLCompression        ✓ OK
```

### Example Output (JSON Format)

```json
[
  {
    "role": "search-head",
    "config_file": "server.conf",
    "stanza": "httpServer",
    "setting": "busyKeepAliveIdleTimeout",
    "expected_value": "120",
    "actual_value": "120",
    "status": "OK"
  }
]
```

## Troubleshooting

### Common Issues

1. **Permission Denied**: Run as the splunk user or ensure read access to Splunk configuration files
2. **Splunk Not Found**: Use `--splunk-home` parameter to specify correct installation path
3. **btool Not Working**: The script will attempt to read configuration files directly

### Debug Mode

Use `--verbose` flag for detailed debugging information:
```bash
/opt/splunk/bin/splunk cmd python3 splunk_config_checker.py --config-file golden_config.txt --verbose
```

## Analysis Modes

### Live Environment Analysis
- Uses Splunk's btool utility to read current configurations
- Requires access to a running Splunk instance
- Best for real-time validation of active configurations

### Offline Diag Analysis
- Analyzes configuration files extracted from Splunk diag bundles
- No need for a running Splunk instance
- Ideal for troubleshooting and historical analysis
- Use `--diag-file` parameter with path to .tar.gz diag file

**Note**: This tool performs read-only analysis and never modifies Splunk configurations. It only generates logs, txt files, and reports.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is provided as-is for use with Splunk Enterprise environments.