/* ═══════════════════════════════════════════════════════════════
   index.js — Tüm Adımları Tek Seferde Çalıştır
   
   Bu dosya 4 adımı da sırayla çalıştırır:
   1. DID Oluşturma
   2. VC Verme
   3. VP Oluşturma
   4. Doğrulama + Sahtecilik Testi
   
   Çalıştır: node index.js
   ═══════════════════════════════════════════════════════════════ */

import {
    generateKeyPair, createDIDKey, createDIDDocument,
    signData, verifySignature,
    toHex, toBase58, fromBase58,
    printHeader, printSuccess, printInfo, printWarn, printError, printKey, printJSON, colors
} from './crypto-utils.js';
import fs from 'fs';

console.log(colors.bgBlue + colors.white + colors.bold);
console.log('  ╔═══════════════════════════════════════════════════════╗');
console.log('  ║                                                       ║');
console.log('  ║   🔐 SSI & DID — Gerçek Kriptografi Demo             ║');
console.log('  ║   Hyperledger Indy Kavramları ile                     ║');
console.log('  ║                                                       ║');
console.log('  ╚═══════════════════════════════════════════════════════╝');
console.log(colors.reset);

console.log(colors.dim + '  Bu demo GERÇEK Ed25519 kriptografi kullanır.' + colors.reset);
console.log(colors.dim + '  Sahte/rastgele değil, gerçek anahtar çifti + gerçek imza!' + colors.reset);

// ╔═══════════════════════════════════════════════╗
// ║  ADIM 1: DID OLUŞTURMA                       ║
// ╚═══════════════════════════════════════════════╝

printHeader('ADIM 1/4: DID OLUŞTURMA');

// İTÜ (Issuer)
const issuerKeys = generateKeyPair();
const issuerDID = createDIDKey(issuerKeys.publicKey);
const issuerDIDDoc = createDIDDocument(issuerDID, issuerKeys.publicKey);

printSuccess('İTÜ (Issuer) DID oluşturuldu');
printKey('  DID       ', issuerDID);
printKey('  Public Key', toBase58(issuerKeys.publicKey).substring(0, 30) + '...');
printKey('  Priv Key  ', toBase58(issuerKeys.privateKey).substring(0, 15) + '... (GİZLİ!)');

// Ahmet (Holder)
const holderKeys = generateKeyPair();
const holderDID = createDIDKey(holderKeys.publicKey);
const holderDIDDoc = createDIDDocument(holderDID, holderKeys.publicKey);

console.log();
printSuccess('Ahmet (Holder) DID oluşturuldu');
printKey('  DID       ', holderDID);
printKey('  Public Key', toBase58(holderKeys.publicKey).substring(0, 30) + '...');

// Banka (Verifier)
const verifierKeys = generateKeyPair();
const verifierDID = createDIDKey(verifierKeys.publicKey);

console.log();
printSuccess('Garanti Bankası (Verifier) DID oluşturuldu');
printKey('  DID       ', verifierDID);

console.log(colors.dim + '\n  → 3 gerçek Ed25519 anahtar çifti üretildi' + colors.reset);
console.log(colors.dim + '  → Her DID, public key\'den deterministik olarak türetildi' + colors.reset);

// ╔═══════════════════════════════════════════════╗
// ║  ADIM 2: VC (DİPLOMA) VERME                  ║
// ╚═══════════════════════════════════════════════╝

printHeader('ADIM 2/4: VC (DİPLOMA) VERME');

const schema = {
    name: 'Diploma', version: '1.0',
    attrNames: ['ad', 'soyad', 'bolum', 'mezuniyet_yili', 'gpa', 'ogrenci_no']
};
printInfo('Schema: ' + JSON.stringify(schema.attrNames));

