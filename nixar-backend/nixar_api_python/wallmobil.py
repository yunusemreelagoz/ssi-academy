import requests
import json
import time
import base64

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


def demo_sign_verify():
    """
    Dağıtık Sign & Verify akışı:
    Holder (Mac:8000) veriyi imzalar → şifreler → Kurum'a gönderir (GCloud:8080) → Kurum açar & doğrular.
    Ön koşul: main() ile bağlantı kurulmuş olmalı.
    """
    print("\n" + "="*50)
    print("🔏 SIGN & VERIFY DEMO")
    print("="*50)

    # 1. Holder'ın aktif bağlantısını al
    res = requests.get(f"{HOLDER_URL}/api/v1/connections/list?agent_alias={HOLDER_ALIAS}")
    connections = res.json().get("connections", [])
    active = [c for c in connections if c.get("connection_state") == "Active" and c.get("their_did")]
    if not active:
        print("❌ Aktif bağlantı yok! Önce main() çalıştırın.")
        return

    holder_conn = active[-1]
    holder_my_did   = holder_conn["my_did"]
    holder_their_did = holder_conn["their_did"]
    print(f"✅ Holder my_did: {holder_my_did}")
    print(f"✅ Kurum their_did: {holder_their_did}")

    # 2. Kurum'un Holder'a bakan bağlantısını bul
    res = requests.get(f"{KURUM_URL}/api/v1/connections/list?agent_alias=ITU")
    kurum_conns = res.json().get("connections", [])
    kurum_active = [c for c in kurum_conns if c.get("connection_state") == "Active" and c.get("their_did")]
    if not kurum_active:
        print("❌ Kurum tarafında aktif bağlantı yok!")
        return

    kurum_conn = kurum_active[-1]
    kurum_my_did    = kurum_conn["my_did"]
    kurum_their_did = kurum_conn["their_did"]  # Holder'ın DID'i (Kurum bakış açısıyla)
    print(f"✅ Kurum my_did: {kurum_my_did}")
    print(f"✅ Holder their_did (Kurum bakış açısı): {kurum_their_did}")

    # 3. Holder imzalayacak veriyi hazırlar
    raw_data = "Ahmet Yılmaz - TC: 12345678901 - Diploma Talebi"
    signed_data_b64 = base64.b64encode(raw_data.encode()).decode()
    print(f"\n📝 İmzalanacak veri: {raw_data}")
    print(f"   Base64: {signed_data_b64}")

    # 4. Holder veriyi kendi DID'i ile imzalar
    print_step("ADIM 1: Holder Veriyi İmzalıyor")
    res = requests.post(f"{HOLDER_URL}/api/v1/messages/sign", json={
        "agent_alias": HOLDER_ALIAS,
        "from_did": holder_my_did,
        "data": signed_data_b64
    })
    sign_result = res.json()
    print(json.dumps(sign_result, indent=2))
    signature = sign_result["signature"]

    # 5. Holder imzayı DIDComm ile şifreler
    print_step("ADIM 2: Holder İmzayı Şifreli Mesaj Olarak Paketliyor")
    payload = {"signedData": signed_data_b64, "signature": signature}
    res = requests.post(f"{HOLDER_URL}/api/v1/messages/encrypt", json={
        "agent_alias": HOLDER_ALIAS,
        "from_did": holder_my_did,
        "their_did": holder_their_did,
        "message": payload
    })
    encrypt_result = res.json()
    encrypted_message = encrypt_result["encrypted_message"]
    print("Şifreli zarf oluşturuldu ✅")

    # 6. Kurum şifreli zarfı açar
    print_step("ADIM 3: Kurum Şifreli Mesajı Açıyor")
    res = requests.post(f"{KURUM_URL}/api/v1/messages/decrypt", json={
        "agent_alias": "ITU",
        "encrypted_message": encrypted_message
    })
    decrypt_result = res.json()
    print(json.dumps(decrypt_result, indent=2))
    decrypted = decrypt_result["decrypted_message"]
    content = json.loads(decrypted["content"]) if isinstance(decrypted["content"], str) else decrypted["content"]
    sender_did = decrypted.get("senderDid") or decrypted.get("sender_did")

    # 7. Kurum imzayı doğrular
    print_step("ADIM 4: Kurum İmzayı Doğruluyor")
    res = requests.post(f"{KURUM_URL}/api/v1/messages/verify-signature", json={
        "agent_alias": "ITU",
        "their_did": sender_did or kurum_their_did,
        "signed_data": content["signedData"],
        "signature": content["signature"]
    })
    verify_result = res.json()
    print(json.dumps(verify_result, indent=2))

    if verify_result.get("is_verified"):
        print("\n✅ BAŞARILI! İmza doğrulandı — Holder gerçekten o DID'in sahibi.")
    else:
        print("\n❌ İmza doğrulanamadı!")


