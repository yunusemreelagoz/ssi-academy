# DIDComm Bağlantı ve Mesajlaşma Akışı Rehberi

## Sistemdeki Taraflar

```
┌─────────────────────────────┐        ┌─────────────────────────────┐
│         KURUM               │        │          HOLDER              │
│  (Issuer / Verifier)        │        │    (Vatandaş / Öğrenci)     │
│                             │        │                              │
│  Sunucu: 34.76.10.78:8080  │        │  Local: 127.0.0.1:8000      │
│  Dışarıdan erişilebilir    │        │  NAT arkasında, mobil        │
│  Cüzdan: ITU.json          │        │  Cüzdan: MobilCuzdan.json   │
└─────────────────────────────┘        └─────────────────────────────┘
```

---

## AŞAMA 1 — Davetiye Oluşturma

**Yapan:** Kurum  
**Ne zaman:** Öğrenci bağlantı kurmak istediğinde (portal sayfası açıldığında, QR bastırıldığında)

```
Kurum
  │
  ├─ POST /api/v1/connections/create-invitation
  │     {
  │       "agent_alias": "ITU",
  │       "label": "İTÜ Öğrenci İşleri",
  │       "endpoint_url": "http://34.76.10.78:8080/didcomm/ITU"
  │     }
  │
  │  [Nixar kütüphanesi içeride:]
  │  • Tek kullanımlık bir DID üretir
  │  • Bir anahtar çifti (public/private key) üretir
  │  • Bunları cüzdana kaydeder
  │
  └─ Dönen Davetiye:
       {
         "did": "AaVthTuv3pqUa8X9WmPscU",
         "endpoint": "http://34.76.10.78:8080/didcomm/ITU",  ← "cevabı buraya gönder"
         "recipient_keys": "6DmPfvd49NGp..."                 ← "benim public key'm"
       }
```

> **Not:** Bu noktada hiçbir ağ trafiği yoktur. Davetiye sadece Kurum'un cüzdanında durur.
> Holder'a QR kod, link veya JSON olarak iletilir.

---

## AŞAMA 2 — Connection Request Oluşturma

**Yapan:** Holder  
**Ne zaman:** QR kodu okuttuktan sonra, otomatik olarak

```
Holder
  │
  ├─ POST /api/v1/holder/create-conn-request
  │     {
  │       "agent_alias": "MobilCuzdan",
  │       "invitation": { ...davetiye... }
  │     }
  │
  │  [Nixar kütüphanesi içeride:]
  │  • Kendi DID ve anahtar çiftini üretir
  │  • Davetiyedeki "recipient_keys" (Kurum'un public key'i) ile
  │    Connection Request'i ŞIFRELER
  │  • Sadece Kurum'un private key'i ile açılabilir
  │
  └─ Dönen Şifreli Paket:
       {
         "cipherText": "Eu00e97IeEy...",
         "iv": "H9IOASw9...",
         "protectedSender": "eyJlbmMiOi...",
         "tag": "kn3es9dA..."
       }
```

> **Not:** Holder kendi DID ve anahtarlarını cüzdanına kaydetti.
> Şifreli paket transit sırasında kimse tarafından okunamaz.

---

## AŞAMA 3 — Connection Request Gönderme

**Yapan:** Holder → Kurum  
**Ne zaman:** Hemen, AŞAMA 2'nin ardından

İki farklı yol:

### Yol A: DIDComm (Gerçek Protokol) ✅
```
Holder
  │
  └─ POST http://34.76.10.78:8080/didcomm/ITU
          { ...şifreli conn_req... }

         ─────────── İnternet ───────────>

                                         Kurum
                                           │
                                           ├─ [Webhook tetiklendi]
                                           ├─ @type yok → conn_req dene
                                           ├─ connection_accept_request() çağır
                                           │   • Paketi private key ile açar
                                           │   • Holder'ın DID'ini tanır
                                           │   • Kendi Connection Response'unu üretir
                                           │   • Bunu da ŞIFRELER (Holder'ın public key'i ile)
                                           │
                                           └─ Döner:
                                                { "connection_response": { ...şifreli... } }
```

### Yol B: REST API (Kolaylık Endpoint'i)
```
Holder
  │
  └─ POST http://34.76.10.78:8080/api/v1/connections/accept-request
          {
            "agent_alias": "ITU",
            "connection_request": { ...şifreli conn_req... }
          }
```

