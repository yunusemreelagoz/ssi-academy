/* ═══════════════════════════════════════════════════════════════
   3-vp-olustur.js — Verifiable Presentation (VP) Oluşturma
   
   Ahmet (Holder), bankaya başvururken diplomasından
   SADECE gerekli bilgileri paylaşır (Selective Disclosure).
   
   Çalıştır: node 3-vp-olustur.js
   ═══════════════════════════════════════════════════════════════ */

import {
    signData, fromBase58,
    printHeader, printSuccess, printInfo, printWarn, printError, printKey, printJSON, colors
} from './crypto-utils.js';
import fs from 'fs';

if (!fs.existsSync('state.json')) {
    console.log(colors.red + '\n  ❌ Önce önceki adımları çalıştır!\n' + colors.reset);
    process.exit(1);
}

const state = JSON.parse(fs.readFileSync('state.json', 'utf-8'));

if (!state.vc) {
    console.log(colors.red + '\n  ❌ Önce "node 2-vc-ver.js" komutunu çalıştır!\n' + colors.reset);
    process.exit(1);
}

printHeader('ADIM 3: VERİFİABLE PRESENTATİON (VP) OLUŞTURMA');

console.log(colors.yellow + '\n  📖 Senaryo:' + colors.reset);
console.log(colors.dim + '  Ahmet, Garanti Bankası\'na iş başvurusu yapıyor.' + colors.reset);
console.log(colors.dim + '  Banka: "Üniversite diplomanızı gösterin"' + colors.reset);
console.log(colors.dim + '  Ahmet: Tüm bilgilerini değil, SADECE gerekli olanları paylaşacak!' + colors.reset);

// ═══════════════════════════════════════
// 1. Ahmet'in cüzdanındaki VC
// ═══════════════════════════════════════
console.log(colors.bold + '\n\n  📱 Ahmet\'in Cüzdanındaki VC' + colors.reset);
console.log(colors.dim + '  ─────────────────────────────────────' + colors.reset);

const vc = state.vc;
printInfo('VC\'deki TÜM bilgiler:');
const allClaims = vc.credentialSubject;
Object.entries(allClaims).forEach(([key, value]) => {
    if (key === 'id') {
        printKey(`  ${key}`, String(value).substring(0, 40) + '...');
    } else {
        printKey(`  ${key}`, String(value));
    }
});

// ═══════════════════════════════════════
// 2. Selective Disclosure (Seçici Paylaşım)
// ═══════════════════════════════════════
console.log(colors.bold + '\n\n  🔍 Selective Disclosure (Seçici Paylaşım)' + colors.reset);
console.log(colors.dim + '  ─────────────────────────────────────' + colors.reset);

printInfo('Banka şunları istiyor: bölüm, mezuniyet yılı');
console.log();
printSuccess('PAYLAŞILACAK bilgiler:');
printKey('  ✅ bolum          ', allClaims.bolum);
printKey('  ✅ mezuniyet_yili ', String(allClaims.mezuniyet_yili));

console.log();
printError('GİZLİ KALACAK bilgiler:');
printKey('  🔒 ad             ', '████████ (gizli)');
printKey('  🔒 soyad          ', '████████ (gizli)');
printKey('  🔒 gpa            ', '████████ (gizli)');
printKey('  🔒 ogrenci_no     ', '████████ (gizli)');

console.log(colors.yellow + `
  💡 Bu çok önemli bir özellik!
  Ahmet, GPA'sını veya öğrenci numarasını bankaya göstermek
  zorunda DEĞİL. Sadece bölümünü ve mezuniyet yılını paylaşıyor.
  
  Gerçek Indy'de bu "Zero-Knowledge Proof" ile yapılır.
  Biz burada basitleştirilmiş selective disclosure gösteriyoruz.
` + colors.reset);

// ═══════════════════════════════════════
// 3. VP Oluştur
// ═══════════════════════════════════════
console.log(colors.bold + '\n  📨 VP (Verifiable Presentation) Oluşturuluyor' + colors.reset);
console.log(colors.dim + '  ─────────────────────────────────────' + colors.reset);

