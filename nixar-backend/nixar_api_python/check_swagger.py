import urllib.request
import json
try:
    with urllib.request.urlopen("http://localhost:8000/openapi.json") as url:
        data = json.loads(url.read().decode())
        print(f"Swagger Version: {data.get('info', {}).get('version')}")
        endpoints = data.get("paths", {}).keys()
        print("Mevcut Endpointler:")
        for ep in endpoints:
            if "connections" in ep or "didcomm" in ep:
                print(f"✅ {ep}")
except Exception as e:
    print(f"API'ye ulaşılamadı: {e}")
