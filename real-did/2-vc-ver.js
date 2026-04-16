/* ═══════════════════════════════════════════════════════════════
   2-vc-ver.js — Verifiable Credential (VC) Oluşturma
   
   İTÜ (Issuer) Ahmet'e (Holder) gerçek dijital diploma verir.
   Diploma, İTÜ'nün GERÇEK private key'i ile imzalanır.
   
   Çalıştır: node 2-vc-ver.js
   ═══════════════════════════════════════════════════════════════ */

import {
    signData, fromBase58,
    printHeader, printSuccess, printInfo, printWarn, printKey, printJSON, colors
} from './crypto-utils.js';
import fs from 'fs';

// Önceki adımdan state'i oku
if (!fs.existsSync('state.json')) {
    console.log(colors.red + '\n  ❌ Önce "node 1-did-olustur.js" komutunu çalıştır!\n' + colors.reset);
    process.exit(1);
}

const state = JSON.parse(fs.readFileSync('state.json', 'utf-8'));

printHeader('ADIM 2: VERİFİABLE CREDENTİAL (VC) OLUŞTURMA');

console.log(colors.yellow + '\n  📖 Ne yapıyoruz?' + colors.reset);
console.log(colors.dim + '  İTÜ, Ahmet\'e dijital diploma (VC) veriyor.' + colors.reset);
console.log(colors.dim + '  Bu diploma İTÜ\'nün GERÇEK private key\'i ile imzalanacak!' + colors.reset);

// ═══════════════════════════════════════
// 1. Schema Tanımla
// ═══════════════════════════════════════
console.log(colors.bold + '\n\n  📋 Schema Tanımlama' + colors.reset);
console.log(colors.dim + '  ─────────────────────────────────────' + colors.reset);

const schema = {
    id: 'schema:itu:diploma:1.0',
    name: 'Diploma',
    version: '1.0',
    attrNames: ['ad', 'soyad', 'bolum', 'mezuniyet_yili', 'gpa', 'ogrenci_no']
};

printInfo('Schema tanımlandı:');
printJSON('', schema);
console.log(colors.dim + '\n  → Gerçek Indy\'de bu schema blockchain\'e yazılır.' + colors.reset);
console.log(colors.dim + '  → Schema, bir credential\'ın hangi alanları içereceğini belirler.' + colors.reset);

// ═══════════════════════════════════════
// 2. Credential Subject (Diploma Bilgileri)
// ═══════════════════════════════════════
console.log(colors.bold + '\n\n  📝 Diploma Bilgileri Hazırlanıyor' + colors.reset);
console.log(colors.dim + '  ─────────────────────────────────────' + colors.reset);

const credentialSubject = {
    id: state.holder.did,
    ad: 'Ahmet',
    soyad: 'Yılmaz',
    bolum: 'Bilgisayar Mühendisliği',
    mezuniyet_yili: 2024,
    gpa: 3.5,
    ogrenci_no: '020180101'
};

printInfo('Ahmet\'in diploma bilgileri:');
printJSON('', credentialSubject);

// ═══════════════════════════════════════
// 3. VC Oluştur (İmzasız)
// ═══════════════════════════════════════
console.log(colors.bold + '\n\n  🎫 Verifiable Credential Oluşturuluyor' + colors.reset);
console.log(colors.dim + '  ─────────────────────────────────────' + colors.reset);

const now = new Date().toISOString();

// VC'nin imzalanacak kısmı (proof hariç)
const vcPayload = {
    "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://www.w3.org/2018/credentials/examples/v1"
    ],
    type: ["VerifiableCredential", "UniversityDegreeCredential"],
    issuer: {
        id: state.issuer.did,
        name: state.issuer.name
    },
    issuanceDate: now,
    expirationDate: "2034-01-01T00:00:00Z",
    credentialSubject: credentialSubject
};

printInfo('VC içeriği (henüz imzalanmamış):');
printJSON('', vcPayload);

// ═══════════════════════════════════════
// 4. İTÜ'nün Private Key'i ile İMZALA
// ═══════════════════════════════════════
console.log(colors.bold + '\n\n  ✍️  İTÜ Private Key ile İmzalama' + colors.reset);
console.log(colors.dim + '  ─────────────────────────────────────' + colors.reset);

printWarn('İTÜ\'nün private key\'i kullanılıyor...');
printKey('  Private Key', state.issuer.privateKey.substring(0, 20) + '... (GİZLİ!)');

// GERÇEK İMZALAMA! Private key ile Ed25519 imza atılıyor
const issuerPrivateKey = fromBase58(state.issuer.privateKey);
const signature = signData(vcPayload, issuerPrivateKey);

printSuccess('İmza oluşturuldu!');
printKey('  İmza (Base58)', signature.substring(0, 40) + '...');
printInfo(`İmza uzunluğu: ${signature.length} karakter`);

// ═══════════════════════════════════════
// 5. Tam VC (İmzalı)
// ═══════════════════════════════════════
const vc = {
    ...vcPayload,
    proof: {
        type: "Ed25519Signature2020",
        created: now,
        verificationMethod: `${state.issuer.did}#keys-1`,
        proofPurpose: "assertionMethod",
        proofValue: signature
    }
};

console.log(colors.bold + '\n\n  📜 Tamamlanmış VC (İmzalı Diploma)' + colors.reset);
console.log(colors.dim + '  ─────────────────────────────────────' + colors.reset);
printJSON('', vc);

// State'e kaydet
state.vc = vc;
state.schema = schema;
fs.writeFileSync('state.json', JSON.stringify(state, null, 2));

// VC'yi ayrıca dosya olarak da kaydet (Ahmet'in cüzdanı)
fs.writeFileSync('ahmet-cuzdani-diploma.json', JSON.stringify(vc, null, 2));

console.log(colors.bgGreen + colors.white + colors.bold + '\n  ✅ ADIM 2 TAMAMLANDI! ' + colors.reset);
console.log(colors.green + '  Diploma VC\'si oluşturuldu ve Ahmet\'in cüzdanına kaydedildi.' + colors.reset);
console.log(colors.dim + '  → ahmet-cuzdani-diploma.json dosyasını incele!' + colors.reset);
console.log(colors.dim + '\n  Sonraki adım: node 3-vp-olustur.js\n' + colors.reset);

// AÇIKLAMA
console.log(colors.bgYellow + colors.white + '  📚 ÖĞRENME NOTU ' + colors.reset);
console.log(colors.yellow + `
  Şimdi ne oldu?
  ─────────────
  1. SCHEMA tanımladık: Diplomanın alanlarını belirledi
     (Gerçek Indy'de bu blockchain'e yazılır)
  
  2. VC PAYLOAD hazırladık: Ahmet'in diploma bilgileri
     - issuer: İTÜ'nün DID'i (kim verdi?)
     - subject: Ahmet'in DID'i + bilgileri (kime verildi?)
  
  3. GERÇEK İMZA attık! 🔥
     - İTÜ'nün Ed25519 private key'i ile imzaladık
     - Bu imza sadece İTÜ'nün private key'i ile atılabilir
     - Herkes İTÜ'nün public key'i ile doğrulayabilir
  
  4. VC = Payload + Proof (İmza)
     - proof alanı: imzanın kendisi + meta bilgiler
     - verificationMethod: hangi key ile doğrulanacak
     - proofPurpose: neden imzalandı (assertionMethod)
  
  ⚡ Önemli:
  - İmza GERÇEK kriptografik bir imza!
  - VC'yi biri değiştirirse imza bozulur ve doğrulama BAŞARISIZ olur
` + colors.reset);
