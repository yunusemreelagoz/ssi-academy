/* ═══════════════════════════════════════════════════════════════
   crypto-utils.js — Temel Kriptografik Yardımcı Fonksiyonlar
   
   Bu dosya gerçek Ed25519 anahtar çifti üretir, imzalar ve doğrular.
   Ed25519, Hyperledger Indy'nin de kullandığı imza algoritmasıdır.
   ═══════════════════════════════════════════════════════════════ */

import * as ed from '@noble/ed25519';
import { sha512 } from '@noble/hashes/sha2.js';
import { binary_to_base58, base58_to_binary } from 'base58-js';
import { base58btc } from 'multiformats/bases/base58';
import crypto from 'crypto';

// Ed25519 v3 için SHA-512 hash fonksiyonunu ayarla
ed.hashes.sha512 = sha512;

// ─────────────────────────────────────────────
// 1. ANAHTAR ÇİFTİ ÜRETME
// ─────────────────────────────────────────────

/**
 * Gerçek Ed25519 anahtar çifti üretir.
 * 
 * Private Key: 32 byte rastgele sayı (GİZLİ!)
 * Public Key:  Private Key'den matematiksel olarak türetilir
 * 
 * @returns {{ privateKey: Uint8Array, publicKey: Uint8Array }}
 */
export function generateKeyPair() {
    // 32 byte kriptografik olarak güvenli rastgele sayı
    const privateKey = ed.utils.randomSecretKey();
    
    // Public key, private key'den MATEMATIKSEL olarak türetilir
    // Private key → Public key: KOLAY (tek yönlü fonksiyon)
    // Public key → Private key: İMKANSIZ (bu yüzden güvenli!)
    const publicKey = ed.getPublicKey(privateKey);
    
    return { privateKey, publicKey };
}

// ─────────────────────────────────────────────
// 2. DID OLUŞTURMA (did:key metodu)
// ─────────────────────────────────────────────

/**
 * Public Key'den did:key formatında DID oluşturur.
 * 
 * did:key metodu:
 * 1. Public key'in başına multicodec prefix eklenir (ed25519 = 0xed01)
 * 2. Multibase base58btc ile encode edilir (z ile başlar)
 * 3. "did:key:" prefix'i eklenir
 * 
 * @param {Uint8Array} publicKey - Ed25519 public key (32 byte)
 * @returns {string} DID string (örn: "did:key:z6Mkf...")
 */
export function createDIDKey(publicKey) {
    // Ed25519 multicodec prefix: 0xed, 0x01
    const multicodecPrefix = new Uint8Array([0xed, 0x01]);
    
    // Prefix + public key birleştir
    const multicodecKey = new Uint8Array(multicodecPrefix.length + publicKey.length);
    multicodecKey.set(multicodecPrefix);
    multicodecKey.set(publicKey, multicodecPrefix.length);
    
    // Base58btc encode (multibase 'z' prefix ile)
    const encoded = base58btc.encode(multicodecKey);
    
    return `did:key:${encoded}`;
}

// ─────────────────────────────────────────────
// 3. DID DOCUMENT OLUŞTURMA
// ─────────────────────────────────────────────

/**
 * DID'den W3C standartlarına uygun DID Document oluşturur.
 * 
 * DID Document şunları içerir:
 * - id: DID'in kendisi
 * - verificationMethod: Public key bilgileri (imza doğrulama için)
 * - authentication: Kimlik doğrulama yöntemleri
 * - assertionMethod: İddia/beyan yöntemleri (VC imzalamak için)
 * 
 * @param {string} did - DID string
 * @param {Uint8Array} publicKey - Ed25519 public key
 * @returns {Object} DID Document (JSON-LD formatında)
 */
export function createDIDDocument(did, publicKey) {
    const publicKeyBase58 = binary_to_base58(publicKey);
    
    return {
        "@context": [
            "https://www.w3.org/ns/did/v1",
            "https://w3id.org/security/suites/ed25519-2020/v1"
        ],
        "id": did,
        "verificationMethod": [
            {
                "id": `${did}#keys-1`,
                "type": "Ed25519VerificationKey2020",
                "controller": did,
                "publicKeyBase58": publicKeyBase58
            }
        ],
        "authentication": [
            `${did}#keys-1`
        ],
        "assertionMethod": [
            `${did}#keys-1`
        ]
    };
}

