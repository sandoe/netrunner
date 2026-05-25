import sys
sys.path.append("/home/aso/repos/projects/netrunner")

from backend.generators.network import gen_wireguard

def run_tests():
    # Test case 1: Snake case, normal string allowed_ips
    cfg1 = {
        "interface": "wg0",
        "private_key": "PRIV1",
        "address": "10.0.0.1/24",
        "peers": [
            {
                "public_key": "PUB1",
                "allowed_ips": "10.0.0.2/32, 192.168.1.0/24",
                "endpoint": "1.2.3.4:51820"
            }
        ]
    }
    cmds1 = gen_wireguard("wg0", cfg1)
    print("=== TEST 1 (SNAKE CASE, STRING ALLOWED IPS) ===")
    print("\n".join(cmds1))
    
    # Test case 2: Camel case, array allowedIPs, array DNS
    cfg2 = {
        "interface": "wg0",
        "privateKey": "PRIV2",
        "addresses": ["10.0.0.1/24", "fc00::1/64"],
        "dns": ["1.1.1.1", "8.8.8.8"],
        "peers": [
            {
                "publicKey": "PUB2",
                "allowedIPs": ["10.0.0.2/32", "192.168.2.0/24"],
                "persistentKeepalive": 25
            }
        ]
    }
    cmds2 = gen_wireguard("wg0", cfg2)
    print("\n=== TEST 2 (CAMEL CASE, ARRAY ALLOWED IPS & ADDRS & DNS) ===")
    print("\n".join(cmds2))

    # Test case 3: Pascal case, kebab case, array AllowedIPs
    cfg3 = {
        "interface": "wg0",
        "PrivateKey": "PRIV3",
        "Address": "10.0.0.1/24",
        "peers": [
            {
                "PublicKey": "PUB3",
                "AllowedIPs": ["10.0.0.3/32"]
            }
        ]
    }
    cmds3 = gen_wireguard("wg0", cfg3)
    print("\n=== TEST 3 (PASCAL CASE, ARRAY ALLOWED IPS) ===")
    print("\n".join(cmds3))

if __name__ == "__main__":
    run_tests()
