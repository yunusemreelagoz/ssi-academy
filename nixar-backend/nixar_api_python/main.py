from nixar.nixar_api import NixarMessageType
import sys
import ctypes
import os
import json
import hashlib

if sys.platform == "darwin":
    try:
        ctypes.CDLL(os.path.abspath("libsodium.23.dylib"))
        ctypes.CDLL(os.path.abspath("libzmq.5.dylib"))
    except:
        pass

from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from nixar.nixar_api import Nixar, CredDefIssuanceType
import test_utils
from test_utils import create_nixar_agent_w_json_wallet, get_timestamp_tag

app = FastAPI(
    title="Nixar Core API Gateway (SSI)",
    description="TAM KONTROLLÜ KURUMSAL SSI MİKROSERVİSİ",
    version="1.0.0"
)

# Hafızada tutulan ajanlar (Performans için her istekte cüzdan aç-kapa yapmamak adına)
active_agents: Dict[str, Nixar] = {}

# ==============================================================================
# WEBHOOK DURUM DEPOLAMA
# Webhook gelen credential_request veya presentation'ı işleyebilmek için
# Issuer'ın önceden oluşturduğu offer/request bilgileri hafızada tutulur.
# ==============================================================================

# Anahtar: issuer_nonce  |  Değer: {agent_alias, cred_def_id, issuer_nonce, cred_values}
pending_credential_offers: Dict[str, dict] = {}

# Anahtar: presentation nonce  |  Değer: {agent_alias, presentation_request}
pending_presentation_requests: Dict[str, dict] = {}

# ==============================================================================
# KALICI DID KAYIT DEFTERİ (Agent Registry)
# Her kayıt: { "did": "...", "seed_hash": "sha256(seed)" }
# Best Practice:
#   - İlk init'te canonical DID ve seed hash'i birlikte diske yazılır.
#   - Sonraki init'lerde seed hash karşılaştırılır; farklıysa 403 döner.
#   - Seed plaintext saklanmaz — sadece SHA-256 hash'i tutulur.
# ==============================================================================

_REGISTRY_PATH = os.path.join(os.path.dirname(__file__), ".tmp", "agent_registry.json")

def _hash_seed(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()

def _load_registry() -> Dict[str, Dict]:
    if os.path.exists(_REGISTRY_PATH):
        with open(_REGISTRY_PATH, "r") as f:
            return json.load(f)
    return {}

def _save_registry(registry: Dict[str, Dict]):
    os.makedirs(os.path.dirname(_REGISTRY_PATH), exist_ok=True)
    with open(_REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)

# Uygulama başlarken mevcut kayıtları yükle
_agent_registry: Dict[str, Dict] = _load_registry()

# ==============================================================================
# PYDANTIC MODELLERİ (VERİ TRANSFER OBJELERİ - DTO)
# ==============================================================================

class AgentInitReq(BaseModel):
    alias: str
    password: str
    role: Optional[str] = None
    seed: Optional[str] = None

class HolderInitReq(BaseModel):
    alias: str
    password: str
    seed: Optional[str] = None

class SchemaCreateReq(BaseModel):
    agent_alias: str
    schema_name: str
    attributes: List[str]
    version: str = "1.0"

class CredDefCreateReq(BaseModel):
    agent_alias: str
    schema_id: str
    is_revokable: bool = False

class CredentialOfferReq(BaseModel):
    agent_alias: str
    cred_def_id: str

class CredentialIssueReq(BaseModel):
    agent_alias: str
    cred_request: Dict[str, Any]
    credential_values: Dict[str, Any]
    issuer_nonce: str

class PresentationCreateReq(BaseModel):
    agent_alias: str
    presentation_request: Dict[str, Any]

class VerifyPresentationReq(BaseModel):
    agent_alias: str
    presentation_request: Dict[str, Any]
    presentation: Dict[str, Any]

# ==============================================================================
# 1. AJAN (CÜZDAN) YÖNETİMİ
# ==============================================================================

@app.post("/api/v1/agents/init", tags=["Kurumsal Cüzdan Yönetimi"])
def init_agent(req: AgentInitReq):
    """
    Kurumsal bir ajan (Issuer veya Verifier) oluşturur ve Ledger'a kaydeder.

    **Kimler kullanmalı?**
    - Kimlik Vericiler (Issuer): Üniversite, Nüfus Müdürlüğü vb.
    - Doğrulayıcılar (Verifier): Banka, Noter vb.
    - Vatandaş/Öğrenci (Holder) için → `/api/v1/holder/init` kullanın!

    **⚠️ Seed Kuralı:** Bir alias ilk kez hangi seed ile init edildiyse,
    sonraki tüm init'lerde aynı seed verilmelidir. Farklı seed → HTTP 403.

    **Örnek İstek:**
    ```json
    {
      "alias": "ITU",
      "password": "güçlü-şifre-123",
      "role": "ENDORSER",
      "seed": "00000000000000000000000000000ITU"
    }
    ```
    - `alias`: Ajana verilen benzersiz isim (örn: "ITU", "ZiraatBankasi")
    - `password`: Cüzdan şifresi (her açılışta aynı olmalı)
    - `role`: `"ENDORSER"` (Issuer/Verifier için) veya `null` (sadece doğrulayıcı)
    - `seed`: Tam 32 karakter. Aynı seed → her zaman aynı DID (deterministik). Sabit tutun!

    **Örnek Yanıt:**
    ```json
    {
      "status": "success",
      "message": "Ajan basariyla olusturuldu",
      "did": "4fUYw6T3PPht7KLMAkczas"
    }
    ```
    """
    try:
        # ── SEED DOĞRULAMASI ─────────────────────────────────────────────────
        # Ajan daha önce kaydedildiyse, verilen seed kayıttaki ile eşleşmeli.
        if req.alias in _agent_registry:
            record = _agent_registry[req.alias]
            stored_hash = record.get("seed_hash")
            incoming_hash = _hash_seed(req.seed) if req.seed else None
            if stored_hash and incoming_hash != stored_hash:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        f"'{req.alias}' ajanı daha önce farklı bir seed ile kaydedildi. "
                        "Canonical DID'i korumak için orijinal seed kullanılmalıdır."
                    )
                )

        # Hafıza kontrolü (seed doğru, ajan zaten aktif)
        if req.alias in active_agents:
            record = _agent_registry.get(req.alias, {})
            return {"status": "success", "message": "Agent zaten aktif.", "did": record.get("did")}

        # Tohumu Base64'e çevir (Eğer verilmişse)
        encoded_seed = test_utils.encode_base64(req.seed) if req.seed else None

        # Ajanı yarat veya yükle
        password_cb = lambda: test_utils.native_string(req.password)
        agent = create_nixar_agent_w_json_wallet(req.alias, password_cb, req.role, base64_seed=encoded_seed)
        active_agents[req.alias] = agent

        # ── İLK KAYIT: DID + seed hash birlikte saklanır ──────────────────────
        if req.alias not in _agent_registry:
            if encoded_seed:
                try:
                    did_info = agent.create_local_did(encoded_seed)
                    _agent_registry[req.alias] = {
                        "did": did_info.get("id"),
                        "seed_hash": _hash_seed(req.seed)
                    }
                    _save_registry(_agent_registry)
                except Exception:
                    pass

        record = _agent_registry.get(req.alias, {})
        return {"status": "success", "message": "Ajan basariyla olusturuldu", "did": record.get("did")}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/network/info", tags=["Kurumsal Cüzdan Yönetimi"])
