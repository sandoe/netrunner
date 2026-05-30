import paramiko
import asyncio
import os

async def deploy_beacon_to_node(ip, username, password, target_server_ip, csi_mode, sample_rate, udp_port, node_id):
    def run_ssh():
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
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
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
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
