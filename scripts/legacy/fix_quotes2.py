import re

def fix_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    def replacer(match):
        inner = match.group(1)
        # inner might contain \" or ', let's convert everything properly
        inner = inner.replace('\\"', '"')
        inner = inner.replace("'", '"')
        # If the inner python script contains {"something"}, the braces are for python f-string.
        # But wait, we're swapping quotes, what if it was {port}? It becomes "{port}" which is fine.
        return f"python3 -c '{inner}'"

    # Match `python3 -c \"...\"` or `python3 -u -c \"...\"`
    content = re.sub(r'python3\s+(?:-u\s+)?-c\s+\\"(.*?)\\"', replacer, content)

    with open(filepath, 'w') as f:
        f.write(content)

fix_file('backend/routers/mcu.py')
fix_file('backend/routers/mcu_repl.py')

# Also fix the pkill issue in mcu_repl.py
with open('backend/routers/mcu_repl.py', 'r') as f:
    repl = f.read()

repl = repl.replace(
    """kill_ch.exec_command(f"pkill -f 'mpremote connect {port}'")""",
    """kill_ch.exec_command(f"for pid in $(lsof -t {port} 2>/dev/null); do kill -9 $pid || true; done")"""
)

with open('backend/routers/mcu_repl.py', 'w') as f:
    f.write(repl)
