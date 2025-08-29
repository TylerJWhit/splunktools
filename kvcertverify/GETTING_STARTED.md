#!/bin/bash

# Splunk KV Store Certificate Verification Tool - Getting Started Guide

cat << 'EOF'
🔍 Splunk KV Store Certificate Verification Tool
===============================================

This tool helps verify your KV Store certificate configuration before upgrading
from Splunk KV Store 4/4.2 to 7.

📋 What it checks:
• Certificate formats (PKCS8/PKCS12 for sslConfig)
• Certificate purposes (no purpose or dual purpose for kvstore)
• CA certificate chain validation
• SSL configuration settings (compression, renegotiation)
• SAN requirements (127.0.0.1/localhost for kvstore)
• Version compatibility requirements

🚀 Quick Start:

1. Install Python dependencies (for comprehensive checks):
   pip install -r requirements.txt

2. Run verification on your Splunk instance:
   
   # Comprehensive Python verification (recommended)
   python3 kv_cert_verifier.py /opt/splunk --verbose
   
   # Basic bash verification (no Python dependencies needed)
   ./kv_cert_verifier.sh /opt/splunk --verbose
   
   # Test the tool with simulated environment
   ./test_tool.sh

📁 Files included:
• kv_cert_verifier.py  - Main Python verification script
• kv_cert_verifier.sh    - Bash script for basic checks
• test_tool.sh         - Test script to validate tool functionality
• requirements.txt     - Python dependencies
• README.md           - Detailed documentation

🔧 Example usage:

# For a standard Splunk installation
python3 kv_cert_verifier.py /opt/splunk

# For Splunk in a custom location
python3 kv_cert_verifier.py /usr/local/splunk --verbose

# Using environment variable
export SPLUNK_HOME=/opt/splunk
python3 kv_cert_verifier.py $SPLUNK_HOME

# Basic checks only (no Python required)
./kv_cert_verifier.sh /opt/splunk --check

# Test the tool
./test_tool.sh

📊 Output examples:

✅ Success output:
✓ SSL Config section exists
✓ SSL compression enabled
✓ SSL renegotiation enabled
✓ SSL server certificate valid
✓ KV Store certificates valid
✓ All checks passed! Ready for upgrade.

❌ Issues found:
✗ SSL renegotiation disabled
✗ KV Store cert missing localhost in SAN
✗ Some checks failed. Review issues before upgrading.

🛠️ Common fixes:

1. Enable SSL settings in server.conf:
   [sslConfig]
   allowSslCompression = true
   allowSslRenegotiation = true

2. Add localhost to certificate SAN or disable verification:
   [kvstore]
   verifyServerName = false

3. Use proper certificate formats:
   - sslConfig: PKCS8 or PKCS12 format
   - kvstore: No purpose or dual purpose (client+server)

📖 For detailed documentation, see README.md

🧪 Test first: Always test in a non-production environment!

EOF
