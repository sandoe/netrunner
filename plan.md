# Progress Bar & Stop Button Plan

1. Modify `backend/scripts/bruteforcer.py`
   - Use `subprocess.Popen` with `stdout.readline` loop.
   - Add `-V` to Hydra cmd for verbose output.
   - Parse `[DATA]` for total tries.
   - Parse `[ATTEMPT]` to increment counter.
   - Periodically `print(f"[PROGRESS] {attempt_count}/{total_tries}")` and `sys.stdout.flush()`.
   - On success, `print(f"[SUCCESS] {username}:{password}")`.

2. Modify `backend/routers/bruteforce.py`
   - Launch script with `nohup python3 ... > /tmp/netrunner-bruteforce.log 2>&1 &`
   - Replace blocking `run_command` with a polling loop inside `_run_attack_bg` that does `cat /tmp/netrunner-bruteforce.log` every 2 seconds.
   - Parse `[PROGRESS]` from log output to update `active_attacks[nid]["progress"]` and `"total"`.
   - If `[SUCCESS]` is found, finish attack and store creds.
   - Add `@router.post("/bruteforce/stop")` endpoint to kill the python script and hydra containers.

3. Modify `frontend/src/api/client.ts`
   - Add `stopAttack(node_id: string)` API call.

4. Modify `frontend/src/components/BruteforceControlRoom.vue`
   - Add Stop button to the Live Operations monitor rows.
   - Show a `<progress>` bar and percentage based on `status.progress / status.total`.
