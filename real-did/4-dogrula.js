/* ═══════════════════════════════════════════════════════════════
   4-dogrula.js — VP Doğrulama (Verification)
   
   Ziraat Bankası (Verifier) Ahmet'in sunduğu VP'yi doğrular.
   İmzalar GERÇEK kriptografik olarak kontrol edilir!
   
   Ayrıca: Sahtecilik testi — veriler değiştirilirse ne olur?
   
   Çalıştır: node 4-dogrula.js
   ═══════════════════════════════════════════════════════════════ */

import {
    verifySignature, fromBase58, signData,
    printHeader, printSuccess, printInfo, printWarn, printError, printKey, printJSON, colors
} from './crypto-utils.js';
import fs from 'fs';

if (!fs.existsSync('state.json')) {
    console.log(colors.red + '\n  ❌ Önce önceki adımları çalıştır!\n' + colors.reset);
    process.exit(1);
}

const state = JSON.parse(fs.readFileSync('state.json', 'utf-8'));

if (!state.vp) {
    console.log(colors.red + '\n  ❌ Önce "node 3-vp-olustur.js" komutunu çalıştır!\n' + colors.reset);
    process.exit(1);
}

printHeader('ADIM 4: VP DOĞRULAMA (VERİFİCATİON)');

console.log(colors.yellow + '\n  📖 Senaryo:' + colors.reset);
console.log(colors.dim + '  Ziraat Bankası, Ahmet\'in gönderdiği VP\'yi doğruluyor.' + colors.reset);
console.log(colors.dim + '  Tüm imzalar GERÇEK kriptografik olarak kontrol edilecek!' + colors.reset);

const vp = state.vp;
const vc = vp.verifiableCredential[0];

// ═══════════════════════════════════════
// 1. VP Yapı Kontrolü
// ═══════════════════════════════════════
console.log(colors.bold + '\n\n  🔍 1. VP Yapı Kontrolü' + colors.reset);
console.log(colors.dim + '  ─────────────────────────────────────' + colors.reset);

const hasContext = vp["@context"] && vp["@context"].length > 0;
const hasType = vp.type && vp.type.includes("VerifiablePresentation");
const hasHolder = !!vp.holder;
const hasVPProof = !!vp.proof;
const hasVC = vp.verifiableCredential && vp.verifiableCredential.length > 0;

printInfo('Yapı kontrolleri:');
console.log(`  ${hasContext ? '✅' : '❌'} @context mevcut`);
console.log(`  ${hasType ? '✅' : '❌'} type: VerifiablePresentation`);
console.log(`  ${hasHolder ? '✅' : '❌'} holder DID: ${vp.holder ? vp.holder.substring(0, 40) + '...' : 'YOK'}`);
console.log(`  ${hasVPProof ? '✅' : '❌'} VP proof (Ahmet'in imzası) mevcut`);
console.log(`  ${hasVC ? '✅' : '❌'} ${vp.verifiableCredential?.length || 0} adet VC içeriyor`);

if (!hasContext || !hasType || !hasHolder || !hasVPProof || !hasVC) {
    printError('VP yapısı geçersiz! Doğrulama başarısız.');
    process.exit(1);
}
printSuccess('VP yapısı geçerli!');

// ═══════════════════════════════════════
// 2. VC İçerik Kontrolü
// ═══════════════════════════════════════
console.log(colors.bold + '\n\n  🔍 2. VC İçerik Kontrolü' + colors.reset);
console.log(colors.dim + '  ─────────────────────────────────────' + colors.reset);

const issuerDID = vc.issuer.id || vc.issuer;
printKey('  Issuer DID', issuerDID.substring(0, 45) + '...');
printKey('  Subject DID', vc.credentialSubject.id.substring(0, 45) + '...');
printKey('  Verilen tarih', vc.issuanceDate);

printInfo('Paylaşılan bilgiler:');
Object.entries(vc.credentialSubject).forEach(([key, value]) => {
    if (key !== 'id') {
        printKey(`  ${key}`, String(value));
    }
});

// ═══════════════════════════════════════
// 3. İTÜ'nün İmzasını Doğrula (VC Proof)
// ═══════════════════════════════════════
console.log(colors.bold + '\n\n  🔐 3. İTÜ\'nün İmzasını Doğrulama (VC Proof)' + colors.reset);
console.log(colors.dim + '  ─────────────────────────────────────' + colors.reset);

printInfo('İTÜ\'nün public key\'i alınıyor (gerçekte blockchain\'den)...');
const issuerPublicKey = fromBase58(state.issuer.publicKey);
printKey('  İTÜ Public Key', state.issuer.publicKey.substring(0, 30) + '...');

// VC'nin orijinal payload'ını yeniden oluştur (proof hariç)
const originalVCPayload = { ...state.vc };
delete originalVCPayload.proof;

printInfo('Orijinal VC payload\'ı ile imza karşılaştırılıyor...');
const vcSignature = vc.proof.proofValue;
printKey('  VC İmzası', vcSignature.substring(0, 40) + '...');

const vcValid = verifySignature(originalVCPayload, vcSignature, issuerPublicKey);

if (vcValid) {
    printSuccess('İTÜ\'nün imzası GEÇERLİ! ✅');
    console.log(colors.green + '  → Bu diploma gerçekten İTÜ tarafından verilmiş!' + colors.reset);
} else {
    printError('İTÜ\'nün imzası GEÇERSİZ! ❌');
    console.log(colors.red + '  → Bu diploma SAHTE olabilir!' + colors.reset);
}