// VP'nin payload'ı
const vpPayload = {
    "@context": [
        "https://www.w3.org/2018/credentials/v1"
    ],
    type: ["VerifiablePresentation"],
    holder: state.holder.did,
    verifiableCredential: [
        {
            // Orijinal VC'den sadece gerekli alanları al
            "@context": vc["@context"],
            type: vc.type,
            issuer: vc.issuer,
            issuanceDate: vc.issuanceDate,
            credentialSubject: {
                id: allClaims.id,
                // SADECE paylaşılan alanlar:
                bolum: allClaims.bolum,
                mezuniyet_yili: allClaims.mezuniyet_yili
                // ad, soyad, gpa, ogrenci_no → YOK! Gizli!
            },
            // Orijinal VC'nin proof'u (İTÜ'nün imzası) dahil
            proof: vc.proof
        }
    ]
};

printInfo('VP payload (imzalanmadan önce):');
printJSON('', vpPayload);

// ═══════════════════════════════════════
// 4. Ahmet'in Private Key'i ile İmzala
// ═══════════════════════════════════════
console.log(colors.bold + '\n\n  ✍️  Ahmet\'in Private Key\'i ile VP İmzalama' + colors.reset);
console.log(colors.dim + '  ─────────────────────────────────────' + colors.reset);

printWarn('Ahmet\'in private key\'i kullanılıyor...');

const holderPrivateKey = fromBase58(state.holder.privateKey);
const vpSignature = signData(vpPayload, holderPrivateKey);

printSuccess('VP imzası oluşturuldu!');
printKey('  VP İmzası (Base58)', vpSignature.substring(0, 40) + '...');

// Tam VP
const vp = {
    ...vpPayload,
    proof: {
        type: "Ed25519Signature2020",
        created: new Date().toISOString(),
        verificationMethod: `${state.holder.did}#keys-1`,
        proofPurpose: "authentication",
        challenge: "banka-dogrulama-" + Date.now(),
        proofValue: vpSignature
    }
};

console.log(colors.bold + '\n\n  📜 Tamamlanmış VP (İmzalı Sunum)' + colors.reset);
console.log(colors.dim + '  ─────────────────────────────────────' + colors.reset);
printJSON('', vp);

// State'e kaydet
state.vp = vp;
fs.writeFileSync('state.json', JSON.stringify(state, null, 2));
fs.writeFileSync('bankaya-gonderilen-vp.json', JSON.stringify(vp, null, 2));

console.log(colors.bgGreen + colors.white + colors.bold + '\n  ✅ ADIM 3 TAMAMLANDI! ' + colors.reset);
console.log(colors.green + '  VP oluşturuldu ve bankaya gönderilmeye hazır.' + colors.reset);
console.log(colors.dim + '  → bankaya-gonderilen-vp.json dosyasını incele!' + colors.reset);
console.log(colors.dim + '\n  Sonraki adım: node 4-dogrula.js\n' + colors.reset);

// AÇIKLAMA
console.log(colors.bgYellow + colors.white + '  📚 ÖĞRENME NOTU ' + colors.reset);
console.log(colors.yellow + `
  Şimdi ne oldu?
  ─────────────
  1. Ahmet cüzdanındaki VC'den SADECE gerekli alanları seçti
     → bolum ve mezuniyet_yili paylaşıldı
     → ad, soyad, gpa, ogrenci_no GİZLİ kaldı
  
  2. VP oluşturuldu:
     - holder: Ahmet'in DID'i (bunu kim sunuyor?)
     - verifiableCredential: İçindeki VC (İTÜ'nün orijinal imzası dahil!)
     - proof: Ahmet'in kendi imzası (VP'nin gerçekten Ahmet'ten geldiğinin kanıtı)
  
  3. VP'de İKİ İMZA var:
     a) İTÜ'nün imzası: "Bu diplomayı BEN verdim" diyor
     b) Ahmet'in imzası: "Bu sunumu BEN yaptım" diyor
  
  4. challenge alanı:
     - Bankadan gelen bir meydan okuma değeri
     - Replay attack'ı önler (aynı VP'yi başkası kullanamaz)
  
  ⚡ Zero-Knowledge Proof vs Selective Disclosure:
  - Burada "selective disclosure" yaptık (sadece bazı alanları gösterdik)
  - Gerçek Indy'de "ZKP" ile daha güçlü: "18 yaşından büyüğüm"
    diyebilirsin ama doğum tarihini vermezsin!
` + colors.reset);
