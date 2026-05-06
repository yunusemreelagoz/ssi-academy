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
    Belirtilen cüzdan verileri ile bir Kurumsal Nixar Ajanı oluşturur veya hafızaya yükler.
    
    KİMLER KULLANMALI?
    - Kimlik Vericiler (Issuer): Örn; Üniversite (Diploma verir), Nüfus Müd. (Kimlik verir)
    - Doğrulayıcılar (Verifier): Örn; Banka (Kredi için kimlik/maaş sorar), Noter.
    
    NOT: Bu endpoint ile kurulan cüzdanlar zorunlu olarak Ledger'a (blokzinciri ağına) kaydedilir.
    Vatandaş/Öğrenci (Holder) işlemleri için KESİNLİKLE KULLANILMAMALI! 
    Vatandaşlar için /api/v1/holder/init uç noktası kullanılmalıdır.
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
    if alias not in active_agents:
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
    Yeni bir Veri Şablonu (Schema) oluşturur ve ağa (Ledger) yazar.
    Örn: Üniversite'nin vereceği diploma için 'Öğrenci No', 'Bölüm', 'Not Ortalaması' gibi alanları tanımlar.
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
    Oluşturulan Schema'yı baz alarak bir Kimlik Tanımı (Credential Definition) yaratır.
    Kriptografik anahtarların oluştuğu evredir. Kurum bu adımı atmadan kimlik/evrak ihraç edemez.
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
    Verici Kurum (Issuer), öğrenciye/vatandaşa göndermek üzere bir 'Kimlik Verisi Teklifi' hazırlar.
    Bu teklif, vatandaşın mobil uygulamasına gönderilir.
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
    Vatandaş kendisine gelen belge teklifini (offer) alır ve 
    'Evet, bu belgeyi almaya hazırım ve kriptografik isteğim budur' (Credential Request) diyerek cevap üretir.
    """
    agent = active_agents.get(agent_alias)
    if not agent: raise HTTPException(status_code=404, detail="Agent aktif değil")
    
    cred_req = agent.prover_create_credential_request(offer)
    return {"credential_request": cred_req}

@app.post("/api/v1/issuer/issue-credential", tags=["Verici / Üniversite (Issuer)"])
def issue_credential(req: CredentialIssueReq):
    """
    Vatandaştan gelen isteği alan Kurum, içine gerçek verileri (Not: 3.5, İsim: Ahmet) 
    doldurarak kriptografik olarak imzalar ve belgeyi (Credential) ihraç eder.
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
    Vatandaş, kurumun imzalayıp gönderdiği belgeyi (Credential) alır ve kendi lokal 
    cüzdanına (Wallet) güvenli bir biçimde kaydeder.
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
    Vatandaş, banka/noter gibi yerlerin istediği verilere göre (Presentation Request), 
    cüzdanındaki orijinal belgeyi bozmadan bir Sıfır Bilgi İspatı (ZKP) Kanıtı (Presentation) hazırlar.
    Örn: Doğum tarihini vermeden yaşı 18'den büyüktür kanıtı.
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
    Doğrulayıcı Kurum (Verifier), vatandaştan gelen kanıtı (Presentation) alır. 
    İçindeki kriptografik imzaları Ledger üzerinden kontrol ederek verinin tahrif edilip edilmediğini doğrular.
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
    Sıradan bir vatandaş (Holder) için ağa (ledger) yazılmayacak yerel bir DID/cüzdan oluşturur.
    Mahremiyet (Privacy) felsefesine uygun olarak bu DID herkese açık olmaz.
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
