#!/usr/bin/env python3

# Quick script to fix the response handling in orchestrator.py

import re

# Read the file
with open('orchestrator.py', 'r') as f:
    content = f.read()

# Fix the multi-agent response synthesis
content = re.sub(
    r'if financial_response\.get\("answer"\):',
    'if financial_response.get("answer") or financial_response.get("response"):',
    content
)

content = re.sub(
    r'answer_parts\.append\(f"\*\*Financial Analysis:\*\*\\n\{financial_response\[\'answer\'\]\}"\)',
    'answer_parts.append(f"**Financial Analysis:**\\n{financial_response.get(\'answer\', financial_response.get(\'response\', \'\'))}")',
    content
)

content = re.sub(
    r'if sales_response\.get\("answer"\):',
    'if sales_response.get("answer") or sales_response.get("response"):',
    content
)

content = re.sub(
    r'answer_parts\.append\(f"\*\*Sales & Marketing Insights:\*\*\\n\{sales_response\[\'answer\'\]\}"\)',
    'answer_parts.append(f"**Sales & Marketing Insights:**\\n{sales_response.get(\'answer\', sales_response.get(\'response\', \'\'))}")',
    content
)

# Write the file back
with open('orchestrator.py', 'w') as f:
    f.write(content)

print("Fixed response handling in orchestrator.py")