> **Fark:** Yol A gerçek DIDComm protokolüdür — mobil uygulamalar bunu kullanır.
> Yol B bizim REST kolaylığımızdır — aynı işi yapar ama Kurum alias'ını URL'e gömmeniz gerekmez.

---

## AŞAMA 4 — Connection Response Kabul Etme

**Yapan:** Holder  
**Ne zaman:** Kurum'dan şifreli yanıt döndükten hemen sonra

```
Holder
  │
  ├─ POST /api/v1/connections/accept-response
  │     {
  │       "agent_alias": "MobilCuzdan",
  │       "connection_response": { ...Kurum'dan gelen şifreli yanıt... }
  │     }
  │
  │  [Nixar kütüphanesi içeride:]
  │  • Yanıtı kendi private key'i ile açar
  │  • Kurum'un DID'ini cüzdana kaydeder
  │
  └─ Cüzdanda artık:
       my_did    = "2enLPT4xXRUBCYfmbpXQv7"   (Holder'ın DID'i)
       their_did = "AaVthTuv3pqUa8X9WmPscU"   (Kurum'un DID'i)
```

```
                    ✅ BAĞLANTI AKTİF
     Her iki taraf birbirinin DID'ini tanıyor
     Her iki taraf birbirinin public key'ini biliyor
```

---

## AŞAMA 5 — Şifreli Mesaj Gönderme

**Yapan:** Holder veya Kurum (her ikisi de gönderebilir)  
**Ön koşul:** Bağlantı aktif olmalı

### 5A. Mesajı Şifrele

```
Holder
  │
  ├─ POST /api/v1/messages/encrypt
  │     {
  │       "agent_alias": "MobilCuzdan",
  │       "from_did":   "2enLPT4xXRUBCYfmbpXQv7",   ← connections/list'ten my_did
  │       "their_did":  "AaVthTuv3pqUa8X9WmPscU",   ← connections/list'ten their_did
  │       "message": { "text": "Diplomanızı talep ediyorum" }
  │     }
  │
  │  [Nixar kütüphanesi içeride:]
  │  • their_did'in public key'ini cüzdandan okur
  │  • Mesajı bu public key ile şifreler
  │  • Sadece their_did'in private key'i açabilir
  │
  └─ Döner: { "encrypted_message": { "cipherText": "...", "iv": "...", ... } }
```

### 5B. Şifreli Zarfı Karşı Tarafa İlet

```
Holder
  │
  └─ POST http://34.76.10.78:8080/didcomm/ITU
          { ...encrypted_message... }
```

---

## AŞAMA 6 — Şifreli Mesajı Açma

**Yapan:** Kurum  

```
Kurum (Webhook otomatik tetiklenir)
  │
  ├─ /didcomm/ITU'ya şifreli mesaj geldi
  ├─ connection_decrypt() çağır
  │   • Kendi private key'i ile zarfı açar
  │   • Gönderenin DID'ini doğrular (senderDid)
  │
  └─ Sonuç:
       {
         "content": "{ \"text\": \"Diplomanızı talep ediyorum\" }",
         "messageType": "MessageTypeSimple",
         "senderDid": "2enLPT4xXRUBCYfmbpXQv7"   ← Holder'ın DID'i
       }
```

---

## Tam Akış — Özet Diyagram

```
KURUM                                              HOLDER
  │                                                   │
  │◄──── 1. Davetiye oluştur (offline) ───────────────│
  │      (QR / link olarak ilet)                      │
  │                                                   │
  │                              2. conn_req oluştur ─┤
  │                                                   │
  │◄──── 3. POST /didcomm/ITU (conn_req) ─────────────│
  │                                                   │
  │ 4. Kabul et + conn_res üret                       │
  │                                                   │
  │───── conn_res ────────────────────────────────────►│
  │                                                   │
  │                         5. conn_res'i kabul et ───┤
  │                                                   │
  │         ✅ BAĞLANTI AKTİF (her iki taraf)         │
  │                                                   │
  │◄──── 6. POST /didcomm/ITU (şifreli mesaj) ────────│
  │                                                   │
  │ 7. Aç, içeriği oku                                │
  │                                                   │
```

---

## API Endpoint Özeti

### Bağlantı Kurma

