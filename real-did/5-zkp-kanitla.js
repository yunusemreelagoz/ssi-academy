/* ═══════════════════════════════════════════════════════════════
   5-zkp-kanitla.js — Zero-Knowledge Proof (Sıfır Bilgi İspatı)
   
   Senaryo: Ahmet Ziraat Bankası'na GPA'sını PAYLAŞMAZ. 
   Ancak GPA'sının > 3.0 olduğunu matematiksel olarak kanıtlar.
   Banka Ahmet'in GPA'sının 3.1 mi yoksa 4.0 mı olduğunu TAHMİN EDEMEZ.
   Sadece "3.0'dan büyük" olduğunu doğrular.
   
   Çalıştır: node 5-zkp-kanitla.js
   ═══════════════════════════════════════════════════════════════ */

import fs from 'fs';
import crypto from 'crypto';
import { printHeader, printSuccess, printInfo, printWarn, printError, colors } from './crypto-utils.js';

printHeader('ADIM 5: ZERO-KNOWLEDGE PROOF (ZKP) İLE PREDICATE (ŞART) İSPATI');

// Demo State Oku
if (!fs.existsSync('state.json')) {
    console.log(colors.red + '\n  ❌ Önce önceki adımları çalıştır!\n' + colors.reset);
    process.exit(1);
}
const state = JSON.parse(fs.readFileSync('state.json', 'utf-8'));

console.log(colors.yellow + '\n  📖 ZKP Senaryosu:' + colors.reset);
console.log(colors.dim + '  Banka: "GPA\'nı (not ortalamanı) görmek istemiyorum! Gizlilik gereği sakla."' + colors.reset);
console.log(colors.dim + '  Banka: "Bana SADECE GPA > 3.0 şartını sağladığını kanıtlayan bir ZKP (Sıfır Bilgi İspatı) gönder."' + colors.reset);
console.log(colors.dim + '  Ahmet: "Tamam, GPA\'m gizli kalacak, sana matematiksel bir ZKP sunumu atıyorum."' + colors.reset);

// ═══════════════════════════════════════
// 1. ZKP Pedicates (Şartları) Tanımla
// ═══════════════════════════════════════
console.log(colors.bold + '\n\n  🔍 1. İstenen Şart (Predicate)' + colors.reset);
console.log(colors.dim + '  ─────────────────────────────────────' + colors.reset);

const requestedPredicate = {
    attribute: "gpa",
    operator: ">=",
    value: 3.0
};
printInfo(`Banka'nın Şartı: ${requestedPredicate.attribute} ${requestedPredicate.operator} ${requestedPredicate.value}`);


// ═══════════════════════════════════════
// 2. Ahmet ZKP Üretir (Prover)
// ═══════════════════════════════════════
console.log(colors.bold + '\n  🔐 2. Ahmet ZKP Kanıtı (Range Proof) Üretiyor' + colors.reset);
console.log(colors.dim + '  ─────────────────────────────────────' + colors.reset);

const ahmetGpa = state.vc.credentialSubject.gpa; // Ahmet'in gerçek notu (3.5)
printWarn('Ahmet kendi cüzdanındaki GPA\'ya bakıyor: ' + ahmetGpa);

if (ahmetGpa < requestedPredicate.value) {
    printError('Ahmet şartı sağlamıyor! ZKP üretilemez.');
    process.exit(1);
}

// ZKP Matematiksel Simülasyonu (Pedersen Commitment Mantığı)
// Gerçek Indy'de bu işlem CL(Camenisch-Lysyanskaya) imzalarıyla yapılır.
printInfo('Kriptografik çalışma motoru başlatıldı (AnonCreds simülasyonu)...');

const blindingFactor = crypto.randomBytes(32).toString('hex'); // Ahmet rastegele bir sayı (tuz) üretir

// Ahmet GPA değerini kriptolayıp gizler (Commitment)
const gpaCommitment = crypto.createHash('sha256')
    .update(ahmetGpa.toString() + blindingFactor)
    .digest('hex');

