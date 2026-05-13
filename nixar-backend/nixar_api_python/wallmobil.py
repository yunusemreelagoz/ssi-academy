import requests
import json
import time

HOLDER_URL = "http://127.0.0.1:8000"   # Mobil cüzdan (local)
KURUM_URL  = "http://34.76.10.78:8080" # Kurum/Issuer (uzak sunucu)
HOLDER_ALIAS = "MobilCuzdan"

def print_step(title):
    print(f"\n{'='*50}\n🚀 ADIM: {title}\n{'='*50}")

def main():
    print("📱 MOBİL CÜZDAN SİMÜLATÖRÜ BAŞLIYOR...")
    time.sleep(1)

    # 1. Mobil Cüzdanı Kur
    print_step("1. Mobil Cüzdan Başlatılıyor (Holder)")
    res = requests.post(f"{HOLDER_URL}/api/v1/holder/init", json={
        "alias": HOLDER_ALIAS,
        "password": "123456",
        "seed": "000000000000000000000000000Mobil"
    })
    print(json.dumps(res.json(), indent=2))
    
    # 2. Üniversiteyi (Kurumu) Kuralım ki bize davetiye üretebilsin (Normalde Kurum bunu kendi yapar)
    print_step("2. Kurum (ITU) Başlatılıyor")
    requests.post(f"{KURUM_URL}/api/v1/agents/init", json={
        "alias": "ITU",
        "password": "123456",
        "role": "ENDORSER",
        "seed": "00000000000000000000000000000ITU"
    })
    
    # 3. Davetiye Oluşturma (Üniversite portalında QR koda basıldığını varsayalım)
    print_step("3. Üniversiteden Davetiye (Invitation) İsteniyor")
    res = requests.post(f"{KURUM_URL}/api/v1/connections/create-invitation", json={
        "agent_alias": "ITU",
        "label": "İTÜ Öğrenci İşleri",
        "endpoint_url": f"{KURUM_URL}/didcomm/ITU"
    })
    print("Kurum Davetiye API Yanıtı:", res.text)
    invitation_data = res.json().get("raw_nixar_invitation", res.json().get("invitation"))
    print("Alınan Davetiye:")
    print(json.dumps(invitation_data, indent=2))

    # 4. Mobil Cüzdanın Davetiyeyi Kabul Etmesi (QR Okutma Simülasyonu)
    print_step("4. Mobil Cüzdan Davetiyeyi Kabul Ediyor (QR Okundu!)")
    res = requests.post(f"{HOLDER_URL}/api/v1/holder/accept-invitation", json={
        "agent_alias": HOLDER_ALIAS,
        "invitation": invitation_data  # Karekoddan çıkan datayı veriyoruz
    })
    print("Bağlantı Yanıtı:")
    print(json.dumps(res.json(), indent=2))

    # 5. Bağlantıları Kontrol Et
    print_step("5. Mobil Cüzdanındaki Aktif Bağlantılar Kontrol Ediliyor")
    res = requests.get(f"{HOLDER_URL}/api/v1/connections/list?agent_alias={HOLDER_ALIAS}")
    connections = res.json().get("connections", [])
    print(json.dumps(connections, indent=2))

    if connections:
        active = [c for c in connections if c.get("connection_state") == "Active" and c.get("their_did")]
        if active:
            print(f"\n✅ BAŞARILI! Kurumla bağlantı kuruldu. Kurumun DID'i: {active[-1].get('their_did')}")
        else:
            print("\n❌ BAĞLANTI KURULAMADI!")

    print("\nSimülasyon tamamlandı. İlerleyen aşamalarda buraya Credential Alma ve Presentation kısımları eklenebilir.")

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("❌ HATA: API çalışmıyor! Lütfen önce diğer terminalde 'python main.py' komutuyla sunucuyu başlatın.")
