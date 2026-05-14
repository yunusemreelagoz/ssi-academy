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

def demo_credential_flow():
    """
    Tam Credential Issuance + Presentation akışı (webhook üzerinden).

    Akış:
      1.  Kurum schema + cred_def oluşturur (zaten varsa atlar)
      2.  Kurum prepare-offer çağırır → offer + cred_values sunucuda saklanır
      3.  Holder offer'dan credential request üretir
      4.  Holder cred_req'i MessageTypeCredentialRequest olarak şifreler → /didcomm/ITU'ya POST eder
      5.  Webhook otomatik credential imzalar → encrypted_credential döner
      6.  Holder credential'ı açar ve cüzdana kaydeder
      7.  Kurum prepare-presentation-request çağırır
      8.  Holder presentation oluşturur → MessageTypePresentation olarak şifreler → /didcomm/ITU'ya POST eder
      9.  Webhook otomatik doğrular → {is_valid, revealed_data} döner

    Kullanım: python3 wallmobil.py credential
    Ön koşul: Holder ve ITU arasında aktif bağlantı olmalı (önce 'webhook' veya 'connect' çalıştırın).
    """
    print("\n" + "="*60)
    print("🎓 KREDİ VERME + DOĞRULAMA DEMO (Webhook)")
    print("="*60)

    # ── Bağlantı bilgilerini al ──────────────────────────────────
    res = requests.get(f"{HOLDER_URL}/api/v1/connections/list?agent_alias={HOLDER_ALIAS}")
    conns = res.json().get("connections", [])
    active = [c for c in conns if c.get("connection_state") == "Active" and c.get("their_did")]
    if not active:
        print("❌ Aktif bağlantı yok! Önce 'python3 wallmobil.py webhook' çalıştırın.")
        return

    holder_conn    = active[-1]
    holder_my_did  = holder_conn["my_did"]
    holder_their   = holder_conn["their_did"]   # Kurum'un DID'i (Holder gözünden)

    res = requests.get(f"{KURUM_URL}/api/v1/connections/list?agent_alias=ITU")
    kurum_conns = res.json().get("connections", [])
    kurum_active = [c for c in kurum_conns if c.get("connection_state") == "Active" and c.get("their_did")]
    if not kurum_active:
        print("❌ Kurum tarafında aktif bağlantı yok!")
        return

    kurum_conn   = kurum_active[-1]
    kurum_my_did = kurum_conn["my_did"]
    kurum_their  = kurum_conn["their_did"]   # Holder'ın DID'i (Kurum gözünden)

    print(f"✅ Holder my_did   : {holder_my_did}")
    print(f"✅ Kurum  their_did: {holder_their}")

    # ── ADIM 1: Schema ──────────────────────────────────────────
    print_step("1. Schema Oluşturuluyor")
    import random, time as _time
    schema_ver = f"1.{random.randint(100,999)}"   # her seferinde farklı versiyon
    res = requests.post(f"{KURUM_URL}/api/v1/schema/create", json={
        "agent_alias": "ITU",
        "schema_name": "ITU_Diploma",
        "attributes": ["ad", "soyad", "departman", "mezuniyet_yili", "gpa"],
        "version": schema_ver
    })
    schema_resp = res.json()
    print(json.dumps(schema_resp, indent=2, ensure_ascii=False))
    if "schema_id" not in schema_resp:
        print("❌ Schema oluşturulamadı. Ledger erişimi kontrol edin.")
        return
    schema_id = schema_resp["schema_id"]

    # ── ADIM 2: Credential Definition ───────────────────────────
    print_step("2. Credential Definition Oluşturuluyor")
    res = requests.post(f"{KURUM_URL}/api/v1/credential-definition/create", json={
        "agent_alias": "ITU",
        "schema_id": schema_id,
        "is_revokable": False
    })
    cred_def_resp = res.json()
    print(json.dumps(cred_def_resp, indent=2, ensure_ascii=False))
    if "cred_def_id" not in cred_def_resp:
        print("❌ Credential Definition oluşturulamadı.")
        return
    cred_def_id = cred_def_resp["cred_def_id"]

    # ── ADIM 3: Kurum Offer Hazırlar (cred_values sunucuda saklanır) ──
    print_step("3. Kurum Credential Offer Hazırlıyor (prepare-offer)")
    diploma_values = {
        "ad":             {"raw": "Ahmet",                  "encoded": "1"},
        "soyad":          {"raw": "Yilmaz",                 "encoded": "2"},
        "departman":      {"raw": "Bilgisayar Muhendisligi", "encoded": "3"},
        "mezuniyet_yili": {"raw": "2024",                   "encoded": "2024"},
        "gpa":            {"raw": "3.5",                    "encoded": "35"},
    }
    res = requests.post(f"{KURUM_URL}/api/v1/issuer/prepare-offer", json={
        "agent_alias": "ITU",
        "cred_def_id": cred_def_id,
        "cred_values": diploma_values
    })
    offer_resp = res.json()
    print(json.dumps(offer_resp, indent=2, ensure_ascii=False))
    offer = offer_resp["offer"]

    # ── ADIM 4: Holder Credential Request Üretir ────────────────
    print_step("4. Holder Credential Request Üretiyor")
    res = requests.post(
        f"{HOLDER_URL}/api/v1/holder/create-request?agent_alias={HOLDER_ALIAS}",
        json=offer
    )
    cred_req_resp = res.json()
    cred_req = cred_req_resp["credential_request"]
    print("Credential Request oluşturuldu ✅")
    print(f"  Anahtarlar: {list(cred_req.keys())}")

    # ── ADIM 5: Holder cred_req'i doğrudan Kurum'a gönderir ────────────────────
    print_step("5. Holder Credential Request'i Kurum'a Gönderiyor")
    issue_res = requests.post(f"{KURUM_URL}/api/v1/issuer/issue-for-request", json={
        "agent_alias": "ITU",
        "cred_request": cred_req,
        "cred_def_id":  cred_def_id
    })
    issue_body = issue_res.json()
    print(f"Status: {issue_body.get('status')}")

    if issue_body.get("status") != "issued":
        print(f"❌ Credential issuance başarısız: {issue_body}")
        return
    credential = issue_body["credential"]
    print("✅ Credential Kurum tarafından imzalandı!")

    # ── ADIM 6: Holder Credential'ı Cüzdana Kaydeder ────────────────────────────
    print_step("6. Holder Credential'ı Cüzdana Kaydediyor")
    res = requests.post(
        f"{HOLDER_URL}/api/v1/holder/store-credential?agent_alias={HOLDER_ALIAS}",
        json=credential
    )
    print(json.dumps(res.json(), indent=2, ensure_ascii=False))
    print("✅ Diploma cüzdana kaydedildi!")

    # ── ADIM 7: Kurum Proof Request Hazırlar ────────────────────
    print_step("7. Kurum Presentation Request Hazırlıyor")
    pres_request = {
        "name":    "ITU_Diploma_Dogrulama",
        "version": "1.0",
        "nonce":   str(random.getrandbits(64)),
        "requestedAttributes": {
            "attr_ad":      {"name": "ad",             "restrictions": [{"cred_def_id": cred_def_id}]},
            "attr_dept":    {"name": "departman",      "restrictions": [{"cred_def_id": cred_def_id}]},
            "attr_yil":     {"name": "mezuniyet_yili", "restrictions": [{"cred_def_id": cred_def_id}]},
        },
        "requestedPredicates": {
            "pred_gpa": {"name": "gpa", "p_type": ">=", "p_value": 30, "restrictions": [{"cred_def_id": cred_def_id}]}
        }
    }
    res = requests.post(f"{KURUM_URL}/api/v1/verifier/prepare-presentation-request", json={
        "agent_alias": "ITU",
        "presentation_request": pres_request
    })
    print(json.dumps(res.json(), indent=2, ensure_ascii=False))

    # ── ADIM 8: Holder Presentation Oluşturur ve Doğrudan Gönderir ─────────────
    print_step("8. Holder Presentation Oluşturuyor → Kurum'a Gönderiyor")
    res = requests.post(f"{HOLDER_URL}/api/v1/holder/create-presentation", json={
        "agent_alias": HOLDER_ALIAS,
        "presentation_request": pres_request
    })
    pres_resp = res.json()
    if "presentation" not in pres_resp:
        print(f"❌ Presentation oluşturulamadı: {pres_resp}")
        return
    presentation = pres_resp["presentation"]
    print("Presentation oluşturuldu ✅")

    verify_res = requests.post(f"{KURUM_URL}/api/v1/verifier/submit-presentation", json={
        "agent_alias": "ITU",
        "presentation": presentation
    })
    verify_result = verify_res.json()

    # ── ADIM 9: Sonuç ───────────────────────────────────────────
    print_step("9. Doğrulama Sonucu")
    print(json.dumps(verify_result, indent=2, ensure_ascii=False))

    if verify_result.get("is_valid"):
        revealed = verify_result.get("revealed_data", {})
        print("\n🎉 DOĞRULAMA BAŞARILI!")
        print("   Kurum'un Gördükleri:")
        for k, v in revealed.items():
            print(f"     {k}: {v}")
        print("   GPA: GİZLİ — ama matematiksel olarak >= 3.0 kanıtlandı! 🔐")
    else:
        print("\n❌ DOĞRULAMA BAŞARISIZ!")



    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "connect"
    try:
        if mode == "sign":
            demo_sign_verify()
        elif mode == "webhook":
            demo_webhook_connect()
        elif mode == "credential":
            demo_credential_flow()
        else:
            main()
    except requests.exceptions.ConnectionError:
        print("❌ HATA: API çalışmıyor! Lütfen önce diğer terminalde 'python main.py' komutuyla sunucuyu başlatın.")
