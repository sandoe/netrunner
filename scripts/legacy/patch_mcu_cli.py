import json

with open("backend/scripts/nr_mcu_cli.py", "r") as f:
    code = f.read()

if "elif cmd == \"put\":" not in code:
    insert_str = """
        elif cmd == "put":
            import os
            local_path = args[0]
            remote_path = args[1]
            if os.path.isdir(local_path):
                for item in os.listdir(local_path):
                    lp = os.path.join(local_path, item)
                    rp = dev._join(remote_path, item) if hasattr(dev, '_join') else remote_path.rstrip('/') + '/' + item
                    if remote_path == "/": rp = "/" + item
                    dev.put(lp, rp, recursive=True)
            else:
                dev.put(local_path, remote_path, recursive=True)
            return json.dumps({"status": "ok"})
"""
    code = code.replace('elif cmd == "rm":', insert_str.lstrip('\n') + '        elif cmd == "rm":')
    with open("backend/scripts/nr_mcu_cli.py", "w") as f:
        f.write(code)
    print("Patched nr_mcu_cli.py")