const vcPayload = {
    "@context": ["https://www.w3.org/2018/credentials/v1"],
    type: ["VerifiableCredential", "UniversityDegreeCredential"],
    issuer: { id: issuerDID, name: 'İstanbul Teknik Üniversitesi' },
    issuanceDate: new Date().toISOString(),
    credentialSubject: {
        id: holderDID,
        ad: 'Ahmet', soyad: 'Yılmaz',
        bolum: 'Bilgisayar Mühendisliği',
        mezuniyet_yili: 2024, gpa: 3.5,
        ogrenci_no: '020180101'
    }
};

// GERÇEK İMZALAMA
const vcSignature = signData(vcPayload, issuerKeys.privateKey);

const vc = {
    ...vcPayload,
    proof: {
        type: "Ed25519Signature2020",
        created: new Date().toISOString(),
        verificationMethod: `${issuerDID}#keys-1`,
        proofPurpose: "assertionMethod",
        proofValue: vcSignature
    }
};

printSuccess('VC oluşturuldu ve İTÜ\'nün private key\'i ile İMZALANDI');
printKey('  İmza', vcSignature.substring(0, 50) + '...');
printInfo('VC\'deki bilgiler:');
Object.entries(vc.credentialSubject).forEach(([k, v]) => {
    if (k !== 'id') printKey(`  ${k}`, String(v));
});

// VC'yi dosyaya kaydet
fs.writeFileSync('ahmet-cuzdani-diploma.json', JSON.stringify(vc, null, 2));
console.log(colors.dim + '\n  → Diploma, ahmet-cuzdani-diploma.json dosyasına kaydedildi' + colors.reset);

// ╔═══════════════════════════════════════════════╗
// ║  ADIM 3: VP (SEÇİCİ SUNUM) OLUŞTURMA         ║
// ╚═══════════════════════════════════════════════╝

printHeader('ADIM 3/4: VP (SEÇİCİ SUNUM) OLUŞTURMA');

printWarn('Banka istiyor: bölüm, mezuniyet yılı');
printSuccess('Paylaşılan:  ✅ bolum, ✅ mezuniyet_yili');
printError('Gizli kalan: 🔒 ad, 🔒 soyad, 🔒 gpa, 🔒 ogrenci_no');

const vpPayload = {
    "@context": ["https://www.w3.org/2018/credentials/v1"],
    type: ["VerifiablePresentation"],
    holder: holderDID,
    verifiableCredential: [{
        "@context": vc["@context"],
        type: vc.type,
        issuer: vc.issuer,
        issuanceDate: vc.issuanceDate,
        credentialSubject: {
            id: holderDID,
            bolum: 'Bilgisayar Mühendisliği',
            mezuniyet_yili: 2024
        },
        proof: vc.proof
    }]
};

// Ahmet'in imzası
const vpSignature = signData(vpPayload, holderKeys.privateKey);

const vp = {
    ...vpPayload,
    proof: {
        type: "Ed25519Signature2020",
        created: new Date().toISOString(),
        verificationMethod: `${holderDID}#keys-1`,
        proofPurpose: "authentication",
        challenge: "banka-" + Date.now(),
        proofValue: vpSignature
    }
};

printSuccess('VP oluşturuldu ve Ahmet\'in private key\'i ile imzalandı');
fs.writeFileSync('bankaya-gonderilen-vp.json', JSON.stringify(vp, null, 2));
console.log(colors.dim + '  → VP, bankaya-gonderilen-vp.json dosyasına kaydedildi' + colors.reset);

// ╔═══════════════════════════════════════════════╗
// ║  ADIM 4: DOĞRULAMA                            ║
// ╚═══════════════════════════════════════════════╝

printHeader('ADIM 4/4: DOĞRULAMA');

console.log(colors.bold + '\n  🏢 Garanti Bankası doğrulama yapıyor...\n' + colors.reset);