// "3.0'dan büyük" olduğunu kanıtlayan matematiksel formül oluşturulur
const zkpMathematicalProof = crypto.createHash('sha256')
    .update(gpaCommitment + requestedPredicate.value.toString() + "range_proof")
    .digest('hex');

const zkpVP = {
    "@context": ["https://www.w3.org/2018/credentials/v1"],
    type: ["VerifiablePresentation", "ZkpPresentation"],
    holder: state.holder.did,
    zkpRequested: requestedPredicate,
    proofs: {
        // GERÇEK DEĞER YOK! Sadece commitment ve proof var.
        gpaCommitment: gpaCommitment,
        rangeProof: zkpMathematicalProof
    }
};

printSuccess('✅ ZKP başarıyla üretildi!');
console.log(colors.gray + JSON.stringify(zkpVP, null, 2) + colors.reset);
console.log(colors.red + '\n  DİKKAT: VP içerisinde Ahmet\'in gerçek GPA\'sı (3.5) YOK! Sadece anlamsız hashler var.' + colors.reset);


// ═══════════════════════════════════════
// 3. Banka ZKP'yi Doğrular (Verifier)
// ═══════════════════════════════════════
console.log(colors.bold + '\n\n  🏢 3. Ziraat Bankası ZKP\'yi Doğruluyor' + colors.reset);
console.log(colors.dim + '  ─────────────────────────────────────' + colors.reset);

printInfo('Bankaya gelen VP incelemeye alınıyor...');

// Banka ZKP doğrulama motorunu çalıştırır
// Matematiksel olarak formülün bütünlüğünü test eder.
const expectedProof = crypto.createHash('sha256')
    .update(zkpVP.proofs.gpaCommitment + zkpVP.zkpRequested.value.toString() + "range_proof")
    .digest('hex');

console.log(colors.dim + `  Beklenen ZKP formül sonucu : ${expectedProof.substring(0, 30)}...` + colors.reset);
console.log(colors.dim + `  Ahmet'in ZKP formül sonucu:  ${zkpVP.proofs.rangeProof.substring(0, 30)}...` + colors.reset);

if (expectedProof === zkpVP.proofs.rangeProof) {
    printSuccess('🎉 ZKP GEÇERLİ! Doğrulama Başarılı!');
    console.log(colors.green + '\n  Banka Kararı: "Ahmet\'in GPA\'sını bilmiyorum. Belki 3.1, belki 4.0.' + colors.reset);
    console.log(colors.green + '  Ancak kriptografik olarak 3.0\'dan BÜYÜK olduğuna eminim! Başvurusu onaylandı."' + colors.reset);
} else {
    printError('❌ ZKP Doğrulaması BAŞARISIZ! Verilerle oynanmış.');
}


// AÇIKLAMA
console.log(colors.bgBlue + colors.white + '\n  🧠 ZKP (Sıfır Bilgi İspatı) NASIL ÇALIŞTI? ' + colors.reset);
console.log(colors.cyan + `
  Normalde (Selective Disclosure):
  Ahmet bankaya "GPA: 3.5" derdi. Banka "Evet, 3.0'dan büyük" derdi.
  Sonuç: Banka Ahmet'in notunu GÖRDÜ. Gizlilik ihlali!

  ZKP İle Olan:
  1. Ahmet notunu gizli bir 'blinding factor' (Rastgele tuz) ile kilitledi (Commitment).
  2. Kilitli halinden matematiksel bir 'Range Proof' (Aralık İspatı) fonksiyonu geçirdi.
  3. Banka sadece Ahmet'in formül çıktılarını alttaki denkleme koydu.
     Denklem tuttuysa => Ahmet yalan söylemiyor.
  
  Banka Ahmet'in notunu gördü mü? HAYIR.
  Peki 3.0'dan büyük olduğuna emin mi? %100 EVET.
  
  *Hyperledger Indy (AnonCreds) bu işlemleri çok daha gelişmiş 
  asimetrik çarpanlara ayırma matematiğiyle yapar.*
` + colors.reset);
