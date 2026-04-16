# 📂 Oluşturulan JSON Dosyaları — Detaylı Rehber

> [!NOTE]
> `node index.js` çalıştırıldığında 4 JSON dosyası oluşturulur. Her biri SSI sürecindeki farklı bir adımı temsil eder.

---

## 📋 Genel Bakış

| Dosya | Temsil Ettiği Şey | Kim Oluşturdu? | Kim Görür? |
|-------|-------------------|----------------|------------|
| `itu-did-document.json` | İTÜ'nün dijital kimlik kartı | İTÜ | Herkes (blockchain'de) |
| `ahmet-did-document.json` | Ahmet'in dijital kimlik kartı | Ahmet | Herkes (blockchain'de) |
| `ahmet-cuzdani-diploma.json` | Ahmet'in dijital diploması (VC) | İTÜ verdi, Ahmet saklıyor | Sadece Ahmet |
| `bankaya-gonderilen-vp.json` | Bankaya sunulan sınırlı bilgi (VP) | Ahmet | Ahmet + Banka |

---

## 1️⃣ `itu-did-document.json` — İTÜ'nün DID Document'i

> **Gerçek hayat karşılığı:** İTÜ'nün resmi mührü ve iletişim bilgilerini içeren noter onaylı kartvizit. "Ben İTÜ'yüm, beni bu şekilde doğrulayabilirsiniz" diyor.

```json
{
  "@context": [                          // ← 📌 STANDART TANIMI
    "https://www.w3.org/ns/did/v1",      //    W3C DID standardı
    "https://w3id.org/security/suites/ed25519-2020/v1"  // Ed25519 kripto standardı
  ],

  "id": "did:key:z6Mkv...mfde",         // ← 📌 İTÜ'NÜN DID'İ
                                         //    Blockchain'deki benzersiz kimliği
                                         //    "did:key:" = metod (blockchain'siz DID)
                                         //    "z6Mkv..." = public key'den türetilmiş ID

  "verificationMethod": [               // ← 📌 DOĞRULAMA YÖNTEMLERİ
    {
      "id": "...#keys-1",               //    Bu anahtarın referans adı
      "type": "Ed25519VerificationKey2020", // Anahtar türü (Ed25519)
      "controller": "did:key:z6Mkv...", //    Bu anahtarı kim kontrol ediyor? (İTÜ kendisi)
      "publicKeyBase58": "H93hxcc..."   //    🔓 İTÜ'NÜN PUBLIC KEY'İ
                                         //    Herkes bu key ile İTÜ'nün imzalarını doğrular
    }
  ],

  "authentication": [                   // ← 📌 KİMLİK DOĞRULAMA
    "...#keys-1"                         //    "keys-1 ile kimliğimi kanıtlarım"
  ],

  "assertionMethod": [                  // ← 📌 İDDİA/BEYAN YÖNTEMİ
    "...#keys-1"                         //    "keys-1 ile VC'leri imzalarım"
  ]
}
```

### Her Alanın Açıklaması

| Alan | Ne İşe Yarar? | Analoji |
|------|--------------|---------|
| `@context` | Bu JSON'un hangi standarda uygun olduğunu belirtir | Sözleşmenin hangi dilde yazıldığı |
| `id` | İTÜ'nün benzersiz DID adresi | TC Kimlik No (ama kendin oluşturuyorsun) |
| `verificationMethod` | İmza doğrulamada kullanılacak public key(ler) | Resmi mühür örneği |
| `publicKeyBase58` | **Public key'in kendisi** (Base58 formatında) | İmza doğrulama kalıbı |
| `authentication` | Kimlik doğrulama için hangi key kullanılır | "Bu mühürle beni tanıyın" |
| `assertionMethod` | VC imzalama için hangi key kullanılır | "Bu mühürle diploma veririm" |

> [!IMPORTANT]
> DID Document'te **private key YOKTUR!** Sadece public key var. Private key İTÜ'nün kasasında gizli kalır.

---

## 2️⃣ `ahmet-did-document.json` — Ahmet'in DID Document'i

> Yapı İTÜ'nünkiyle **tamamen aynı**, sadece Ahmet'e ait farklı anahtar çifti ile oluşturulmuş.

```json
{
  "id": "did:key:z6Mks...Fdqp",         // ← Ahmet'in DID'i (İTÜ'nünden farklı!)
  "verificationMethod": [{
    "publicKeyBase58": "ESwXZcN..."      // ← Ahmet'in public key'i (İTÜ'nünden farklı!)
  }]
}
```

### İTÜ vs Ahmet DID Document Farkı

| | İTÜ | Ahmet |
|--|-----|-------|
| DID | `did:key:z6Mkv...mfde` | `did:key:z6Mks...Fdqp` |
| Public Key | `H93hxcc...` | `ESwXZcN...` |
| Rol | Diploma **veren** | Diploma **alan** |
| `assertionMethod` kullanımı | VC imzalamak için | VP imzalamak için |