| Adım | Endpoint | Yapan | Açıklama |
|------|----------|-------|----------|
| 1 | `POST /api/v1/connections/create-invitation` | Kurum | Davetiye oluştur |
| 2 | `POST /api/v1/holder/create-conn-request` | Holder | conn_req üret |
| 3A | `POST /didcomm/{alias}` | Holder→Kurum | Webhook (DIDComm — gerçek protokol) |
| 3B | `POST /api/v1/connections/accept-request` | Holder→Kurum | REST alternatifi |
| 4 | *(webhook otomatik yapar)* | Kurum | conn_res üret |
| 5 | `POST /api/v1/connections/accept-response` | Holder | Bağlantıyı tamamla |

### Credential İhracı (Issuance)

| Adım | Endpoint | Yapan | Açıklama |
|------|----------|-------|----------|
| 6 | `POST /api/v1/issuer/prepare-offer` | Kurum | Offer oluştur + cred_values sakla |
| 7 | *(QR / link aracılığıyla)* | Kurum→Holder | Offer'ı Holder'a ilet |
| 8 | `POST /didcomm/{alias}` | Holder→Kurum | Webhook: CredentialRequest gönder |
| 9 | *(webhook otomatik yapar)* | Kurum | Credential imzala + şifreli gönder |
| 10 | `POST /didcomm/{alias}` | Kurum→Holder webhook | Credential al + cüzdana kaydet |

### Doğrulama (Verification)

| Adım | Endpoint | Yapan | Açıklama |
|------|----------|-------|----------|
| 11 | `POST /api/v1/verifier/prepare-presentation-request` | Kurum | Proof request oluştur + sakla |
| 12 | *(QR / link aracılığıyla)* | Kurum→Holder | Proof request'i Holder'a ilet |
| 13 | `POST /didcomm/{alias}` | Holder→Kurum | Webhook: Presentation gönder |
| 14 | *(webhook otomatik yapar)* | Kurum | `verifier_verify_presentation()` → sonuç |

### Mesajlaşma (Şifreli)

| Endpoint | Yapan | Açıklama |
|----------|-------|----------|
| `POST /api/v1/messages/encrypt` | Holder/Kurum | Mesajı şifrele |
| `POST /didcomm/{alias}` | Holder→Kurum | Şifreli mesajı ilet (webhook açar) |
| `POST /api/v1/messages/decrypt` | Kurum | Manuel açma (test için) |
| `POST /api/v1/messages/sign` | Holder/Kurum | DID ile imzala |
| `POST /api/v1/messages/verify-signature` | Kurum/Holder | İmzayı doğrula |

---

## Güvenlik Notları

- **Tüm mesajlar şifrelidir** — transit sırasında kimse içeriği okuyamaz
- **Kimlik doğrulama DID tabanlıdır** — merkezi bir sunucu yoktur
- **Private key cüzdandan çıkmaz** — Nixar kütüphanesi tüm kriptografik işlemleri cüzdan içinde yapar
- **Her bağlantı benzersiz DID çifti kullanır** — bağlantılar birbirinden izole edilmiştir

---

## Gerçek Senaryo: Holder-Initiated Akış

### NAT Problemi ve Çözümü

Holder genellikle NAT arkasında (mobil, ev ağı) olduğu için Issuer Holder'a doğrudan HTTP bağlantısı kuramaz:

```
Issuer → POST http://holder-ip/didcomm/...  ❌ ÇALIŞMAZ
                                               (NAT, firewall, dinamik IP)
```

**Çözüm:** Her adımda **Holder harekete geçer**, Issuer bekler ve cevap verir. Issuer hiçbir zaman Holder'a doğrudan bağlanmaya çalışmaz. Proof Request, Credential Offer gibi talepler **QR kod veya deep-link** içinde Holder'a iletilir; Holder bunları okuyunca ne yapacağını bilir ve kendi başlatır.

---

### Tam Holder-Initiated Akış