def get_network_info():
    """
    Sunucunun bağlı olduğu Indy ağı hakkında bilgi döner.

    Genesis dosyasındaki node IP'lerini okuyarak hangi ağa bağlı olunduğunu tespit eder.
    """
    genesis_path = os.path.join(os.path.dirname(__file__), "genesis.txn")
    use_von_network = os.environ.get("USE_VON_NETWORK", "1") == "1"

    nodes = []
    network_name = "bilinmiyor"
    try:
        with open(genesis_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    txn = json.loads(line)
                    alias = txn.get("txn", {}).get("data", {}).get("data", {}).get("alias", "")
                    client_ip = txn.get("txn", {}).get("data", {}).get("data", {}).get("client_ip", "")
                    client_port = txn.get("txn", {}).get("data", {}).get("data", {}).get("client_port", "")
                    if alias and client_ip:
                        nodes.append({"alias": alias, "ip": client_ip, "port": client_port})
                except Exception:
                    pass

        # IP adresine göre ağı tahmin et
        ips = {n["ip"] for n in nodes}
        if "127.0.0.1" in ips or "172." in str(ips):
            network_name = "von_network (local)"
        elif "138.197.138.255" in ips:
            network_name = "BCovrin Test Network"
        elif "130.107.207.129" in ips:
            network_name = "SSI Türkiye Testnet"
        elif nodes:
            network_name = f"özel ağ ({list(ips)[0]})"
    except FileNotFoundError:
        return {"error": "genesis.txn bulunamadı", "genesis_path": genesis_path}

    return {
        "network_name": network_name,
        "genesis_path": genesis_path,
        "use_von_network": use_von_network,
        "node_count": len(nodes),
        "nodes": nodes,
        "active_agents": list(active_agents.keys()),
    }

@app.get("/api/v1/agents/{alias}/did", tags=["Kurumsal Cüzdan Yönetimi"])
def get_agent_did(alias: str):
    """
    Daha önce init edilmiş bir ajanın canonical (kalıcı) DID'ini döner.

    **Örnek İstek:**
    ```
    GET /api/v1/agents/ITU/did
    ```
    - `alias`: Daha önce init edilen ajanın adı (URL parametresi)

    **Örnek Yanıt:**
    ```json
    {
      "alias": "ITU",
      "did": "4fUYw6T3PPht7KLMAkczas"
    }
    ```
    **⚠️ Not:** Ajan önce init edilmiş olmalıdır, yoksa 404 döner.
    """
    if alias not in _agent_registry:
        raise HTTPException(status_code=404, detail="Agent bulunamadı (Önce Init yapın)")
    record = _agent_registry.get(alias, {})
    did = record.get("did") if isinstance(record, dict) else record
    if not did:
        raise HTTPException(status_code=404, detail="DID bulunamadı. Ajanı seed ile init edin.")
    return {"alias": alias, "did": did}

# ==============================================================================
# 2. SCHEMA (ŞABLON) VE CRED-DEF YÖNETİMİ
# ==============================================================================

@app.post("/api/v1/schema/create", tags=["Verici / Üniversite (Issuer)"])
def create_schema(req: SchemaCreateReq):
    """
    Kimlik belgesinin hangi alanları içereceğini tanımlayan Şema'yı oluşturur ve Ledger'a yazar.

    **Akıştaki yeri:** ADIM 1 — Issuer (üniversite) önce şemayı tanımlar.

    **Örnek İstek:**
    ```json
    {
      "agent_alias": "ITU",
      "schema_name": "Universite Diplomasi",
      "attributes": ["name", "department", "grade"],
      "version": "1.0"
    }
    ```
    - `agent_alias`: Daha önce init edilen Issuer ajanının adı
    - `schema_name`: Şema adı (benzersiz olması önerilir, aynı ada tekrar yazılamaz)
    - `attributes`: Kimlik belgesinin içereceği alan isimleri listesi
    - `version`: Şema versiyonu (varsayılan: "1.0")

    **Örnek Yanıt:**
    ```json
    {
      "status": "success",
      "schema_id": "4fUYw6T3PPht7KLMAkczas:2:Universite Diplomasi:1.0"
    }
    ```
    **⚠️ Not:** `schema_id` bir sonraki adımda (credential-definition) kullanılacak — saklayın!
    """
    if req.agent_alias not in active_agents:
        raise HTTPException(status_code=404, detail="Agent aktif değil")
    agent = active_agents[req.agent_alias]
    try:
        schema_id = agent.issuer_create_schema(req.schema_name, req.attributes, req.version)
        return {"status": "success", "schema_id": schema_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/credential-definition/create", tags=["Verici / Üniversite (Issuer)"])
def create_cred_def(req: CredDefCreateReq):
    """
    Şemayı baz alarak kriptografik anahtar çiftini oluşturur ve Ledger'a yazar (Credential Definition).

    **Akıştaki yeri:** ADIM 2 — Schema oluşturulduktan sonra, credential ihraç etmeden önce yapılır.

    **Örnek İstek:**
    ```json
    {
      "agent_alias": "ITU",
      "schema_id": "4fUYw6T3PPht7KLMAkczas:2:Universite Diplomasi:1.0",
      "is_revokable": false
    }
    ```
    - `agent_alias`: Daha önce init edilen Issuer ajanının adı
    - `schema_id`: Bir önceki adımdan dönen schema_id değeri
    - `is_revokable`: İptal mekanizması ister misin? (şimdilik `false` önerilir)

    **Örnek Yanıt:**
    ```json
    {
      "status": "success",
      "cred_def_id": "4fUYw6T3PPht7KLMAkczas:3:CL:20:bilgem"
    }
    ```
    **⚠️ Not:** `cred_def_id` sonraki tüm adımlarda (offer, issue, verify) kullanılacak — saklayın!
    Ledger'a yazılması zaman alabilir; hemen ardından credential oluşturursanız 5 saniye bekleyin.
    """
    if req.agent_alias not in active_agents:
        raise HTTPException(status_code=404, detail="Agent aktif değil")
    agent = active_agents[req.agent_alias]
    try:
        tag = get_timestamp_tag()
        cred_def_id = agent.issuer_create_credential_definition(req.schema_id, req.is_revokable, tag, CredDefIssuanceType.ISSUANCE_BY_DEFAULT, 1000)
        return {"status": "success", "cred_def_id": cred_def_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# 3. İHRAÇ (ISSUANCE) AKIŞI
# ==============================================================================

@app.post("/api/v1/issuer/create-offer", tags=["Verici / Üniversite (Issuer)"])
def create_offer(req: CredentialOfferReq):
    """
    Issuer'ın Holder'a göndereceği kimlik belgesi teklifini (Credential Offer) oluşturur.

    **Akıştaki yeri:** ADIM 3 — Credential Definition hazır olduktan sonra her diploma/kimlik için çağrılır.

    **Örnek İstek:**
    ```json
    {
      "agent_alias": "ITU",
      "cred_def_id": "4fUYw6T3PPht7KLMAkczas:3:CL:20:bilgem"
    }
    ```
    - `agent_alias`: Daha önce init edilen Issuer ajanının adı
    - `cred_def_id`: Bir önceki adımdan dönen cred_def_id değeri

    **Örnek Yanıt:**
    ```json
    {
      "offer": { ... },
      "issuer_nonce": "748392019283746152"
    }
    ```
    **⚠️ Not:** Dönen `offer` ve `issuer_nonce` değerlerini saklayın.
    `offer` → holder/create-request'e gönderilir.
    `issuer_nonce` → issuer/issue-credential'da tekrar kullanılır.
    """
    agent = active_agents.get(req.agent_alias)
    if not agent: raise HTTPException(status_code=404, detail="Agent aktif değil")
    
    import random
    nonce = str(random.getrandbits(80))
    offer = agent.issuer_create_credential_offer(req.cred_def_id, nonce)
    return {"offer": offer, "issuer_nonce": nonce}

@app.post("/api/v1/holder/create-request", tags=["Vatandaş / Öğrenci (Holder)"])
def create_request(agent_alias: str, offer: Dict[str, Any] = Body(...)):
    """
    Holder (öğrenci/vatandaş), kendisine gelen teklifi (offer) kabul edip kriptografik istek oluşturur.

    **Akıştaki yeri:** ADIM 4 — Issuer'ın gönderdiği `offer` bu endpoint'e iletilir.

    **Örnek İstek:**
    - URL parametresi: `?agent_alias=Ahmet`
    - Body: issuer/create-offer'dan gelen `offer` alanının içeriği (doğrudan yapıştırın)
    ```json
    {
      "schema_id": "...",
      "cred_def_id": "...",
      ...
    }
    ```

    **Örnek Yanıt:**
    ```json
    {
      "credential_request": { ... }
    }
    ```
    **⚠️ Not:** Dönen `credential_request` → issuer/issue-credential'a gönderilir.
    """
    agent = active_agents.get(agent_alias)
    if not agent: raise HTTPException(status_code=404, detail="Agent aktif değil")
    
    cred_req = agent.prover_create_credential_request(offer)
    return {"credential_request": cred_req}

@app.post("/api/v1/issuer/issue-credential", tags=["Verici / Üniversite (Issuer)"])
def issue_credential(req: CredentialIssueReq):
    """
    Issuer, Holder'ın isteğine gerçek verileri doldurup kriptografik olarak imzalar ve belgeyi ihraç eder.

    **Akıştaki yeri:** ADIM 5 — holder/create-request'ten gelen `credential_request` burada kullanılır.

    **Örnek İstek:**
    ```json
    {
      "agent_alias": "ITU",
      "cred_request": { ... },
      "credential_values": {
        "name":       { "raw": "Ahmet Yılmaz",        "encoded": "1" },
        "department": { "raw": "Bilgisayar Müh.",      "encoded": "2" },
        "grade":      { "raw": "3.85",                 "encoded": "3" }
      },
      "issuer_nonce": "748392019283746152"
    }
    ```
    - `cred_request`: holder/create-request'ten dönen `credential_request` değeri
    - `credential_values`: Her alan için `raw` (okunabilir) ve `encoded` (sayısal) değer çifti
    - `issuer_nonce`: issuer/create-offer'dan gelen `issuer_nonce` değeri

    **Örnek Yanıt:**
    ```json
    {
      "credential": { ... }
    }
    ```
    **⚠️ Not:** Dönen `credential` → holder/store-credential'a gönderilir.
    """
    agent = active_agents.get(req.agent_alias)
    if not agent: raise HTTPException(status_code=404, detail="Agent aktif değil")
    
    try:
        cred_info = agent.issuer_create_credential(req.cred_request, req.credential_values, req.issuer_nonce)
        return {"credential": cred_info["credential"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/holder/store-credential", tags=["Vatandaş / Öğrenci (Holder)"])
def store_credential(agent_alias: str, credential: Dict[str, Any] = Body(...)):
    """
    Holder (öğrenci/vatandaş), üniversitenin imzaladığı belgeyi kendi cüzdanına kaydeder.

    **Akıştaki yeri:** ADIM 6 — issuer/issue-credential'dan gelen `credential` burada saklanır.

    **Örnek İstek:**
    - URL parametresi: `?agent_alias=Ahmet`
    - Body: issuer/issue-credential'dan dönen `credential` alanının içeriği (doğrudan yapıştırın)
    ```json
    {
      "schema_id": "...",
      "cred_def_id": "...",
      "values": { ... },
      "signature": { ... },
      ...
    }
    ```

    **Örnek Yanıt:**
    ```json
    {
      "status": "success",
      "message": "Evrak Cüzdana Saklandı!"
    }
    ```
    **⚠️ Not:** Bu adımdan sonra holder ZKP sunumu yapabilir → holder/create-presentation
    """
    agent = active_agents.get(agent_alias)
    if not agent: raise HTTPException(status_code=404, detail="Agent aktif değil")
    
    agent.prover_store_credential(None, credential)
    return {"status": "success", "message": "Evrak Cüzdana Saklandı!"}

# ==============================================================================
# 4. DOĞRULAMA (VERIFICATION) - SIFIR BİLGİ İSPATI (ZKP)
# ==============================================================================

@app.post("/api/v1/holder/create-presentation", tags=["Vatandaş / Öğrenci (Holder)"])
def create_presentation(req: PresentationCreateReq):
    """
    Holder, doğrulayıcının (bankanın) istediği alanlar için ZKP kanıtı (Presentation) oluşturur.
    Paylaşılmak istenmeyen alanlar gizli kalır — sadece istenilen alanlar açılır.

    **Akıştaki yeri:** ADIM 7 — Banka talep gönderir, holder bu talebi karşılayan kanıtı oluşturur.

    **Örnek İstek:**
    ```json
    {
      "agent_alias": "Ahmet",
      "presentation_request": {
        "name": "Banka Kimlik Dogrulama",
        "version": "1.0",
        "nonce": "123456",
        "requestedAttributes": {
          "attr1": { "name": "name",  "restrictions": [{ "cred_def_id": "4fUYw6T3PPht7KLMAkczas:3:CL:20:bilgem" }] },
          "attr2": { "name": "grade", "restrictions": [{ "cred_def_id": "4fUYw6T3PPht7KLMAkczas:3:CL:20:bilgem" }] }
        },
        "requestedPredicates": {}
      }
    }
    ```
    - `agent_alias`: Credential'ı cüzdanında tutan Holder'ın alias'ı
    - `requestedAttributes`: Bankanın görmek istediği alanlar (+ hangi cred_def'e ait olduğu)
    - `requestedPredicates`: Eşitsizlik kanıtları (örn: yaş > 18) — boş bırakılabilir

    **Örnek Yanıt:**
    ```json
    {
      "presentation": { ... }
    }
    ```
    **⚠️ Not:** Dönen `presentation` → verifier/verify-presentation'a gönderilir.
    `department` gibi listelenmeyen alanlar **hiç açıklanmadan** kanıtlanır (ZKP).
    """
    agent = active_agents.get(req.agent_alias)
    if not agent: raise HTTPException(status_code=404, detail="Agent aktif değil")
    
    try:
        vp = agent.prover_create_presentation(req.presentation_request, {})
        return {"presentation": vp}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/verifier/verify-presentation", tags=["Doğrulayıcı / Banka (Verifier)"])
def verify_presentation(req: VerifyPresentationReq):
    """
    Verifier (banka), Holder'dan gelen ZKP kanıtını Ledger üzerinden doğrular.

    **Akıştaki yeri:** ADIM 8 (SON) — holder/create-presentation'dan gelen `presentation` burada doğrulanır.

    **Örnek İstek:**
    ```json
    {
      "agent_alias": "Ziraat",
      "presentation_request": {
        "name": "Banka Kimlik Dogrulama",
        "version": "1.0",
        "nonce": "123456",
        "requestedAttributes": {
          "attr1": { "name": "name",  "restrictions": [{ "cred_def_id": "4fUYw6T3PPht7KLMAkczas:3:CL:20:bilgem" }] },
          "attr2": { "name": "grade", "restrictions": [{ "cred_def_id": "4fUYw6T3PPht7KLMAkczas:3:CL:20:bilgem" }] }
        },
        "requestedPredicates": {}
      },
      "presentation": { ... }
    }
    ```
    - `agent_alias`: Daha önce init edilen Verifier ajanının adı
    - `presentation_request`: holder/create-presentation'a gönderilen ile **aynı** obje olmalı
    - `presentation`: holder/create-presentation'dan dönen `presentation` değeri

    **Örnek Yanıt:**
    ```json
    {
      "is_valid": true,
      "revealed_data": {
        "attr1": "Ahmet Yılmaz",
        "attr2": "3.85"
      }
    }
    ```
    - `is_valid`: Kanıtın kriptografik olarak geçerli olup olmadığı
    - `revealed_data`: Banka'nın görebildiği alanlar (gizli kalan alanlar burada görünmez)
    """
    agent = active_agents.get(req.agent_alias)
    if not agent: raise HTTPException(status_code=404, detail="Agent aktif değil")
    
    try:
        is_valid = agent.verifier_verify_presentation(req.presentation_request, req.presentation)
        
        decoded_attrs = {}
        if is_valid:
            revealed = req.presentation.get("requested_proof", {}).get("revealed_attrs", {})
            for key, val in revealed.items():
                decoded_attrs[key] = val.get("raw")

        return {"is_valid": is_valid, "revealed_data": decoded_attrs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/holder/init", tags=["Vatandaş / Öğrenci (Holder)"])
def init_holder(req: HolderInitReq):
    """
    Vatandaş/Öğrenci (Holder) için yerel cüzdan oluşturur. Ledger'a kayıt YAPILMAZ.

    **Kimler kullanmalı?** Yalnızca Holder'lar (belge sahibi vatandaş/öğrenci).
    Kurumlar (Issuer/Verifier) için → `/api/v1/agents/init` kullanın!

    **Örnek İstek:**
    ```json
    {
      "alias": "Ahmet",
      "password": "ahmet-sifre-456",
      "seed": "000000000000000000000000000Ahmet"
    }
    ```
    - `alias`: Holder'a verilen benzersiz isim
    - `password`: Cüzdan şifresi (her açılışta aynı olmalı)
    - `seed`: Opsiyonel, 32 karakter. Verilirse aynı DID deterministik olarak oluşur.

    **Örnek Yanıt:**
    ```json
    {
      "status": "ok",
      "message": "Holder cüzdanı BAŞARIYLA oluşturuldu (Ledger kaydı YAZILMADI).",
      "agent_alias": "Ahmet"
    }
    ```
    """
    if req.alias in active_agents:
        return {"status": "ok", "message": "Holder Zaten aktif", "agent_alias": req.alias}
    
    try:
        from test_utils import create_holder_agent_w_json_wallet, native_string, encode_base64
        pw_cb = lambda: native_string(req.password)
        b64_seed = encode_base64(req.seed) if req.seed else None

        agent = create_holder_agent_w_json_wallet(req.alias, pw_cb, b64_seed)
        active_agents[req.alias] = agent
        
        return {
            "status": "ok",
            "message": "Holder cüzdanı BAŞARIYLA oluşturuldu (Ledger kaydı YAZILMADI).",
            "agent_alias": req.alias
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Holder oluşturulamadı: {str(e)}")

# ==============================================================================
# DIDCOMM / BAĞLANTI (CONNECTION) MODELLERİ
# ==============================================================================

class InvitationCreateReq(BaseModel):
    agent_alias: str
    label: str
    endpoint_url: str
    seed: Optional[str] = None

class ConnectionAcceptReq(BaseModel):
    agent_alias: str
    connection_request: Dict[str, Any]

class EncryptMessageReq(BaseModel):
    agent_alias: str
    from_did: str
    their_did: str
    message: Any
    message_type: str = "simple"  # simple | credential_offer | credential_request | credential | presentation_request | presentation

class DecryptMessageReq(BaseModel):
    agent_alias: str
    encrypted_message: Dict[str, Any]

class SignDataReq(BaseModel):
    agent_alias: str
    from_did: str
    data: str  # base64 encoded

class VerifySignatureReq(BaseModel):
    agent_alias: str
    their_did: str
    signed_data: str   # base64 encoded orijinal veri
    signature: str     # base64 encoded imza

class SendProofRequestReq(BaseModel):
    agent_alias: str
    connection_id_or_did: str
    presentation_request: Dict[str, Any]

class CredentialOfferCreateReq(BaseModel):
    agent_alias: str
    cred_def_id: str
    cred_values: Dict[str, Any]   # {"ad": {"raw": "Ahmet", "encoded": "1"}, ...}

class IssueForRequestReq(BaseModel):
    agent_alias: str
    cred_request: Dict[str, Any]
    cred_def_id: str   # pending_offers'dan doğru kaydı bulmak için

class SubmitPresentationReq(BaseModel):
    agent_alias: str
    presentation: Dict[str, Any]

class PresentationRequestCreateReq(BaseModel):
    agent_alias: str
    presentation_request: Dict[str, Any]   # name, version, nonce, requestedAttributes, requestedPredicates

class ConnReqCreateReq(BaseModel):
    agent_alias: str
    invitation: Dict[str, Any]

class ConnResAcceptReq(BaseModel):
    agent_alias: str
    connection_response: Dict[str, Any]

# ==============================================================================
# DIDCOMM BAĞLANTILARI VE ÇİFT YÖNLÜ (P2P) İSTEKLER
# ==============================================================================

@app.post("/api/v1/connections/send-proof-request", tags=["Cihaz Bağlantıları"])
def send_proof_request_to_connection(req: SendProofRequestReq):
    """
    Bağlantı kurulmuş bir Holder'a (öğrenci/vatandaş) şifreli kanıt talebi (Proof Request) gönderir.

    **Ne işe yarar?**
    Verifier (örn: banka), daha önce DIDComm bağlantısı kurduğu bir Holder'dan
    belirli alanları kanıtlamasını talep eder. Talep uçtan uca şifrelenerek
    (DIDComm Envelope) hazırlanır — sadece hedef kişi açabilir.

    **Akıştaki yeri:** Bağlantı kurulduktan sonra, Verifier bu endpoint ile
    kanıt talebini şifreler, ardından Holder'ın webhook adresine POST eder.

    **Örnek İstek:**
    ```json
    {
      "agent_alias": "Ziraat",
      "connection_id_or_did": "FjRfZ...Holder_DID",
      "presentation_request": {
        "name": "Banka Kimlik Dogrulama",
        "version": "1.0",
        "nonce": "123456",
        "requestedAttributes": {
          "attr1": { "name": "name", "restrictions": [{ "cred_def_id": "..." }] }
        },
        "requestedPredicates": {}
      }
    }
    ```
    - `agent_alias`: Kanıt talebi gönderen Verifier ajanının adı
    - `connection_id_or_did`: Karşı tarafın (Holder) DID'i — bağlantı listesinden alınır
    - `presentation_request`: Hangi alanların kanıtlanmasını istediğiniz (verify akışıyla aynı format)

    **Örnek Yanıt:**
    ```json
    {
      "status": "success",
      "message": "Zarf hazırlandı, karşı tarafa iletebilirsiniz.",
      "encrypted_proof_request": { ... }
    }
    ```
    **⚠️ Not:** Dönen `encrypted_proof_request` zarfını Holder'ın webhook URL'ine POST etmeniz gerekir.
    """
    agent = active_agents.get(req.agent_alias)
    if not agent: raise HTTPException(status_code=404, detail="Agent aktif değil")
    
    try:
        conns = agent.connection_get_connections()
        from_did = ""
        for c in conns:
            if c.get("their_did") == req.connection_id_or_did:
                from_did = c.get("my_did")
                break
                
        if not from_did:
            raise HTTPException(status_code=400, detail="Bu their_did ile aktif bir bağlantı bulunamadı.")

        encrypted_req = agent.connection_encrypt(
            from_did=from_did,
            their_did=req.connection_id_or_did, 
            message_type=NixarMessageType.MESSAGE_TYPE_PRESENTATION_REQUEST, 
            content=req.presentation_request
        )
        return {"status": "success", "message": "Zarf hazırlandı, karşı tarafa iletebilirsiniz.", "encrypted_proof_request": encrypted_req}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/connections/create-invitation", tags=["Cihaz Bağlantıları"])
def create_connection_invitation(req: InvitationCreateReq):
    """
    Başka bir ajanla (telefon, başka kurum vb.) güvenli DIDComm bağlantısı başlatmak için davetiye oluşturur.

    **Ne işe yarar?**
    İki tarafın (örn: üniversite ↔ öğrenci) uçtan uca şifreli iletişim kurması için
    ilk adım budur. Davetiyeyi oluşturan taraf bir DID ve endpoint bilgisi üretir;
    karşı taraf bu daveti tarayarak (QR kod vb.) bağlantı isteği gönderir.

    **Gerçek hayat senaryosu:** Üniversite bir QR kod oluşturur, öğrenci telefonuyla
    tarar ve otomatik olarak bağlantı isteği gider.

    **Örnek İstek:**
    ```json
    {
      "agent_alias": "ITU",
      "label": "ITU Ogrenci Isleri",
      "endpoint_url": "https://itu.example.com/didcomm/ITU",
      "seed": "00000000000000000000000000ConnIT"
    }
    ```
    - `agent_alias`: Daveti oluşturan ajanın adı
    - `label`: Davetiyede görünecek etiket (karşı tarafa gösterilir)
    - `endpoint_url`: Karşı tarafın bağlantı isteğini POST edeceği webhook URL'i
    - `seed`: (Opsiyonel) Bağlantı için kullanılacak DID'in seed'i, 32 karakter

    **Örnek Yanıt:**
    ```json
    {
      "invitation": {
        "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/connections/1.0/invitation",
        "label": "ITU Ogrenci Isleri",
        "recipientKeys": ["..."],
        "serviceEndpoint": "https://itu.example.com/didcomm/ITU"
      }
    }
    ```
    **⚠️ Not:** Dönen `invitation` objesini karşı tarafa QR kod, link veya doğrudan JSON olarak iletin.
    Karşı taraf bu daveti `connections/accept-request` ile kabul eder.
    """
    agent = active_agents.get(req.agent_alias)
    if not agent: raise HTTPException(status_code=404, detail="Agent aktif değil")
    
    try:
        encoded_seed = test_utils.encode_base64(req.seed) if req.seed else None
        conn_inv = agent.connection_create_local_invitation(req.label, req.endpoint_url, encoded_seed)
        return {"invitation": conn_inv}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/connections/accept-request", tags=["Cihaz Bağlantıları"])
def accept_connection_request(req: ConnectionAcceptReq):
    """
    Karşı taraftan gelen bağlantı isteğini (Connection Request) kabul eder ve güvenli kanal kurar.

    **Ne işe yarar?**
    Davetiyeyi alan taraf bir bağlantı isteği gönderdiğinde, daveti oluşturan taraf
    bu endpoint ile isteği kabul eder. Kabul sonrası her iki taraf da birbirinin
    DID'ini tanır ve uçtan uca şifreli mesajlaşmaya başlayabilir.

    **Akıştaki yeri:** create-invitation → karşı taraf Connection Request gönderir →
    bu endpoint ile kabul edilir → bağlantı aktif olur.

    **Örnek İstek:**
    ```json
    {
      "agent_alias": "ITU",
      "connection_request": {
        "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/connections/1.0/request",
        "label": "Ahmet Telefonu",
        "connection": {
          "DID": "...",
          "DIDDoc": { ... }
        }
      }
    }
    ```
    - `agent_alias`: Daveti oluşturmuş olan ajanın adı
    - `connection_request`: Karşı taraftan gelen ham bağlantı isteği JSON'u

    **Örnek Yanıt:**
    ```json
    {
      "status": "success",
      "connection_response": {
        "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/connections/1.0/response",
        "connection": { "DID": "...", "DIDDoc": { ... } }
      }
    }
    ```
    **⚠️ Not:** Webhook aktifse bu adım otomatik gerçekleşir — gelen istekler `/didcomm/{alias}` üzerinden otomatik kabul edilir.
    """
    agent = active_agents.get(req.agent_alias)
    if not agent: raise HTTPException(status_code=404, detail="Agent aktif değil")
    
    try:
        conn_res = agent.connection_accept_request(req.connection_request, None)
        return {"status": "success", "connection_response": conn_res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class InvitationAcceptReq(BaseModel):
    agent_alias: str
    invitation: Dict[str, Any]

class ConnReqCreateReq(BaseModel):
    agent_alias: str
    invitation: Dict[str, Any]

@app.post("/api/v1/holder/create-conn-request", tags=["Vatandaş / Öğrenci (Holder)"])
def holder_create_conn_request(req: ConnReqCreateReq):
    """
    Davetiyeden Connection Request üretir fakat karşı tarafa GÖNDERMEZ.
    Dönen `connection_request` manuel olarak /didcomm/{alias} webhook'una POST edilebilir.
    """
    agent = active_agents.get(req.agent_alias)
    if not agent: raise HTTPException(status_code=404, detail="Agent aktif değil")
    try:
        conn_req = agent.connection_create_request(req.invitation, None)
        return {"connection_request": conn_req}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ConnResAcceptReq(BaseModel):
    agent_alias: str
    connection_response: Dict[str, Any]

@app.post("/api/v1/connections/accept-response", tags=["Cihaz Bağlantıları"])
def accept_connection_response(req: ConnResAcceptReq):
    """
    Karşı taraftan (Kurum'dan) gelen Connection Response'u kabul ederek bağlantıyı tamamlar.
    Webhook üzerinden manuel bağlantı kurulumunda /api/v1/holder/create-conn-request'ten sonra çağrılır.
    """
    agent = active_agents.get(req.agent_alias)
    if not agent: raise HTTPException(status_code=404, detail="Agent aktif değil")
    try:
        agent.connection_accept_response(req.connection_response)
        return {"status": "success", "message": "Bağlantı tamamlandı."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/holder/accept-invitation", tags=["Vatandaş / Öğrenci (Holder)"])
def holder_accept_invitation(req: InvitationAcceptReq):
    """
    Mobil uygulamanın QR okuyup arka planda yapacağı işlemleri simüle eder.
    Invitation'daki endpoint URL'inden Kurum'un base URL'ini türetir ve
    /api/v1/connections/accept-request'e HTTP POST yaparak dağıtık çalışır —
    Kurum aynı sunucuda olmak zorunda değildir.
    """
    import requests as http_requests
    from urllib.parse import urlparse

    agent = active_agents.get(req.agent_alias)
    if not agent: raise HTTPException(status_code=404, detail="Agent aktif değil")

    try:
        # 1. Holder, davetiyeyi işleyip Connection Request oluşturur
        conn_req = agent.connection_create_request(req.invitation, None)

        # 2. endpoint URL'inden Kurum'un base URL'ini ve alias'ını türet
        #    Örnek: http://34.76.10.78:8080/didcomm/ITU
        #    → base_url = http://34.76.10.78:8080
        #    → issuer_alias = ITU
        endpoint = req.invitation.get("endpoint", req.invitation.get("serviceEndpoint", ""))
        if not endpoint:
            raise HTTPException(status_code=400, detail="Davetiyede endpoint URL bulunamadı.")

        parsed = urlparse(endpoint)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        issuer_alias = parsed.path.rstrip("/").split("/")[-1]

        accept_url = f"{base_url}/api/v1/connections/accept-request"
        print(f"🌐 [HOLDER] Kurum API'sine bağlanılıyor: {accept_url} (alias: {issuer_alias})")

        # 3. Kurum'un accept-request endpoint'ine Connection Request'i gönder
        webhook_resp = http_requests.post(
            accept_url,
            json={"agent_alias": issuer_alias, "connection_request": conn_req},
            timeout=15
        )

        if webhook_resp.status_code not in (200, 201):
            raise HTTPException(
                status_code=502,
                detail=f"Kurum API'si hata döndü ({webhook_resp.status_code}): {webhook_resp.text}"
            )

        resp_json = webhook_resp.json()
        conn_res = resp_json.get("connection_response", resp_json)
        print(f"✅ [HOLDER] Kurum'dan Connection Response alındı.")

        # 4. Kurum'dan gelen yanıtı Holder kabul eder — bağlantı tamamlanır
        agent.connection_accept_response(conn_res)

        return {"status": "success", "message": "Bağlantı Kurum ve Holder arasında başarıyla kuruldu!"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/connections/list", tags=["Cihaz Bağlantıları"])
def get_connections(agent_alias: str):
    """
    Bir ajanın mevcut tüm DIDComm bağlantılarını listeler.

    **Ne işe yarar?**
    Ajanın hangi cihaz/kurum/kişi ile bağlantı kurduğunu gösterir.
    Her bağlantıda kendi DID'iniz (`my_did`) ve karşı tarafın DID'i (`their_did`) yer alır.
    Mesaj şifrelemek veya kanıt talebi göndermek için `their_did` değerine ihtiyaç duyarsınız.

    **Örnek İstek:**
    ```
    GET /api/v1/connections/list?agent_alias=ITU
    ```
    - `agent_alias`: Bağlantılarını listelemek istediğiniz ajanın adı (query parametresi)

    **Örnek Yanıt:**
    ```json
    {
      "connections": [
        {
          "my_did": "V4SG...abc",
          "their_did": "FjRf...xyz",
          "label": "Ahmet Telefonu"
        }
      ]
    }
    ```
    **⚠️ Not:** Bağlantı yoksa boş liste döner. Önce `create-invitation` ve `accept-request` ile bağlantı kurun.
    """
    agent = active_agents.get(agent_alias)
    if not agent: raise HTTPException(status_code=404, detail="Agent aktif değil")
    
    try:
        conns = agent.connection_get_connections()
        return {"connections": conns}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/messages/encrypt", tags=["Cihaz Bağlantıları"])
def encrypt_message_for_connection(req: EncryptMessageReq):
    """
    Bağlantı kurulmuş bir tarafa uçtan uca şifreli mesaj (DIDComm Envelope) oluşturur.

    **Ne işe yarar?**
    İki taraf arasında kurulan DIDComm bağlantısı üzerinden gönderilecek mesajı
    kriptografik olarak şifreler. Sadece hedef DID'in sahibi bu mesajı çözebilir.
    Mesaj bir "zarf" (envelope) içine konur — transit sırasında kimse içeriğini okuyamaz.

    **Kullanım senaryoları:**
    - Kurum → Holder'a özel bildirim göndermek
    - Holder → Verifier'a kanıt belgesi göndermek
    - İki kurum arasında gizli veri paylaşımı

    **Örnek İstek:**
    ```json
    {
      "agent_alias": "ITU",
      "from_did": "V4SG...abc",
      "their_did": "FjRf...xyz",
      "message": { "text": "Diplomanız hazır" }
    }
    ```
    - `agent_alias`: Mesajı gönderen ajanın adı
    - `from_did`: Gönderenin kendi DID'i (`connections/list`'ten `my_did` alanı)
    - `their_did`: Alıcının DID'i (`connections/list`'ten `their_did` alanı)
    - `message`: Şifrelenecek mesaj içeriği (herhangi bir JSON objesi olabilir)

    **Örnek Yanıt:**
    ```json
    {
      "encrypted_message": {
        "protected": "...",
        "iv": "...",
        "ciphertext": "...",
        "tag": "..."
      }
    }
    ```
    **⚠️ Not:** Dönen `encrypted_message` zarfını karşı tarafın webhook URL'ine POST edin.
    Karşı taraf `messages/decrypt` ile açabilir.
    """
    _type_map = {
        "simple":               NixarMessageType.MESSAGE_TYPE_SIMPLE,
        "credential_offer":     NixarMessageType.MESSAGE_TYPE_CREDENTIAL_OFFER,
        "credential_request":   NixarMessageType.MESSAGE_TYPE_CREDENTIAL_REQUEST,
        "credential":           NixarMessageType.MESSAGE_TYPE_CREDENTIAL,
        "presentation_request": NixarMessageType.MESSAGE_TYPE_PRESENTATION_REQUEST,
        "presentation":         NixarMessageType.MESSAGE_TYPE_PRESENTATION,
    }
    agent = active_agents.get(req.agent_alias)
    if not agent: raise HTTPException(status_code=404, detail="Agent aktif değil")
    msg_type = _type_map.get(req.message_type, NixarMessageType.MESSAGE_TYPE_SIMPLE)
    try:
        encrypted_message = agent.connection_encrypt(
            req.from_did, req.their_did, msg_type, req.message
        )
        return {"encrypted_message": encrypted_message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/messages/decrypt", tags=["Cihaz Bağlantıları"])
def decrypt_message_from_connection(req: DecryptMessageReq):
    """
    Şifreli bir DIDComm zarfını (envelope) açarak içindeki orijinal mesajı çıkarır.

    **Ne işe yarar?**
    Karşı tarafın `messages/encrypt` ile oluşturduğu veya webhook üzerinden gelen
    şifreli mesajı kendi özel anahtarınızla çözer. Sadece mesajın hedef DID'ine
    sahip olan ajan bu zarfı açabilir.

    **Kullanım senaryosu:** Holder'ın telefonundan gelen şifreli kanıt belgesi,
    Verifier tarafından bu endpoint ile açılır ve içeriği okunur.

    **Örnek İstek:**
    ```json
    {
      "agent_alias": "Ziraat",
      "encrypted_message": {
        "protected": "...",
        "iv": "...",
        "ciphertext": "...",
        "tag": "..."
      }
    }
    ```
    - `agent_alias`: Mesajı çözecek ajanın adı (zarfın hedef DID'ine sahip olan)
    - `encrypted_message`: `messages/encrypt`'ten veya webhook'tan gelen şifreli zarf objesi

    **Örnek Yanıt:**
    ```json
    {
      "decrypted_message": {
        "content": "{ \"text\": \"Diplomanız hazır\" }",
        "sender_did": "V4SG...abc",
        "message_type": "simple"
      }
    }
    ```
    **⚠️ Not:** Eğer zarf bu ajana ait değilse veya bozulmuşsa hata döner.
    Webhook aktifse gelen mesajlar otomatik olarak `/didcomm/{alias}` üzerinden çözülür.
    """
    agent = active_agents.get(req.agent_alias)
    if not agent: raise HTTPException(status_code=404, detail="Agent aktif değil")
    try:
        decrypted_message = agent.connection_decrypt(req.encrypted_message)
        return {"decrypted_message": decrypted_message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/messages/sign", tags=["Cihaz Bağlantıları"])
def sign_data_with_did(req: SignDataReq):
    """
    Ajanın DID'i ile veriyi imzalar (dijital imza oluşturur).

    **Ne işe yarar?**
    Holder veya Issuer kendi DID'i ile herhangi bir veriyi imzalayabilir.
    Oluşturulan imza karşı tarafa gönderilebilir, karşı taraf da `messages/verify-signature`
    ile imzayı doğrulayabilir.

    **Kullanım senaryosu:**
    Holder, kimliğini kanıtlamak için belirli bir veriyi kendi DID'i ile imzalar.
    Bu imza banka (Verifier) tarafından doğrulanarak holder'ın gerçekten söz konusu DID'in
    sahibi olduğu teyit edilir.

    **Örnek İstek:**
    ```json
    {
      "agent_alias": "MobilCuzdan",
      "from_did": "V4SG...abc",
      "data": "SW1zYWxhbmFjYWsgdmVyaQ=="
    }
    ```
    - `data`: Base64 kodlanmış imzalanacak veri (`base64.b64encode(b"veri").decode()`)

    **Örnek Yanıt:**
    ```json
    {
      "signature": "abc123...base64imza...",
      "signed_data": "SW1zYWxhbmFjYWsgdmVyaQ=="
    }
    ```
    """
    agent = active_agents.get(req.agent_alias)
    if not agent: raise HTTPException(status_code=404, detail="Agent aktif değil")
    try:
        signature = agent.sign_with_did(req.from_did, req.data)
        return {"signature": signature, "signed_data": req.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/messages/verify-signature", tags=["Cihaz Bağlantıları"])
def verify_signature_with_did(req: VerifySignatureReq):
    """
    Bağlantı kurulmuş bir tarafın DID imzasını doğrular.

    **Ne işe yarar?**
    Karşı tarafın (`their_did`) daha önce `messages/sign` ile oluşturduğu imzayı doğrular.
    İmzanın o DID'e ait özel anahtarla gerçekten oluşturulup oluşturulmadığını kontrol eder.

    **Ön koşul:** İmzayı doğrulayacak ajan ile imzalayanın önceden DIDComm bağlantısı kurmuş olması gerekir.
    Bağlantı sayesinde `their_did`'in public key bilgisi yerel cüzdanda mevcuttur.

    **Dağıtık senaryo:**
    1. Holder (Mac:8000) → `messages/sign` → imza oluşturur
    2. Holder → imzayı şifreli olarak `messages/encrypt` ile zarflar ve Kurum'a gönderir
    3. Kurum (GCloud:8080) → `messages/decrypt` → zarfı açar
    4. Kurum → `messages/verify-signature` → imzayı doğrular ✅

    **Örnek İstek:**
    ```json
    {
      "agent_alias": "ITU",
      "their_did": "FjRf...xyz",
      "signed_data": "SW1zYWxhbmFjYWsgdmVyaQ==",
      "signature": "abc123...base64imza..."
    }
    ```

    **Örnek Yanıt:**
    ```json
    {
      "is_verified": true,
      "their_did": "FjRf...xyz"
    }
    ```
    """
    agent = active_agents.get(req.agent_alias)
    if not agent: raise HTTPException(status_code=404, detail="Agent aktif değil")
    try:
        is_verified = agent.verify_signature_with_their_did(req.their_did, req.signed_data, req.signature)
        return {"is_verified": is_verified, "their_did": req.their_did}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# WEBHOOK (TELEFONDAN GELEN RAW İSTEKLER İÇİN DİNLEYİCİ)
# ==============================================================================
from fastapi import Request

@app.post("/api/v1/issuer/prepare-offer", tags=["Verici / Üniversite (Issuer)"])
def prepare_credential_offer(req: CredentialOfferCreateReq):
    """
    Issuer, Credential Offer oluşturur ve webhook tarafından otomatik işlenebilmesi için
    credential değerlerini sunucuda saklar.

    Holder'dan `/didcomm/ITU` webhook'una `MessageTypeCredentialRequest` geldiğinde,
    sunucu burada kaydedilen `cred_values` ve `issuer_nonce` ile credentials otomatik imzalar.

    **Örnek İstek:**
    ```json
    {
      "agent_alias": "ITU",
      "cred_def_id": "4fUYw6T3...:3:CL:20:diploma",
      "cred_values": {
        "ad":              { "raw": "Ahmet",   "encoded": "1" },
        "soyad":           { "raw": "Yılmaz",  "encoded": "2" },
        "mezuniyet_yili":  { "raw": "2024",    "encoded": "2024" },
        "gpa":             { "raw": "3.5",     "encoded": "35" }
      }
    }
    ```

    **Örnek Yanıt:**
    ```json
    {
      "offer": { ... },
      "issuer_nonce": "748392019283746152"
    }
    ```
    Dönen `offer`'ı QR koda basın veya Holder'a iletin.
    """
    import random
    agent = active_agents.get(req.agent_alias)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent aktif değil")

    nonce = str(random.getrandbits(80))
    offer = agent.issuer_create_credential_offer(req.cred_def_id, nonce)

    # Webhook için sakla
    pending_credential_offers[nonce] = {
        "agent_alias": req.agent_alias,
        "cred_def_id": req.cred_def_id,
        "issuer_nonce": nonce,
        "cred_values": req.cred_values,
    }

    return {"offer": offer, "issuer_nonce": nonce}


@app.post("/api/v1/verifier/prepare-presentation-request", tags=["Doğrulayıcı / Banka (Verifier)"])
def prepare_presentation_request(req: PresentationRequestCreateReq):
    """
    Verifier (banka/kurum), Presentation Request oluşturur ve webhook tarafından otomatik
    doğrulanabilmesi için sunucuda saklar.

    Holder'dan `/didcomm/{alias}` webhook'una `MessageTypePresentation` geldiğinde,
    sunucu burada kaydedilen presentation_request ile otomatik `verifier_verify_presentation()` çağırır.

    **Örnek İstek:**
    ```json
    {
      "agent_alias": "Ziraat",
      "presentation_request": {
        "name": "Banka_Kimlik_Dogrulama",
        "version": "1.0",
        "nonce": "1234567890",
        "requestedAttributes": {
          "attr_departman": { "name": "departman", "restrictions": [{ "cred_def_id": "..." }] }
        },
        "requestedPredicates": {
          "pred_gpa": { "name": "gpa", "p_type": ">=", "p_value": 30, "restrictions": [{ "cred_def_id": "..." }] }
        }
      }
    }
    ```

    **Örnek Yanıt:**
    ```json
    {
      "status": "ready",
      "nonce": "1234567890"
    }
    ```
    `presentation_request`'i QR koda basın veya Holder'a iletin.
    """
    agent = active_agents.get(req.agent_alias)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent aktif değil")

    nonce = req.presentation_request.get("nonce")
    if not nonce:
        raise HTTPException(status_code=400, detail="presentation_request içinde 'nonce' alanı zorunludur.")

    pending_presentation_requests[nonce] = {
        "agent_alias": req.agent_alias,
        "presentation_request": req.presentation_request,
    }

    return {"status": "ready", "nonce": nonce, "presentation_request": req.presentation_request}


@app.post("/api/v1/issuer/issue-for-request", tags=["Verici / Üniversite (Issuer)"])
def issue_for_request(req: IssueForRequestReq):
    """
    Holder'dan gelen credential request'e karşılık credential imzalar ve döner.
    pending_credential_offers'dan cred_def_id ile eşleşen kaydı bulur.
    Transport şifreleme gerektirmez — credential'ın kendi imzası güvenliği sağlar.
    """
    agent = active_agents.get(req.agent_alias)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent aktif değil")

    matched = next(
        (v for v in pending_credential_offers.values()
         if v["agent_alias"] == req.agent_alias and v["cred_def_id"] == req.cred_def_id),
        None
    )
    if not matched:
        raise HTTPException(status_code=404, detail="Bu cred_def_id için pending offer bulunamadı. Önce /api/v1/issuer/prepare-offer çağırın.")

    try:
        cred_info = agent.issuer_create_credential(req.cred_request, matched["cred_values"], matched["issuer_nonce"])
        del pending_credential_offers[matched["issuer_nonce"]]
        return {"status": "issued", "credential": cred_info["credential"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/verifier/submit-presentation", tags=["Doğrulayıcı / Banka (Verifier)"])
def submit_presentation(req: SubmitPresentationReq):
    """
    Holder'dan gelen presentation'ı doğrular.
    pending_presentation_requests'ten agent_alias ile eşleşen en güncel talebi kullanır.
    Transport şifreleme gerektirmez — ZKP kriptografisi güvenliği sağlar.
    """
    agent = active_agents.get(req.agent_alias)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent aktif değil")

    matched_key = next(
        (k for k, v in pending_presentation_requests.items() if v["agent_alias"] == req.agent_alias),
        None
    )
    if not matched_key:
        raise HTTPException(status_code=404, detail="Bekleyen presentation request bulunamadı. Önce /api/v1/verifier/prepare-presentation-request çağırın.")

    pres_request = pending_presentation_requests[matched_key]["presentation_request"]
    try:
        is_valid = agent.verifier_verify_presentation(pres_request, req.presentation)
        revealed = {}
        if is_valid:
            raw = req.presentation.get("requested_proof", {}).get("revealed_attrs", {})
            revealed = {k: v.get("raw") for k, v in raw.items()}
        del pending_presentation_requests[matched_key]
        return {"status": "verified", "is_valid": is_valid, "revealed_data": revealed}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/didcomm/{agent_alias}", tags=["Webhook Dinleyicisi"])
async def didcomm_webhook(agent_alias: str, req: Request):
    """
    Dış dünyadan (telefon, başka sunucu vb.) gelen DIDComm mesajlarını dinleyen webhook endpoint'i.

    **Ne işe yarar?**
    Bu endpoint, ajanınızın "posta kutusu" gibi çalışır. Karşı taraf (örn: öğrencinin telefonu)
    bağlantı isteği, şifreli mesaj veya kanıt belgesi gönderdiğinde bu adrese POST yapar.
    Sunucu gelen mesajın türünü otomatik olarak tespit eder ve uygun işlemi yapar:

    1. **Bağlantı İsteği** (`connections/1.0/request`): Otomatik kabul eder ve bağlantıyı kurar.
    2. **Onay Mesajı** (`ack`): Bağlantının başarıyla kurulduğunu teyit eder.
    3. **Şifreli Mesaj** (diğer tüm türler): Zarfı açar, içeriği çözer ve döner.
       - Kanıt belgesi (Presentation) gelirse loglar ve içeriği döner.
       - Bilinmeyen mesaj türü ise `ignored` olarak işaretler.

    **Kullanım senaryosu:**
    `create-invitation` ile verdiğiniz `endpoint_url` bu adresi göstermelidir.
    Örneğin `endpoint_url: "https://sunucu.com/didcomm/ITU"` olarak ayarlarsanız,
    karşı tarafın tüm mesajları bu endpoint'e düşer.

    **Örnek URL:**
    ```
    POST /didcomm/ITU
    ```
    - `agent_alias`: Mesajı alacak ajanın adı (URL'deki path parametresi)

    **Body:** Karşı tarafın gönderdiği ham JSON — bağlantı isteği veya şifreli zarf olabilir.

    **Olası Yanıtlar:**
    - Bağlantı isteği gelirse → `connection_response` döner
    - Onay gelirse → `{"status": "ok"}`
    - Şifreli mesaj gelirse → `{"status": "message_decrypted", "content": { ... }}`
    - Desteklenmeyen mesaj → `{"status": "ignored", "reason": "unsupported_message"}`

    **⚠️ Not:** Bu endpoint genellikle doğrudan çağrılmaz — karşı tarafın uygulaması otomatik olarak buraya POST yapar.
    Test amaçlı manuel olarak da kullanılabilir.
    """
    agent = active_agents.get(agent_alias)
    if not agent: raise HTTPException(status_code=404, detail="Agent bulunamadı.")

    try:
        body_data = await req.json()
        message_type = body_data.get("@type", "")

        # ── Şifrelenmemiş Bağlantı İstekleri ─────────────────────────────────
        if "connections/1.0/request" in message_type:
            print("🚀 [WEBHOOK] Connection Request alındı (@type ile)")
            conn_res = agent.connection_accept_request(body_data, None)
            return conn_res

        elif "connections/1.0/ack" in message_type or "ack" in message_type:
            return {"status": "ok"}

        elif not message_type:
            # @type yok → önce nixar conn_req dene (nixar conn_req @type içermez, şifreli)
            try:
                print("🚀 [WEBHOOK] @type yok → Connection Request olarak deneniyor...")
                conn_res = agent.connection_accept_request(body_data, None)
                print("✅ [WEBHOOK] Connection Request kabul edildi.")
                return {"status": "success", "connection_response": conn_res}
            except Exception:
                pass  # conn_req değil, şifreli uygulama mesajı olabilir — aşağıda decrypt edilecek

        # ── Şifreli Mesajlar: Decrypt Et, Tipe Göre İşle ─────────────────────
        try:
            decrypted = agent.connection_decrypt(body_data)
        except Exception as dec_err:
            return {"status": "ignored", "reason": "decrypt_failed", "detail": str(dec_err)}

        msg_type: str = decrypted.get("messageType", "")
        sender_did: str = decrypted.get("senderDid", "")
        content_raw = decrypted.get("content", "{}")
        try:
            content = json.loads(content_raw) if isinstance(content_raw, str) else content_raw
        except Exception:
            content = {}

        print(f"📨 [WEBHOOK] Şifreli mesaj açıldı | tip={msg_type} | gönderen={sender_did}")

        # ── MessageTypeCredentialRequest ──────────────────────────────────────
        # Holder, Issuer'ın teklifine karşılık credential talep etti.
        # Pending offer'dan nonce+cred_values'ı bul → credential imzala → geri gönder.
        if msg_type == "MessageTypeCredentialRequest":
            print("📋 [WEBHOOK] Credential Request alındı → credential imzalanıyor...")
            cred_def_id_in_req = content.get("cred_def_id", "")

            # pending_credential_offers içinde bu cred_def_id için hazırlanmış bir offer bul
            matched = next(
                (v for v in pending_credential_offers.values()
                 if v["agent_alias"] == agent_alias and v["cred_def_id"] == cred_def_id_in_req),
                None
            )
            if not matched:
                return {"status": "error", "reason": "Bu cred_def_id için hazırlanmış pending offer yok. Önce /api/v1/issuer/prepare-offer çağırın."}

            cred_info = agent.issuer_create_credential(
                content, matched["cred_values"], matched["issuer_nonce"]
            )
            credential = cred_info["credential"]

            # Holder'a şifreli olarak credential gönder
            conn_info = agent.get_connection_by_their_did(sender_did)
            my_did = conn_info.get("myDid") or conn_info.get("my_did", "")
            encrypted_cred = agent.connection_encrypt(
                my_did, sender_did,
                NixarMessageType.MESSAGE_TYPE_CREDENTIAL,
                credential
            )
            del pending_credential_offers[matched["issuer_nonce"]]
            print("✅ [WEBHOOK] Credential imzalandı ve Holder'a gönderildi.")
            return {"status": "credential_issued", "encrypted_credential": encrypted_cred}

        # ── MessageTypeCredential ─────────────────────────────────────────────
        # Issuer, Holder'a imzalı credential gönderdi.
        # Holder otomatik olarak cüzdana kaydeder.
        elif msg_type == "MessageTypeCredential":
            print("🎓 [WEBHOOK] Credential alındı → cüzdana kaydediliyor...")
            agent.prover_store_credential(None, content)
            print("✅ [WEBHOOK] Credential cüzdana kaydedildi.")
            return {"status": "credential_stored"}

        # ── MessageTypeCredentialOffer ────────────────────────────────────────
        # Issuer, Holder'a credential teklif etti (Issuer-Initiated akış).
        # Holder otomatik credential request oluşturur ve şifreli geri gönderir.
        elif msg_type == "MessageTypeCredentialOffer":
            print("📬 [WEBHOOK] Credential Offer alındı → credential request oluşturuluyor...")
            cred_req = agent.prover_create_credential_request(content)
            conn_info = agent.get_connection_by_their_did(sender_did)
            my_did = conn_info.get("myDid") or conn_info.get("my_did", "")
            encrypted_req = agent.connection_encrypt(
                my_did, sender_did,
                NixarMessageType.MESSAGE_TYPE_CREDENTIAL_REQUEST,
                cred_req
            )
            print("✅ [WEBHOOK] Credential Request Issuer'a gönderildi.")
            return {"status": "credential_request_sent", "encrypted_credential_request": encrypted_req}

        # ── MessageTypePresentationRequest ────────────────────────────────────
        # Verifier, Holder'dan kanıt belgesi istedi.
        # Holder cüzdanından ilgili credential'ı bulur, presentation oluşturur ve gönderir.
        elif msg_type == "MessageTypePresentationRequest":
            print("🏦 [WEBHOOK] Presentation Request alındı → kanıt hazırlanıyor...")
            try:
                agent.prover_fetch_credential_for_presentation_request(content)
            except Exception:
                pass  # bazı nixar versiyonlarında bu adım opsiyonel
            presentation = agent.prover_create_presentation(content, {})
            conn_info = agent.get_connection_by_their_did(sender_did)
            my_did = conn_info.get("myDid") or conn_info.get("my_did", "")
            encrypted_pres = agent.connection_encrypt(
                my_did, sender_did,
                NixarMessageType.MESSAGE_TYPE_PRESENTATION,
                presentation
            )
            print("✅ [WEBHOOK] Presentation Verifier'a gönderildi.")
            return {"status": "presentation_sent", "encrypted_presentation": encrypted_pres}

        # ── MessageTypePresentation ───────────────────────────────────────────
        # Holder, kanıt belgesini (Presentation) gönderdi.
        # Verifier pending_presentation_requests'ten eşleşen talebi bulur ve doğrular.
        elif msg_type == "MessageTypePresentation":
            print("📄 [WEBHOOK] Presentation alındı → doğrulanıyor...")
            pres_nonce = content.get("requested_proof", {}).get("identifiers", [{}])[0].get("timestamp", "")
            # nonce'u presentation'dan da almayı dene
            pres_req_nonce = None
            for k, v in pending_presentation_requests.items():
                if v["agent_alias"] == agent_alias:
                    pres_req_nonce = k
                    break  # en son hazırlanan talebi kullan

            if not pres_req_nonce:
                return {"status": "error", "reason": "Bekleyen presentation request bulunamadı. Önce /api/v1/verifier/prepare-presentation-request çağırın."}

            pres_request_data = pending_presentation_requests[pres_req_nonce]["presentation_request"]
            is_valid = agent.verifier_verify_presentation(pres_request_data, content)

            revealed = {}
            if is_valid:
                raw_revealed = content.get("requested_proof", {}).get("revealed_attrs", {})
                revealed = {k: v.get("raw") for k, v in raw_revealed.items()}

            del pending_presentation_requests[pres_req_nonce]
            print(f"{'✅' if is_valid else '❌'} [WEBHOOK] Presentation doğrulama: {is_valid}")
            return {"status": "presentation_verified", "is_valid": is_valid, "revealed_data": revealed}

        # ── MessageTypeSimple ─────────────────────────────────────────────────
        elif msg_type == "MessageTypeSimple":
            return {"status": "message_received", "content": content, "sender_did": sender_did}

        # ── Bilinmeyen ────────────────────────────────────────────────────────
        else:
            print(f"⚠️  [WEBHOOK] Bilinmeyen messageType: {msg_type}")
            return {"status": "ignored", "reason": f"unsupported_message_type: {msg_type}", "content": decrypted}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "detail": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

