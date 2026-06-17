import re
import ast

def fix_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Find lines that assign `interrupt_cmd = f"..."` or `cmd = f"..."` or `cmds.append(f"...")`
    # We will use regex to find the string part: `python3 -c '...'`
    # and escape the double quotes inside the single quotes.
    
    # Actually, we can just replace `"` inside the single quotes with `\"`.
    # Wait, the single quotes enclose the python script.
    
    def replacer(match):
        # The python script is inside python3 -c '...'
        inner = match.group(1)
        # Any " inside inner should be escaped as \" for the python f-string
        # Let's replace any unescaped " with \"
        # We can just unescape all " first, then escape them all.
        inner = inner.replace('\\"', '"').replace('"', '\\"')
        return f"python3 -c '{inner}'"

    content = re.sub(r"python3\s+(?:-u\s+)?-c\s+'(.*?)'", replacer, content)

    # Let's also fix line 54 specifically because it has open(\"{path}\") which might have triple quotes now
    # If the file already has `"""import sys; ..."""` it'll become `\"\"\"import sys; ...\"\"\"` which is totally fine in an f-string!
    
    with open(filepath, 'w') as f:
        f.write(content)

fix_file('backend/routers/mcu.py')
fix_file('backend/routers/mcu_repl.py')