```
ISSUER (34.76.10.78)                              HOLDER (Mobil / Mac)
       │                                                  │
       │  ════════ AŞAMA 1: BAĞLANTI KURMA ════════       │
       │                                                  │
       │  1. POST /connections/create-invitation          │
       │     → Davetiye oluştur, QR'a bas                 │
       │                              2. QR'ı tara ───────┤
       │                              3. POST /holder/    │
       │                                 create-conn-req  │
       │◄─── POST /didcomm/ITU (şifreli conn_req) ────────│
       │  4. [Webhook] connection_accept_request()        │
       │     → conn_res üret                              │
       │─── şifreli conn_res ─────────────────────────────►│
       │                              5. POST /connections/│
       │                                 accept-response  │
       │         ✅ BAĞLANTI AKTİF                        │
       │                                                  │
       │  ════════ AŞAMA 2: KREDİ VERME ════════          │
       │                                                  │
       │  6. POST /issuer/prepare-offer                   │
       │     { cred_def_id, cred_values }                 │
       │     → offer oluştur + sunucuda sakla             │
       │     → offer'ı QR'a bas / linke göm               │
       │                                                  │
       │                        7. QR'ı tara, offer al ───┤
       │                        8. [Webhook tetiklenir]   │
       │◄─── POST /didcomm/ITU (MessageTypeCredReq) ──────│
       │  9. [Webhook] pending_offers'dan bul             │
       │     issuer_create_credential() → imzala          │
       │─── MessageTypeCredential (şifreli) ─────────────►│
       │                        10. [Holder webhook]      │
       │                            prover_store_cred()   │
       │         ✅ KREDİ HOLDER'IN CÜZDANINDA            │
       │                                                  │
       │  ════════ AŞAMA 3: DOĞRULAMA ════════            │
       │                                                  │
       │  11. POST /verifier/prepare-presentation-request │
       │      { presentation_request }                    │
       │      → sunucuda sakla, QR'a bas                  │
       │                                                  │
       │                       12. QR'ı tara, req al ─────┤
       │                       13. [Webhook tetiklenir]   │
       │◄─── POST /didcomm/ITU (MessageTypePresReq gönderir│
       │                           presentation)  ────────│
       │  14. [Webhook] pending_requests'ten bul          │
       │      verifier_verify_presentation()              │
       │─── { "is_valid": true, "revealed_data": {...} } ─►│
       │         ✅ DOĞRULAMA TAMAMLANDI                  │
```

> **Not:** 9, 10, 14. adımlar webhook tarafından **otomatik** yönetilir.
> Manuel REST çağrısı gerekmez — Holder sadece `/didcomm/ITU`'ya gönderir, geri kalanı sunucu halleder.

### QR / Deep-Link İçeriği

| Aşama | Endpoint (Issuer'da) | QR / Link İçeriği |
|-------|----------------------|-------------------|
| Bağlantı (Adım 1) | `POST /connections/create-invitation` | `{ did, endpoint, recipient_keys }` |
| Kredi Teklifi (Adım 6) | `POST /issuer/prepare-offer` | `offer` objesi (cred_def_id + nonce) |
| Proof Request (Adım 11) | `POST /verifier/prepare-presentation-request` | `presentation_request` objesi |

### Webhook Otomasyonu

Holder sadece `/didcomm/ITU`'ya mesaj gönderir — webhook `messageType`'a göre her şeyi otomatik yapar:

| messageType | Webhook Ne Yapıyor |
|---|---|
| *(şifresiz, @type'sız)* | `connection_accept_request()` → conn_res döner |
| `MessageTypeCredentialRequest` | `pending_offers`'dan bul → `issuer_create_credential()` → şifreli credential döner |
| `MessageTypeCredential` | `prover_store_credential()` → cüzdana kaydeder |
| `MessageTypeCredentialOffer` | `prover_create_credential_request()` → şifreli request döner |
| `MessageTypePresentationRequest` | `prover_create_presentation()` → şifreli presentation döner |
| `MessageTypePresentation` | `verifier_verify_presentation()` → `{is_valid, revealed_data}` döner |
| `MessageTypeSimple` | İçeriği düz döner |

### Temel Prensipler

- **Holder her zaman ilk mesajı gönderir** — Issuer asla Holder'a bağlanmaz
- **Webhook tüm akışı otomatik yönetir** — Holder sadece `POST /didcomm/ITU` yapar, geri kalanı sunucu halleder
- **`prepare-offer` / `prepare-presentation-request`** — Issuer/Verifier'ın QR basmadan önce çalıştırdığı hazırlık adımları
- **QR/link köprü görevi görür** — Issuer'ın talebini NAT'ı aşarak Holder'a ulaştırır
