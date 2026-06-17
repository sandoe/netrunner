import re

def fix_mcu():
    with open('backend/routers/mcu.py', 'r') as f:
        content = f.read()

    # We want to prepend `pkill -9 -f 'mpremote.*{port}' || true; ` to `stty -F {port}` 
    # But only in the interrupt_cmd!
    # interrupt_cmd = f"stty -F {port} -hupcl;
    # Or: interrupt_cmd = f"stty -F {payload.port} -hupcl;
    
    def replacer(match):
        port_var = match.group(1)
        # return the full replaced string
        return f'interrupt_cmd = f"pkill -9 -f \'mpremote.*{{{port_var}}}\' || true; stty -F {{{port_var}}}'

    content = re.sub(r'interrupt_cmd = f"stty -F \{([^\}]+)\}', replacer, content)

    with open('backend/routers/mcu.py', 'w') as f:
        f.write(content)

fix_mcu()

# And let's fix mcu_repl.py to also use pkill -9 -f "mpremote.*{port}"
def fix_mcu_repl():
    with open('backend/routers/mcu_repl.py', 'r') as f:
        content = f.read()

    content = re.sub(
        r'kill_ch\.exec_command\(f"for pid in \$\(lsof -t .*?\); do kill -9 \$pid \|\| true; done"\)',
        r'kill_ch.exec_command(f"pkill -9 -f \'mpremote.*{port}\' || true")',
        content
    )

    with open('backend/routers/mcu_repl.py', 'w') as f:
        f.write(content)

fix_mcu_repl()
