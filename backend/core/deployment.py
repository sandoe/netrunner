import paramiko
import asyncio
import os

# Persisted trust store for SSH host keys (trust-on-first-use).
KNOWN_HOSTS = os.path.join("data", "known_hosts")


class _TofuPolicy(paramiko.MissingHostKeyPolicy):
    """Trust-on-first-use: accept and persist a host key the first time we see
    it, so later connections verify against it. A *changed* key for a known
    host is rejected by paramiko (BadHostKeyException) — i.e. MITM is caught."""

    def __init__(self, path):
        self.path = path

    def missing_host_key(self, client, hostname, key):
        client.get_host_keys().add(hostname, key.get_name(), key)
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            client.save_host_keys(self.path)
        except OSError:
            pass


def _make_ssh_client() -> paramiko.SSHClient:
    ssh = paramiko.SSHClient()
    try:
        ssh.load_host_keys(KNOWN_HOSTS)
    except (IOError, OSError):
        pass
    ssh.set_missing_host_key_policy(_TofuPolicy(KNOWN_HOSTS))
    return ssh


async def deploy_beacon_to_node(ip, username, password, target_server_ip, csi_mode, sample_rate, udp_port, node_id):
    def run_ssh():
        ssh = _make_ssh_client()
        try:
            ssh.connect(ip, username=username, password=password, timeout=60, banner_timeout=60, auth_timeout=60)
            
            # Read template
            with open("backend/core/beacon_script.py", "r") as f:
                script_content = f.read()
                
            # Replace variables
            script_content = script_content.replace("{{TARGET_IP}}", target_server_ip)
            script_content = script_content.replace("{{TARGET_PORT}}", str(udp_port))
            script_content = script_content.replace("{{CSI_MODE}}", csi_mode)
            script_content = script_content.replace("{{SAMPLE_RATE}}", str(sample_rate))
            script_content = script_content.replace("{{NODE_ID}}", str(node_id))
            
            # Create remote file
            sftp = ssh.open_sftp()
            with sftp.file("/tmp/netrunner_beacon.py", "w") as f:
                f.write(script_content)
            sftp.close()
            
            # Kill existing beacons and start new one
            ssh.exec_command("pkill -f netrunner_beacon.py")
            ssh.exec_command("nohup python3 /tmp/netrunner_beacon.py > /tmp/beacon.log 2>&1 &")
            
            return True, "Deployment successful"
        except Exception as e:
            return False, str(e)
        finally:
            ssh.close()
            
    # Run synchronous SSH in thread pool
    loop = asyncio.get_event_loop()
    success, message = await loop.run_in_executor(None, run_ssh)
    if not success:
        raise Exception(message)
    return message

async def stop_beacon_on_node(ip, username, password):
    def run_ssh():
        ssh = _make_ssh_client()
        try:
            ssh.connect(ip, username=username, password=password, timeout=60, banner_timeout=60, auth_timeout=60)
            # Kill existing beacons
            ssh.exec_command("pkill -f netrunner_beacon.py")
            return True, "Stopped successfully"
        except Exception as e:
            return False, str(e)
        finally:
            ssh.close()
            
    # Run synchronous SSH in thread pool
    loop = asyncio.get_event_loop()
    success, message = await loop.run_in_executor(None, run_ssh)
    if not success:
        raise Exception(message)
    return message

async def scrub_beacon_on_node(ip, username, password):
    def run_ssh():
        ssh = _make_ssh_client()
        try:
            ssh.connect(ip, username=username, password=password, timeout=60, banner_timeout=60, auth_timeout=60)
            # Kill and remove all traces
            ssh.exec_command("pkill -f netrunner_beacon.py")
            ssh.exec_command("rm -f /tmp/netrunner_beacon.py /tmp/beacon.log")
            ssh.exec_command("history -c")
            return True, "Scrubbed successfully"
        except Exception as e:
            return False, str(e)
        finally:
            ssh.close()
            
    loop = asyncio.get_event_loop()
    success, message = await loop.run_in_executor(None, run_ssh)
    if not success:
        raise Exception(message)
    return message
