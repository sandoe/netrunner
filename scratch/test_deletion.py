import sys
import os

# Adjust path to import backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.generators.network import gen_interface, gen_vlan_router

print("=== TESTING INTERFACE SETUP DELETION ===")
cfg_del_iface = {
    "interface": "eth0.100",
    "action": "delete_interface",
    "addresses": "10.0.100.1/24"
}
cmds_del_iface = gen_interface(cfg_del_iface)
for cmd in cmds_del_iface:
    print(cmd)

print("\n=== TESTING VLAN ROUTER DELETION ===")
vlans_test = [
    {"id": "10", "address": "10.0.10.1/24", "description": "Mgmt", "action": "add"},
    {"id": "20", "address": "10.0.20.1/24", "description": "User", "action": "del"}
]
cmds_vlan_router = gen_vlan_router("eth0", vlans_test)
for cmd in cmds_vlan_router:
    print(cmd)
