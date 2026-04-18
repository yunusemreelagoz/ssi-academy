/* ═══════════════════════════════════════════════════════════════
   1-did-olustur.js — Gerçek DID Oluşturma
   
   Bu script gerçek Ed25519 anahtar çifti üretir ve
   did:key formatında DID oluşturur.
   
   Çalıştır: node 1-did-olustur.js
   ═══════════════════════════════════════════════════════════════ */

import {
    generateKeyPair, createDIDKey, createDIDDocument,
    toHex, toBase58,
    printHeader, printSuccess, printInfo, printWarn, printKey, printJSON, colors
} from './crypto-utils.js';
import fs from 'fs';

printHeader('ADIM 1: GERÇEK DID OLUŞTURMA');

console.log(colors.yellow + '\n  📖 Ne yapıyoruz?' + colors.reset);
console.log(colors.dim + '  Gerçek Ed25519 anahtar çifti üretip, bundan DID oluşturacağız.' + colors.reset);
console.log(colors.dim + '  Bu, Hyperledger Indy\'nin de kullandığı algoritma!' + colors.reset);

// ═══════════════════════════════════════
// 1. İTÜ (Issuer) için DID oluştur
// ═══════════════════════════════════════
console.log(colors.bold + '\n\n  🏛️  İTÜ (Issuer) İçin Anahtar Üretimi' + colors.reset);
console.log(colors.dim + '  ─────────────────────────────────────' + colors.reset);

const issuerKeys = generateKeyPair();

printInfo('Private Key (GİZLİ! Kimseyle paylaşma!):');
printKey('  Hex    ', toHex(issuerKeys.privateKey));
printKey('  Base58 ', toBase58(issuerKeys.privateKey));
printWarn('Bu anahtarı KESİNLİKLE kimseyle paylaşmamalısın!');

console.log();
printInfo('Public Key (Herkesle paylaşılabilir):');
printKey('  Hex    ', toHex(issuerKeys.publicKey));
printKey('  Base58 ', toBase58(issuerKeys.publicKey));

const issuerDID = createDIDKey(issuerKeys.publicKey);
console.log();
printSuccess('İTÜ DID oluşturuldu:');
printKey('  DID', issuerDID);

const issuerDIDDoc = createDIDDocument(issuerDID, issuerKeys.publicKey);
console.log();
printInfo('İTÜ DID Document:');
printJSON('', issuerDIDDoc);

// ═══════════════════════════════════════
// 2. Ahmet (Holder) için DID oluştur
// ═══════════════════════════════════════
console.log(colors.bold + '\n\n  👤 Ahmet (Holder) İçin Anahtar Üretimi' + colors.reset);
console.log(colors.dim + '  ─────────────────────────────────────' + colors.reset);

const holderKeys = generateKeyPair();

printInfo('Private Key (GİZLİ!):');
printKey('  Base58 ', toBase58(holderKeys.privateKey));

printInfo('Public Key:');
printKey('  Base58 ', toBase58(holderKeys.publicKey));

const holderDID = createDIDKey(holderKeys.publicKey);
printSuccess('Ahmet DID oluşturuldu:');
printKey('  DID', holderDID);

const holderDIDDoc = createDIDDocument(holderDID, holderKeys.publicKey);
printInfo('Ahmet DID Document:');
printJSON('', holderDIDDoc);

// ═══════════════════════════════════════
// 3. Ziraat Bankası (Verifier) için DID oluştur
// ═══════════════════════════════════════
console.log(colors.bold + '\n\n  🏢 Ziraat Bankası (Verifier) İçin Anahtar Üretimi' + colors.reset);
console.log(colors.dim + '  ────────────────────────────────────────────────' + colors.reset);

const verifierKeys = generateKeyPair();
const verifierDID = createDIDKey(verifierKeys.publicKey);

printKey('  Public Key (Base58)', toBase58(verifierKeys.publicKey));
printSuccess('Ziraat DID oluşturuldu:');
printKey('  DID', verifierDID);

// ═══════════════════════════════════════
// 4. Tüm verileri kaydet (sonraki adımlar için)
// ═══════════════════════════════════════
const state = {
    issuer: {
        name: 'İstanbul Teknik Üniversitesi',
        did: issuerDID,
        publicKey: toBase58(issuerKeys.publicKey),
        privateKey: toBase58(issuerKeys.privateKey),
        didDocument: issuerDIDDoc
    },
    holder: {
        name: 'Ahmet Yılmaz',
        did: holderDID,
        publicKey: toBase58(holderKeys.publicKey),
        privateKey: toBase58(holderKeys.privateKey),
        didDocument: holderDIDDoc
    },
    verifier: {
        name: 'Ziraat Bankası',
        did: verifierDID,
        publicKey: toBase58(verifierKeys.publicKey),
        privateKey: toBase58(verifierKeys.privateKey)
    }
};

fs.writeFileSync('state.json', JSON.stringify(state, null, 2));

console.log(colors.bgGreen + colors.white + colors.bold + '\n  ✅ ADIM 1 TAMAMLANDI! ' + colors.reset);
console.log(colors.green + '  Tüm DID\'ler oluşturuldu ve state.json\'a kaydedildi.' + colors.reset);
console.log(colors.dim + '\n  Sonraki adım: node 2-vc-ver.js\n' + colors.reset);

// ═══════════════════════════════════════
// AÇIKLAMA
// ═══════════════════════════════════════
console.log(colors.bgYellow + colors.white + '  📚 ÖĞRENME NOTU ' + colors.reset);
console.log(colors.yellow + `
  Şimdi ne oldu?
  ─────────────
  1. Her aktör için GERÇEK Ed25519 anahtar çifti ürettik.
     (Hyperledger Indy de aynı algoritmayı kullanır!)
  
  2. Public Key'den did:key formatında DID oluşturduk.
     DID = "did:key:" + multibase(multicodec_prefix + public_key)
  
  3. DID Document oluşturduk. Bu belge şunları içerir:
     - verificationMethod: İmza doğrulama için public key
     - authentication: Kimlik doğrulamada hangi key kullanılacak
     - assertionMethod: VC imzalamada hangi key kullanılacak
  
  ⚡ Gerçek Indy'den farkı:
  - Indy'de DID'ler blockchain'e yazılır
  - did:key'de blockchain yok, DID doğrudan public key'den türer
  - Ama kriptografi AYNI: Ed25519!
` + colors.reset);
