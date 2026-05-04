from fastapi import FastAPI
import subprocess

app = FastAPI(title="SSI Nixar Microservice (OpenShift Ready)")

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "SSI Nixar Blockchain API is running securely on OpenShift!",
        "endpoints": ["/setup-issuer", "/run-full-flow"]
    }

@app.post("/setup-issuer")
def setup_issuer():
    """1. Adım: Kurumun (İTÜ) blokzincire kaydı ve Schema basımı"""
    try:
        # Alt işlemi çağırıyoruz, standart çıktıyı yakalıyoruz
        result = subprocess.run(["python", "1-kurum-kurulumu.py"], capture_output=True, text=True, check=True)
        return {"status": "success", "logs": result.stdout.split("\n")}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "logs": e.stdout.split("\n"), "error": e.stderr}

@app.post("/run-full-flow")
def run_full_ssi_flow():
    """2. Adım: Kurum, Öğrenci ve Banka arasındaki uçtan uca Sıfır Bilgi İspatı (ZKP) testi"""
    try:
        result = subprocess.run(["python", "2-tam-ssi-akisi.py"], capture_output=True, text=True, check=True)
        return {"status": "success", "logs": result.stdout.split("\n")}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "logs": e.stdout.split("\n"), "error": e.stderr}
