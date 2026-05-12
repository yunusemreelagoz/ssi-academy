import requests
import json
import time
import random

BASE_URL = "http://127.0.0.1:8000/api/v1"

def print_step(step_name):
    print(f"\n{'-'*60}\n⚙️ ADIM: {step_name}\n{'-'*60}")

def run_test():
    print_step("Cüzdanlar (Agents) Başlatılıyor")
    requests.post(f"{BASE_URL}/agents/init", json={"alias": "ITU", "password": "123456", "role": "ENDORSER", "seed": "00000000000000000000000000000ITU"})
    requests.post(f"{BASE_URL}/agents/init", json={"alias": "Ziraat", "password": "123456", "role": "ENDORSER", "seed": "00000000000000000000000000Ziraat"})
    requests.post(f"{BASE_URL}/holder/init", json={"alias": "Ahmet", "password": "123456", "seed": "000000000000000000000000000Ahmet"})
    
    print_step("Şema ve Kimlik Tanımı Oluşturuluyor (Üniversite)")
    # Aynı şema adıyla çatışmamak için random isim
    schema_name = f"API Test Diploması v{random.randint(1000, 99999)}"
    
    res = requests.post(f"{BASE_URL}/schema/create", json={"agent_alias": "ITU", "schema_name": schema_name, "attributes": ["name", "department", "grade"], "version": "1.0"})
    if res.status_code != 200:
        print("❌ Schema Hatası:", res.json())
        return
    schema_id = res.json().get("schema_id")
    print(f"📝 Schema ID Oluştu: {schema_id}")
    
    print("⏳ Ledger onayı bekleniyor (5 saniye)...")
    time.sleep(5) 
    
    res = requests.post(f"{BASE_URL}/credential-definition/create", json={"agent_alias": "ITU", "schema_id": schema_id, "is_revokable": False})
    if res.status_code != 200:
        print("❌ CredDef Hatası:", res.json())
        return
    cred_def_id = res.json().get("cred_def_id")
    print(f"🔑 Credential Definition ID Oluştu: {cred_def_id}")
    
    if not cred_def_id:
        print("❌ HATA: Credential Definition ID 'None' döndü. Ağ hala senkronize olamadı.")
        return
        
    print("⏳ Ledger onayı bekleniyor (5 saniye)...")
    time.sleep(5) 
    
    print_step("Diploma İhraç Süreci (Üniversite -> Ahmet)")
    res = requests.post(f"{BASE_URL}/issuer/create-offer", json={"agent_alias": "ITU", "cred_def_id": cred_def_id})
    if res.status_code != 200:
        print("❌ Offer Hatası:", res.json())
        return
    offer_data = res.json()
    print("✉️ Teklif (Offer) Oluşturuldu")
    
    res = requests.post(f"{BASE_URL}/holder/create-request?agent_alias=Ahmet", json=offer_data["offer"])
    if res.status_code != 200:
        print("❌ Request Hatası:", res.json())
        return
    cred_req = res.json()["credential_request"]
    print("🙋‍♂️ Ahmet Teklifi Kabul Etti")
    
    cred_values = {"name": {"raw": "Ahmet Yılmaz", "encoded": "1"}, "department": {"raw": "Bilgisayar Müh.", "encoded": "2"}, "grade": {"raw": "3.85", "encoded": "3"}}
    res = requests.post(f"{BASE_URL}/issuer/issue-credential", json={"agent_alias": "ITU", "cred_request": cred_req, "credential_values": cred_values, "issuer_nonce": offer_data["issuer_nonce"]})
    if res.status_code != 200:
        print("❌ İşlem Hatası:", res.json())
        return
    credential = res.json()["credential"]
    print("🎖️ Üniversite Diplomayı İmzaladı")
    
    res = requests.post(f"{BASE_URL}/holder/store-credential?agent_alias=Ahmet", json=credential)
    if res.status_code != 200:
        print("❌ Cüzdana Kaydetme Hatası:", res.json())
        return
    print("💼 Ahmet Diplomayı Cüzdanına Kaydetti:", res.json().get("message"))

    print_step("ZKP Doğrulama Süreci (Ahmet -> Banka)")
    pres_req = {
        "name": "Banka C",
        "version": "1.0",
        "nonce": "123456",
        "requestedAttributes": {
            "attr1": {"name": "name", "restrictions": [{"cred_def_id": cred_def_id}]},
            "attr2": {"name": "grade", "restrictions": [{"cred_def_id": cred_def_id}]}
        },
        "requestedPredicates": {}
    }
    
    res = requests.post(f"{BASE_URL}/holder/create-presentation", json={"agent_alias": "Ahmet", "presentation_request": pres_req})
    if res.status_code != 200:
        print("❌ Sunum (Presentation) Hatası:", res.json())
        return
    presentation = res.json()["presentation"]
    print("📦 Ahmet ZKP Sunumunu Paketledi (Bölüm bilgisi gizlendi!)")
    
    res = requests.post(f"{BASE_URL}/verifier/verify-presentation", json={"agent_alias": "Ziraat", "presentation_request": pres_req, "presentation": presentation})
    if res.status_code != 200:
        print("❌ Doğrulama (Verify) Hatası:", res.json())
        return
    veri = res.json()
    
    print(f"\n✅ Doğrulama BAŞARILI MI?: {veri.get('is_valid')}")
    print(f"👀 Bankanın Görebildiği Veriler: {json.dumps(veri.get('revealed_data'), indent=2, ensure_ascii=False)}")
    print("\n🎉 BÜTÜN UÇTAN UCA SSI API AKIŞI HATASIZ ÇALIŞTI!")
    
if __name__ == '__main__':
    run_test()
