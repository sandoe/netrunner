import sqlite3
import json

conn = sqlite3.connect('data/netrunner.db')
cursor = conn.cursor()
cursor.execute("SELECT id, name, device_type, metadata FROM nodes")
rows = cursor.fetchall()

print(f"{'ID':<15} | {'Name':<20} | {'Type':<10} | {'GNS3 Info'}")
print("-" * 70)
for row in rows:
    nid, name, dtype, meta_json = row
    meta = json.loads(meta_json) if meta_json else {}
    gns3 = meta.get('gns3', {})
    if dtype == 'windows' or 'win' in name.lower():
        gns3_str = f"Proj: {gns3.get('project_id', 'N/A')[:8]}... Node: {gns3.get('node_id', 'N/A')[:8]}..." if gns3 else "None"
        print(f"{nid:<15} | {name:<20} | {dtype:<10} | {gns3_str}")

conn.close()
