import urllib.request
import json
req = urllib.request.urlopen("http://127.0.0.1:8000/api/bluetooth/devices")
data = json.loads(req.read())
print(json.dumps(data, indent=2))
