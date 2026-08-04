import asyncio
import json
import logging
import os
import redis.asyncio as redis
import traceback
import paramiko
import base64

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] Engine: %(message)s"
)

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))


async def engine_loop():
    logging.info(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}...")
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.subscribe("engine_tasks")
        logging.info("Subscribed to 'engine_tasks'. Engine is running.")

        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )
            if message:
                try:
                    task = json.loads(message["data"])
                    task_type = task.get("type")
                    logging.info(f"Received task: {task_type}")

                    if task_type == "inject_agent":
                        node_ip = task.get("ip")
                        username = task.get("username", "root")
                        password = task.get("password", "")
                        node_id = task.get("node_id")

                        logging.info(f"Injecting agent into {node_ip}...")
                        try:
                            # 1. Read agent code
                            agent_path = os.path.join(
                                os.path.dirname(__file__), "agents", "node_agent.py"
                            )
                            with open(agent_path, "r") as f:
                                agent_code = f.read()

                            # 2. Connect via SSH
                            ssh = paramiko.SSHClient()
                            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                            ssh.connect(
                                node_ip,
                                username=username,
                                password=password,
                                timeout=10,
                            )

                            # 3. Inject and run using base64 to avoid quoting hell
                            b64_code = base64.b64encode(
                                agent_code.encode("utf-8")
                            ).decode("utf-8")
                            cmd = f"echo {b64_code} | base64 -d > /tmp/nr_agent.py && python3 /tmp/nr_agent.py; rm /tmp/nr_agent.py"

                            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=15)
                            output = stdout.read().decode("utf-8").strip()

                            if output:
                                try:
                                    stats = json.loads(output)
                                    stats["node_id"] = node_id
                                    await r.publish(
                                        "live_alerts",
                                        json.dumps(
                                            {"type": "NODE_DATA", "data": stats}
                                        ),
                                    )
                                    logging.info(f"Agent data published for {node_ip}")
                                except json.JSONDecodeError:
                                    logging.error(
                                        f"Agent returned invalid JSON: {output}"
                                    )

                            ssh.close()
                        except Exception as e:
                            logging.error(f"Injection failed for {node_ip}: {e}")
                            await r.publish(
                                "live_alerts",
                                json.dumps(
                                    {
                                        "type": "NODE_ERROR",
                                        "node_id": node_id,
                                        "error": str(e),
                                    }
                                ),
                            )

                    elif task_type == "run_code":
                        # TODO: Implement isolated subprocess code execution
                        pass
                    else:
                        logging.warning(f"Unknown task type: {task_type}")
                except Exception as e:
                    logging.error(f"Error processing task: {e}")
                    traceback.print_exc()
    except asyncio.CancelledError:
        logging.info("Engine shutting down...")
    except Exception as e:
        logging.error(f"Engine crashed: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(engine_loop())
    except KeyboardInterrupt:
        pass