---

## 3️⃣ `ahmet-cuzdani-diploma.json` — Verifiable Credential (VC)

> **Gerçek hayat karşılığı:** Ahmet'in cüzdanında taşıdığı dijital diploma. İTÜ tarafından imzalanmış, değiştirilemez.

```json
{
  "@context": [                          // ← 📌 W3C VC standardı
    "https://www.w3.org/2018/credentials/v1"
  ],

  "type": [                              // ← 📌 BELGE TÜRÜ
    "VerifiableCredential",              //    Genel: doğrulanabilir belge
    "UniversityDegreeCredential"         //    Özel: üniversite diploması
  ],

  "issuer": {                            // ← 📌 KİM VERDİ?
    "id": "did:key:z6Mkv...mfde",        //    İTÜ'nün DID'i
    "name": "İstanbul Teknik Üniversitesi" //  İsmi (okunabilirlik için)
  },

  "issuanceDate": "2026-04-16T18:55:28.352Z",  // ← 📌 NE ZAMAN VERİLDİ?

  "credentialSubject": {                 // ← 📌 KİME VERİLDİ + BİLGİLER
    "id": "did:key:z6Mks...Fdqp",        //    Ahmet'in DID'i
    "ad": "Ahmet",                       //    👤 Kişisel bilgi
    "soyad": "Yılmaz",                   //    👤 Kişisel bilgi
    "bolum": "Bilgisayar Mühendisliği",  //    🎓 Diploma bilgisi
    "mezuniyet_yili": 2024,              //    📅 Diploma bilgisi
    "gpa": 3.5,                          //    📊 Akademik bilgi
    "ogrenci_no": "020180101"            //    🔢 Öğrenci numarası
  },

  "proof": {                            // ← 📌 İTÜ'NÜN DİJİTAL İMZASI
    "type": "Ed25519Signature2020",      //    İmza algoritması
    "created": "2026-04-16T18:55:28.355Z", // İmza zamanı
    "verificationMethod":                //    Hangi key ile doğrulanır?
      "did:key:z6Mkv...mfde#keys-1",    //    → İTÜ'nün DID Document'indeki keys-1
    "proofPurpose": "assertionMethod",   //    Neden imzalandı? → "Ben bunu iddia ediyorum"
    "proofValue": "4tAuVzchw61Z..."      //    🔥 GERÇEK ED25519 İMZA!
                                         //    İTÜ'nün private key'i ile üretildi
  }
}
```

### VC'nin 3 Ana Parçası

```
┌─────────────────────────────────────────────┐
│                    VC                        │
│                                              │
│  ┌──────────────┐  "Kim verdi?"              │
│  │   ISSUER     │  → İTÜ'nün DID'i          │
│  └──────────────┘                            │
│                                              │
│  ┌──────────────┐  "Kime + ne bilgisi?"      │
│  │   SUBJECT    │  → Ahmet'in DID'i          │
│  │   (claims)   │  → ad, bölüm, GPA...       │
│  └──────────────┘                            │
│                                              │
│  ┌──────────────┐  "Sahte değil kanıtı"      │
│  │   PROOF      │  → İTÜ'nün Ed25519 imzası  │
│  │   (imza)     │  → proofValue = gerçek imza │
│  └──────────────┘                            │
└─────────────────────────────────────────────┘
```

> [!WARNING]
> `proofValue` alanı GERÇEK kriptografik imzadır. VC'deki herhangi bir bilgi (ad, GPA, bölüm...) değiştirilirse bu imza **bozulur** ve sahtecilik tespit edilir!

---

## 4️⃣ `bankaya-gonderilen-vp.json` — Verifiable Presentation (VP)

> **Gerçek hayat karşılığı:** Ahmet'in bankaya gösterdiği "sınırlı" belge. Diploma bilgilerinin tamamını değil, sadece gerekli kısmını paylaşıyor.

