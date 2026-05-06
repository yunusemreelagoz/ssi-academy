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

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