// 4a. İTÜ'nün VC imzasını doğrula
printInfo('1) İTÜ\'nün VC imzası kontrol ediliyor...');
const vcIsValid = verifySignature(vcPayload, vcSignature, issuerKeys.publicKey);
console.log(vcIsValid
    ? colors.green + '     ✅ İTÜ\'nün imzası GEÇERLİ — diploma gerçek!' + colors.reset
    : colors.red + '     ❌ İTÜ\'nün imzası GEÇERSİZ!' + colors.reset
);

// 4b. Ahmet'in VP imzasını doğrula
printInfo('2) Ahmet\'in VP imzası kontrol ediliyor...');
const vpIsValid = verifySignature(vpPayload, vpSignature, holderKeys.publicKey);
console.log(vpIsValid
    ? colors.green + '     ✅ Ahmet\'in imzası GEÇERLİ — sunumu Ahmet yapmış!' + colors.reset
    : colors.red + '     ❌ Ahmet\'in imzası GEÇERSİZ!' + colors.reset
);

// Sonuç
if (vcIsValid && vpIsValid) {
    console.log(colors.bgGreen + colors.white + colors.bold + `
  ╔═══════════════════════════════════════════════╗
  ║                                               ║
  ║   🎉 TÜM DOĞRULAMALAR BAŞARILI!              ║
  ║                                               ║
  ║   ✅ Diploma gerçek (İTÜ imzası geçerli)     ║
  ║   ✅ Sunum Ahmet'ten (Ahmet imzası geçerli)  ║
  ║   📋 Bölüm: Bilgisayar Mühendisliği         ║
  ║   📅 Mezuniyet: 2024                          ║
  ║   🔒 Ad, Soyad, GPA, No → GİZLİ KALDI       ║
  ║                                               ║
  ╚═══════════════════════════════════════════════╝
` + colors.reset);
}

// ╔═══════════════════════════════════════════════╗
// ║  BONUS: SAHTECİLİK TESTİ                      ║
// ╚═══════════════════════════════════════════════╝

printHeader('BONUS: SAHTECİLİK TESTİ 🔥');

console.log(colors.yellow + '  Birisi VC\'deki GPA\'yı değiştirirse ne olur?\n' + colors.reset);

const fakePayload = JSON.parse(JSON.stringify(vcPayload));
fakePayload.credentialSubject.gpa = 4.0;

printWarn('GPA değiştirildi: 3.5 → 4.0');
printInfo('Orijinal imza ile doğrulama deneniyor...');

const fakeIsValid = verifySignature(fakePayload, vcSignature, issuerKeys.publicKey);

if (!fakeIsValid) {
    console.log(colors.bgRed + colors.white + colors.bold + '\n  ❌ SAHTECİLİK TESPİT EDİLDİ! ' + colors.reset);
    console.log(colors.green + '  Veri değiştirildiğinde imza BOZULDU!' + colors.reset);
    console.log(colors.green + '  → Tek bir karakter bile değişse imza geçersiz olur.' + colors.reset);
    console.log(colors.green + '  → Kriptografik güvenlik sağlandı! 🛡️\n' + colors.reset);
}

// DID Document'ı da kaydet
fs.writeFileSync('itu-did-document.json', JSON.stringify(issuerDIDDoc, null, 2));
fs.writeFileSync('ahmet-did-document.json', JSON.stringify(holderDIDDoc, null, 2));

console.log(colors.dim + '  Oluşturulan dosyalar:' + colors.reset);
console.log(colors.dim + '  ├── itu-did-document.json       (İTÜ\'nün DID Document\'i)' + colors.reset);
console.log(colors.dim + '  ├── ahmet-did-document.json     (Ahmet\'in DID Document\'i)' + colors.reset);
console.log(colors.dim + '  ├── ahmet-cuzdani-diploma.json  (Ahmet\'in diploma VC\'si)' + colors.reset);
console.log(colors.dim + '  └── bankaya-gonderilen-vp.json  (Bankaya gönderilen VP)' + colors.reset);
console.log(colors.dim + '\n  Bu dosyaları açarak JSON yapılarını inceleyebilirsin! 📂\n' + colors.reset);