// ═══════════════════════════════════════
// 4. Ahmet'in İmzasını Doğrula (VP Proof)
// ═══════════════════════════════════════
console.log(colors.bold + '\n\n  🔐 4. Ahmet\'in İmzasını Doğrulama (VP Proof)' + colors.reset);
console.log(colors.dim + '  ─────────────────────────────────────' + colors.reset);

printInfo('Ahmet\'in public key\'i alınıyor...');
const holderPublicKey = fromBase58(state.holder.publicKey);
printKey('  Ahmet Public Key', state.holder.publicKey.substring(0, 30) + '...');

// VP'nin orijinal payload'ını yeniden oluştur
const originalVPPayload = { ...vp };
delete originalVPPayload.proof;

const vpSignature = vp.proof.proofValue;
printKey('  VP İmzası', vpSignature.substring(0, 40) + '...');

const vpValid = verifySignature(originalVPPayload, vpSignature, holderPublicKey);

if (vpValid) {
    printSuccess('Ahmet\'in imzası GEÇERLİ! ✅');
    console.log(colors.green + '  → Bu sunumu gerçekten Ahmet yapmış!' + colors.reset);
} else {
    printError('Ahmet\'in imzası GEÇERSİZ! ❌');
    console.log(colors.red + '  → Bu sunumu Ahmet yapmamış olabilir!' + colors.reset);
}

// ═══════════════════════════════════════
// 5. Sonuç
// ═══════════════════════════════════════
console.log('\n');
if (vcValid && vpValid) {
    console.log(colors.bgGreen + colors.white + colors.bold + ' ═══════════════════════════════════════════ ' + colors.reset);
    console.log(colors.bgGreen + colors.white + colors.bold + '    🎉 DOĞRULAMA BAŞARILI!                  ' + colors.reset);
    console.log(colors.bgGreen + colors.white + colors.bold + ' ═══════════════════════════════════════════ ' + colors.reset);
    console.log(colors.green + `
  ✅ İTÜ'nün imzası geçerli — diploma gerçek
  ✅ Ahmet'in imzası geçerli — sunumu Ahmet yapmış
  ✅ Diploma bilgileri:
     → Bölüm: ${vc.credentialSubject.bolum}
     → Mezuniyet: ${vc.credentialSubject.mezuniyet_yili}
  🔒 Gizli kalan bilgiler: ad, soyad, gpa, ogrenci_no
  
  Ziraat Bankası, Ahmet'in başvurusunu onaylayabilir!
` + colors.reset);
} else {
    console.log(colors.bgRed + colors.white + colors.bold + ' ═══════════════════════════════════════════ ' + colors.reset);
    console.log(colors.bgRed + colors.white + colors.bold + '    ❌ DOĞRULAMA BAŞARISIZ!                  ' + colors.reset);
    console.log(colors.bgRed + colors.white + colors.bold + ' ═══════════════════════════════════════════ ' + colors.reset);
}

// ═══════════════════════════════════════
// 6. SAHTECİLİK TESTİ 🔥
// ═══════════════════════════════════════
console.log(colors.bold + '\n\n  🔥 BONUS: SAHTECİLİK TESTİ' + colors.reset);
console.log(colors.dim + '  ─────────────────────────────────────' + colors.reset);
console.log(colors.yellow + '  Birisi VC\'deki GPA\'yı 3.5\'ten 4.0\'a değiştirmeye çalışırsa ne olur?' + colors.reset);

// VC'yi kopyala ve değiştir
const tamperedPayload = JSON.parse(JSON.stringify(originalVCPayload));
tamperedPayload.credentialSubject.gpa = 4.0;  // SAHTECİLİK! GPA değiştirildi

printWarn('Sahte VC: gpa 3.5 → 4.0 olarak değiştirildi');
printInfo('Aynı imza ile doğrulama deneniyor...');

const tamperedValid = verifySignature(tamperedPayload, vcSignature, issuerPublicKey);

if (!tamperedValid) {
    printError('İMZA DOĞRULAMASI BAŞARISIZ! (Beklendiği gibi!)');
    console.log(colors.green + '  → Veriler değiştirildiğinde imza bozuldu!' + colors.reset);
    console.log(colors.green + '  → SAHTECİLİK TESPİT EDİLDİ! Sistem güvenli. 🛡️' + colors.reset);
} else {
    printSuccess('İmza doğrulandı (bu olmamalıydı!)');
}

// AÇIKLAMA
console.log(colors.bgYellow + colors.white + '\n  📚 ÖĞRENME NOTU ' + colors.reset);
console.log(colors.yellow + `
  Neler doğrulandı?
  ─────────────────
  1. VC İMZASI (İTÜ'nün imzası):
     - İTÜ'nün public key'i ile imza kontrol edildi
     - "Bu diplomayı gerçekten İTÜ mü verdi?" → EVET ✅
  
  2. VP İMZASI (Ahmet'in imzası):
     - Ahmet'in public key'i ile imza kontrol edildi
     - "Bu sunumu gerçekten Ahmet mı yaptı?" → EVET ✅
  
  3. SAHTECİLİK TESTİ:
     - VC'deki bir bilgi değiştirildi (GPA: 3.5 → 4.0)
     - İmza doğrulaması BAŞARISIZ oldu!
     - Çünkü: İmza, verinin matematiksel özeti üzerinden atılır
     - Tek bir BIT bile değişse imza bozulur!
  
  ⚡ Gerçek Indy'de ek kontroller:
  - Revocation kontrolü (diploma iptal edilmiş mi?)
  - Schema kontrolü (doğru formatta mı?)
  - Credential Definition kontrolü
  - Zaman damgası kontrolü (süresi dolmuş mu?)
` + colors.reset);
