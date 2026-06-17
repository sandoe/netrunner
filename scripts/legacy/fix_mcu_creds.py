import re

with open('backend/routers/mcu.py', 'r') as f:
    content = f.read()

# We need to find:
#     nodes = await load_nodes_db()
#     if node_id not in nodes:
#         raise HTTPException(status_code=404, detail="Node not found")
# And replace it with:
#     nodes = await load_nodes_db()
#     if node_id not in nodes:
#         raise HTTPException(status_code=404, detail="Node not found")
#     from ..core.vault import load_credentials
#     un, pw = await load_credentials(node_id)
#     nodes[node_id]["username"] = un
#     nodes[node_id]["password"] = pw

def replacer(match):
    return match.group(0) + """
    from ..core.vault import load_credentials
    un, pw = await load_credentials(node_id)
    nodes[node_id]["username"] = un
    nodes[node_id]["password"] = pw
"""

content = re.sub(
    r'nodes = await load_nodes_db\(\)\n\s+if node_id not in nodes:\n\s+raise HTTPException\(status_code=404, detail="Node not found"\)',
    replacer,
    content
)

with open('backend/routers/mcu.py', 'w') as f:
    f.write(content)