```json
{
  "@context": [...],                     // ← W3C VP standardı

  "type": ["VerifiablePresentation"],    // ← 📌 Bu bir SUNUM

  "holder": "did:key:z6Mks...Fdqp",     // ← 📌 KİM SUNUYOR? → Ahmet

  "verifiableCredential": [              // ← 📌 İÇİNDEKİ VC (filtrelenmiş!)
    {
      "issuer": {                        //    Kim verdi? → İTÜ
        "id": "did:key:z6Mkv...mfde",
        "name": "İstanbul Teknik Üniversitesi"
      },
      "credentialSubject": {
        "id": "did:key:z6Mks...Fdqp",   //    Ahmet'in DID'i
        "bolum": "Bilgisayar Müh.",      //    ✅ PAYLAŞILDI
        "mezuniyet_yili": 2024           //    ✅ PAYLAŞILDI
                                         //    ❌ ad → YOK!
                                         //    ❌ soyad → YOK!
                                         //    ❌ gpa → YOK!
                                         //    ❌ ogrenci_no → YOK!
      },
      "proof": {                         // ← 📌 1. İMZA: İTÜ'nün İmzası
        "proofValue": "4tAuVzchw61Z..."  //    "Bu diplomayı BEN verdim" — İTÜ
      }
    }
  ],

  "proof": {                            // ← 📌 2. İMZA: Ahmet'in İmzası
    "type": "Ed25519Signature2020",
    "verificationMethod":
      "did:key:z6Mks...Fdqp#keys-1",    //    Ahmet'in key'i ile doğrulanır
    "proofPurpose": "authentication",    //    "Bu sunumu BEN yaptım" — Ahmet
    "challenge": "banka-1776365728358",  //    🔒 Tek kullanımlık değer (replay koruması)
    "proofValue": "4Xyme..."             //    🔥 Ahmet'in GERÇEK imzası
  }
}
```

### VP'deki İKİ İMZA

```
┌─────────────────────────────────────────────────────┐
│                       VP                             │
│                                                      │
│   holder: Ahmet     ← "Bu sunumu ben yapıyorum"     │
│                                                      │
│   ┌─────────────────────────────────────────┐        │
│   │  İçteki VC (filtrelenmiş)               │        │
│   │                                          │        │
│   │  credentialSubject:                      │        │
│   │    bolum: "Bilg. Müh."    ← paylaşıldı  │        │
│   │    mezuniyet_yili: 2024   ← paylaşıldı  │        │
│   │    ad: ???                ← GİZLİ 🔒    │        │
│   │    gpa: ???               ← GİZLİ 🔒    │        │
│   │                                          │        │
│   │  proof (İMZA #1): İTÜ'nün imzası 🏛️    │        │
│   │    "Bu diplomayı ben verdim"             │        │
│   └─────────────────────────────────────────┘        │
│                                                      │
│   proof (İMZA #2): Ahmet'in imzası 👤               │
│     "Bu sunumu ben yaptım"                           │
│     challenge: "banka-..."  ← tekrar kullanılamaz    │
│                                                      │
└─────────────────────────────────────────────────────┘
```

> [!TIP]
> **`challenge` alanı neden var?** Banka, Ahmet'e benzersiz bir challenge değeri gönderir. Ahmet bunu VP'ye dahil ederek imzalar. Bu sayede birisi bu VP'yi çalıp başka bir bankada kullansa bile, challenge farklı olacağından geçersiz olur. Buna **replay attack koruması** denir.

---

## 🔄 VC vs VP Karşılaştırması

### Bilgi Karşılaştırması

| Alan | VC'de (Cüzdan) | VP'de (Bankaya giden) | Durum |
|------|----------------|----------------------|-------|
| `ad` | "Ahmet" | — | 🔒 Gizli |
| `soyad` | "Yılmaz" | — | 🔒 Gizli |
| `bolum` | "Bilgisayar Müh." | "Bilgisayar Müh." | ✅ Paylaşıldı |
| `mezuniyet_yili` | 2024 | 2024 | ✅ Paylaşıldı |
| `gpa` | 3.5 | — | 🔒 Gizli |
| `ogrenci_no` | "020180101" | — | 🔒 Gizli |

### İmza Karşılaştırması

| | VC | VP |
|--|----|----|
| İmza sayısı | 1 (İTÜ) | 2 (İTÜ + Ahmet) |
| İTÜ ne diyor? | "Bu diplomayı verdim" | "Bu diplomayı verdim" |
| Ahmet ne diyor? | — | "Bu sunumu ben yaptım" |
| `challenge` | Yok | Var (replay koruması) |
| `proofPurpose` | `assertionMethod` | `authentication` |

---

## 🧠 Doğrulama Süreci (Banka Ne Yapıyor?)

```
Banka VP'yi aldığında şu adımları izler:

1. VP yapısını kontrol et
   └─ type: "VerifiablePresentation" var mı? ✅

2. İTÜ'nün DID'ini blockchain'den çek
   └─ did:key:z6Mkv... → publicKeyBase58: "H93hxcc..." ✅

3. İTÜ'nün VC imzasını doğrula
   └─ proofValue + orijinal veri + İTÜ public key → GEÇERLİ ✅

4. Ahmet'in DID'ini blockchain'den çek
   └─ did:key:z6Mks... → publicKeyBase58: "ESwXZcN..." ✅

5. Ahmet'in VP imzasını doğrula
   └─ proofValue + VP verisi + Ahmet public key → GEÇERLİ ✅

6. Challenge kontrolü
   └─ "banka-1776365728358" benim gönderdiğim mi? → EVET ✅

7. Sonuç: DOĞRULAMA BAŞARILI 🎉
```