// ─────────────────────────────────────────────
// 4. DİJİTAL İMZA
// ─────────────────────────────────────────────

/**
 * Bir veriyi private key ile dijital olarak imzalar.
 * 
 * İmza süreci:
 * 1. Veri JSON olarak stringe çevrilir
 * 2. UTF-8 byte dizisine dönüştürülür
 * 3. Ed25519 algoritması ile imzalanır
 * 
 * @param {Object} data - İmzalanacak veri
 * @param {Uint8Array} privateKey - Ed25519 private key
 * @returns {string} Base58 encoded imza
 */
export function signData(data, privateKey) {
    const dataString = JSON.stringify(data, null, 0);
    const dataBytes = new TextEncoder().encode(dataString);
    const signature = ed.sign(dataBytes, privateKey);
    return binary_to_base58(signature);
}

/**
 * Bir imzayı public key ile doğrular.
 * 
 * Doğrulama:
 * - İmza + Orijinal veri + Public key → DOĞRU/YANLIŞ
 * - İmza sahte ise veya veri değiştirilmişse → YANLIŞ döner
 * 
 * @param {Object} data - Orijinal veri
 * @param {string} signatureBase58 - Base58 encoded imza
 * @param {Uint8Array} publicKey - Ed25519 public key
 * @returns {boolean} İmza geçerli mi?
 */
export function verifySignature(data, signatureBase58, publicKey) {
    const dataString = JSON.stringify(data, null, 0);
    const dataBytes = new TextEncoder().encode(dataString);
    const signatureBytes = base58_to_binary(signatureBase58);
    return ed.verify(signatureBytes, dataBytes, publicKey);
}

// ─────────────────────────────────────────────
// 5. YARDIMCI FONKSİYONLAR
// ─────────────────────────────────────────────

/**
 * Byte dizisini hex string'e çevirir (okunabilirlik için)
 */
export function toHex(bytes) {
    return Array.from(bytes).map(b => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Byte dizisini Base58'e çevirir
 */
export function toBase58(bytes) {
    return binary_to_base58(bytes);
}

/**
 * Base58'den byte dizisine çevirir
 */
export function fromBase58(str) {
    return base58_to_binary(str);
}

/**
 * Konsola renkli çıktı yazdırır
 */
export const colors = {
    reset: '\x1b[0m',
    bold: '\x1b[1m',
    dim: '\x1b[2m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    magenta: '\x1b[35m',
    cyan: '\x1b[36m',
    white: '\x1b[37m',
    bgBlue: '\x1b[44m',
    bgGreen: '\x1b[42m',
    bgRed: '\x1b[41m',
    bgYellow: '\x1b[43m',
};

export function printHeader(title) {
    console.log('\n' + colors.bgBlue + colors.white + colors.bold + ` ${title} ` + colors.reset);
    console.log(colors.blue + '═'.repeat(60) + colors.reset);
}

export function printSuccess(msg) {
    console.log(colors.green + '  ✅ ' + msg + colors.reset);
}

export function printInfo(msg) {
    console.log(colors.cyan + '  ℹ️  ' + msg + colors.reset);
}

export function printWarn(msg) {
    console.log(colors.yellow + '  ⚠️  ' + msg + colors.reset);
}

export function printError(msg) {
    console.log(colors.red + '  ❌ ' + msg + colors.reset);
}

export function printKey(label, value) {
    console.log(colors.dim + `  ${label}: ` + colors.reset + colors.cyan + value + colors.reset);
}

export function printJSON(label, obj) {
    console.log(colors.dim + `  ${label}:` + colors.reset);
    const lines = JSON.stringify(obj, null, 2).split('\n');
    lines.forEach(line => {
        console.log(colors.white + '    ' + line + colors.reset);
    });
}
