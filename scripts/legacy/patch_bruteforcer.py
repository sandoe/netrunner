import re

def process_file():
    with open('/home/aso/Dokumenter/github/netrunner/backend/scripts/bruteforcer.py', 'r') as f:
        content = f.read()

    # Replace run_hydra_attack subprocess
    hydra_attack_old = """    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        output = res.stdout
        
        # Parse Hydra output:
        # [22][ssh] host: 192.168.1.17   login: admin   password: password
        match = re.search(r"login:\s+(\S+)\s+password:\s+(\S+)", output)
        if match:
            u, p = match.groups()
            log_result(target, service, True, u, p)
            return True
        else:
            log_result(target, service, False, error="Dictionary exhausted without success")
            return False
    except Exception as e:"""
    
    hydra_attack_new = """    try:
        proc = subprocess.Popen(cmd + ["-V"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        attempt_count = 0
        total_tries = len(credentials)
        
        import sys, json
        for line in iter(proc.stdout.readline, ''):
            if "[ATTEMPT]" in line:
                attempt_count += 1
                if attempt_count % 10 == 0:
                    print(f"[PROGRESS] {attempt_count}/{total_tries}")
                    sys.stdout.flush()
            
            match = re.search(r"login:\s+(\S+)\s+password:\s+(\S+)", line)
            if match:
                u, p = match.groups()
                log_result(target, service, True, u, p)
                proc.terminate()
                return True

        log_result(target, service, False, error="Dictionary exhausted without success")
        return False
    except Exception as e:"""
    content = content.replace(hydra_attack_old, hydra_attack_new)

    # Replace run_hydra_algo_attack subprocess
    algo_attack_old = """    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        output = res.stdout
        
        match = re.search(r"login:\s+(\S+)\s+password:\s+(\S+)", output)
        if match:
            u, p = match.groups()
            log_result(target, service, True, u, p)
            return True
        else:
            log_result(target, service, False, error="Algorithmic generation exhausted without success")
            return False
    except Exception as e:"""

    algo_attack_new = """    try:
        proc = subprocess.Popen(cmd + ["-V"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        attempt_count = 0
        total_tries = 0
        
        import sys, json
        for line in iter(proc.stdout.readline, ''):
            if "login tries" in line:
                m = re.search(r'(\d+)\s+login tries', line)
                if m: total_tries = int(m.group(1))
            
            if "[ATTEMPT]" in line:
                attempt_count += 1
                if attempt_count % 10 == 0:
                    if total_tries == 0: total_tries = attempt_count * 10 # Fallback
                    print(f"[PROGRESS] {attempt_count}/{total_tries}")
                    sys.stdout.flush()
            
            match = re.search(r"login:\s+(\S+)\s+password:\s+(\S+)", line)
            if match:
                u, p = match.groups()
                log_result(target, service, True, u, p)
                proc.terminate()
                return True

        log_result(target, service, False, error="Algorithmic generation exhausted without success")
        return False
    except Exception as e:"""
    content = content.replace(algo_attack_old, algo_attack_new)

    with open('/home/aso/Dokumenter/github/netrunner/backend/scripts/bruteforcer.py', 'w') as f:
        f.write(content)

process_file()
