import re
with open('backend/routers/mcu.py', 'r') as f:
    content = f.read()

# Replace \\" with \"
content = content.replace(r'\\"', r'\"')

# Wait, there's another place with \\\\\\\" which was left behind? Let's also clean that just in case.
content = content.replace(r'\\\\\"', r'\"')

with open('backend/routers/mcu.py', 'w') as f:
    f.write(content)