def demo_webhook_connect():
    """
    /didcomm/{alias} webhook'u üzerinden doğrudan bağlantı kurma testi.
    Holder → conn_req üretir → /didcomm/ITU'ya POST eder → Kurum webhook'u kabul eder.
    """
    print("\n" + "="*50)
    print("🔗 WEBHOOK BAĞLANTI DEMO")
    print("="*50)

    # 1. Holder başlat
    print_step("1. Holder Başlatılıyor")
    res = requests.post(f"{HOLDER_URL}/api/v1/holder/init", json={
        "alias": HOLDER_ALIAS,
        "password": "123456",
        "seed": "000000000000000000000000000Mobil"
    })
    print(res.json().get("message", res.text))

    # 2. Kurum başlat
    print_step("2. Kurum Başlatılıyor")
    requests.post(f"{KURUM_URL}/api/v1/agents/init", json={
        "alias": "ITU",
        "password": "123456",
        "role": "ENDORSER",
        "seed": "00000000000000000000000000000ITU"
    })

    # 3. Kurum'dan davetiye al
    print_step("3. Davetiye Alınıyor")
    res = requests.post(f"{KURUM_URL}/api/v1/connections/create-invitation", json={
        "agent_alias": "ITU",
        "label": "İTÜ Webhook Testi",
        "endpoint_url": f"{KURUM_URL}/didcomm/ITU"
    })
    invitation = res.json().get("invitation")
    print(f"Davetiye: {json.dumps(invitation, indent=2, ensure_ascii=False)}")

    # 4. Holder davetiyeden conn_req üretir (karşı tarafa göndermez)
    print_step("4. Holder Connection Request Üretiyor")
    res = requests.post(f"{HOLDER_URL}/api/v1/holder/create-conn-request", json={
        "agent_alias": HOLDER_ALIAS,
        "invitation": invitation
    })
    conn_req = res.json().get("connection_request")
    print(f"conn_req anahtarları: {list(conn_req.keys())}")

    # 5. conn_req'i doğrudan /didcomm/ITU webhook'una POST et
    print_step("5. conn_req /didcomm/ITU Webhook'una POST Ediliyor")
    res = requests.post(f"{KURUM_URL}/didcomm/ITU", json=conn_req)
    webhook_resp = res.json()
    print(json.dumps(webhook_resp, indent=2, ensure_ascii=False))

    if "connection_response" not in webhook_resp and webhook_resp.get("status") != "success":
        print("❌ Webhook bağlantıyı kabul etmedi!")
        return

    conn_res = webhook_resp.get("connection_response", webhook_resp)

    # 6. Holder Kurum'dan gelen conn_res'i kabul eder
    print_step("6. Holder Connection Response'u Kabul Ediyor")
    res = requests.post(f"{HOLDER_URL}/api/v1/connections/accept-response", json={
        "agent_alias": HOLDER_ALIAS,
        "connection_response": conn_res
    })
    print(json.dumps(res.json(), indent=2, ensure_ascii=False))

    # 7. Bağlantıları kontrol et
    print_step("7. Bağlantılar Kontrol Ediliyor")
    res = requests.get(f"{HOLDER_URL}/api/v1/connections/list?agent_alias={HOLDER_ALIAS}")
    conns = res.json().get("connections", [])
    active = [c for c in conns if c.get("connection_state") == "Active" and c.get("their_did")]
    if active:
        print(f"\n✅ BAŞARILI! Webhook üzerinden bağlantı kuruldu. their_did: {active[-1]['their_did']}")
    else:
        print("\n❌ Aktif bağlantı yok")


    print("\n" + "="*50)
    print("🔗 WEBHOOK BAĞLANTI DEMO")
    print("="*50)

    # 1. Holder başlat
    print_step("1. Holder Başlatılıyor")
    res = requests.post(f"{HOLDER_URL}/api/v1/holder/init", json={
        "alias": HOLDER_ALIAS,
        "password": "123456",
        "seed": "000000000000000000000000000Mobil"
    })
    print(res.json().get("message", res.text))

    # 2. Kurum başlat
    print_step("2. Kurum Başlatılıyor")
    requests.post(f"{KURUM_URL}/api/v1/agents/init", json={
        "alias": "ITU",
        "password": "123456",
        "role": "ENDORSER",
        "seed": "00000000000000000000000000000ITU"
    })

    # 3. Kurum'dan davetiye al
    print_step("3. Davetiye Alınıyor")
    res = requests.post(f"{KURUM_URL}/api/v1/connections/create-invitation", json={
        "agent_alias": "ITU",
        "label": "İTÜ Webhook Testi",
        "endpoint_url": f"{KURUM_URL}/didcomm/ITU"
    })
    invitation = res.json().get("invitation")
    print(f"Davetiye alındı: {invitation.get('did')}")

    # 4. Holder davetiyeden conn_req üretir (local API'ye sor)
    print_step("4. Holder Connection Request Üretiyor")
    # Bunu doğrudan nixar üzerinden yapmak için holder/accept-invitation'ı
    # ama bu sefer endpoint'i webhook'a yönlendiriyoruz — invitation'daki endpoint zaten /didcomm/ITU
    # Holder local API'si conn_req üretip /didcomm/ITU'ya POST yapacak

    # Holder'ın connection_create_request'ini elde etmek için önce local bir endpoint lazım
    # Mevcut hold/accept-invitation zaten bunu yapıyor ama /api/v1/connections/accept-request'e gönderiyor
    # Biz manual akışı simüle edeceğiz: conn_req'i üret → /didcomm/ITU'ya POST et

    # Holder local API'sinden conn_req al (test_utils üzerinden)
    # Bunun için custom bir endpoint yok, bu yüzden /api/v1/holder/accept-invitation'ın
    # endpoint parsing'ini kullanıyoruz — invitation endpoint'i zaten /didcomm/ITU işaret ediyor
    # accept-invitation kodu endpoint'e parse ederek /api/v1/connections/accept-request'e gider
    # Biz ise direkt /didcomm/ITU'ya göndermek istiyoruz

    # Bunun için conn_req'i döndüren yeni bir endpoint eklemek yerine,
    # accept-invitation'ı çağırıp Kurum'un /didcomm/ITU'sundan yanıtı yakalayacağız.
    # Ama önce webhook'u test etmek için raw conn_req üretip doğrudan POST edelim.

    # Holder tarafında conn_req üretmek için internal endpoint yok; 
    # Bu nedenle /api/v1/holder/accept-invitation'ı kullanıyoruz — 
    # invitation endpoint'i /didcomm/ITU'ya işaret ettiğinden accept-invitation içindeki 
    # URL parsing'i /api/v1/connections/accept-request'e değil webhook'a gidecek şekilde
    # invitation'ı değiştirip test edeceğiz.

    # invitation endpoint'ini webhook URL ile değiştir (zaten /didcomm/ITU)
    # accept-invitation kodu:
    #   base_url = http://34.76.10.78:8080
    #   issuer_alias = ITU
    #   accept_url = base_url + /api/v1/connections/accept-request   ← bunu webhook ile değiştirelim
    
    # En temiz yaklaşım: invitation endpoint'ini /api/v1/connections/accept-request yerine
    # /didcomm/ITU'ya yönlendirmek için accept-invitation'da bir "use_webhook" seçeneği eklemek
    # ya da direkt conn_req'i webhook'a atmak.
    
    # Şimdilik: accept-invitation'ı çağırıyoruz ama Kurum tarafındaki log'dan webhook'un tetiklenip
    # tetiklenmediğini görmek için conn_req'i manuel olarak /didcomm/ITU'ya POST ediyoruz.
    
    # Holder'da conn_req üretip webhook'a atmak için geçici çözüm:
    # invitation endpoint'ini /didcomm/ITU olarak bırak, ama accept-invitation'ı çağırmak
    # yerine doğrudan webhook'u test etmek için raw POST yapalım.
    
    # Önce holder'da bir invitation'dan conn_req üretelim:
    # Bu için /api/v1/holder/create-conn-request gibi bir endpoint gerekir
    # Şimdilik accept-invitation'daki akışı simüle etmek için:
    # conn_req'i üretip webhook'a atmak için accept-invitation'ı kullanalım
    # ama invitation'daki endpoint'i direkt webhook URL olarak verelim.
    
    # invitation zaten endpoint: /didcomm/ITU içeriyor
    # accept-invitation → parse → base_url/api/v1/connections/accept-request'e gider
    # Bu testi gerçek webhook üzerinden yapmak için main.py'e yeni bir endpoint ekleyelim.
    
    print("ℹ️  Bu test için önce Holder'dan raw conn_req alınması gerekiyor.")
    print("   Bunun için /api/v1/holder/create-conn-request endpoint'i henüz yok.")
    print("   Şimdi mevcut accept-invitation akışını webhook üzerinden test ediyoruz...")
    
    # invitation endpoint'ini değiştirmeden accept-invitation çağır
    # Kurum sunucusunda webhook log'larını görmek için:
    res = requests.post(f"{HOLDER_URL}/api/v1/holder/accept-invitation", json={
        "agent_alias": HOLDER_ALIAS,
        "invitation": invitation
    })
    print("Yanıt:", json.dumps(res.json(), indent=2))

    # 5. Bağlantıları kontrol et
    print_step("5. Bağlantılar Kontrol Ediliyor")
    res = requests.get(f"{HOLDER_URL}/api/v1/connections/list?agent_alias={HOLDER_ALIAS}")
    conns = res.json().get("connections", [])
    active = [c for c in conns if c.get("connection_state") == "Active" and c.get("their_did")]
    if active:
        print(f"✅ Bağlantı aktif! their_did: {active[-1]['their_did']}")
    else:
        print("❌ Aktif bağlantı yok")

if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "connect"
    try:
        if mode == "sign":
            demo_sign_verify()
        elif mode == "webhook":
            demo_webhook_connect()
        else:
            main()
    except requests.exceptions.ConnectionError:
        print("❌ HATA: API çalışmıyor! Lütfen önce diğer terminalde 'python main.py' komutuyla sunucuyu başlatın.")
