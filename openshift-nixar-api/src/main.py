from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import json

from nixar.nixar_api import Nixar
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
# PYDANTIC MODELLERİ (VERİ TRANSFER OBJELERİ - DTO)
# ==============================================================================

class AgentInitReq(BaseModel):
    alias: str
    password: str
    role: Optional[str] = None
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

@app.post("/api/v1/agents/init", tags=["Ajan Yönetimi"])
def init_agent(req: AgentInitReq):
    """Belirtilen cüzdan verileri ile bir Nixar Ajanı oluşturur veya hafızaya yükler."""
    try:
        if req.alias in active_agents:
            return {"status": "success", "message": "Agent zaten aktif."}
        
        # Tohumu Base64'e çevir (Eğer verilmişse)
        encoded_seed = test_utils.encode_base64(req.seed) if req.seed else None
        
        # Ajanı yarat veya yükle
        password_cb = lambda: test_utils.native_string(req.password)
        agent = create_nixar_agent_w_json_wallet(req.alias, password_cb, req.role, base64_seed=encoded_seed)
        
        active_agents[req.alias] = agent
        return {"status": "success", "did": agent.get_public_did_doc().split('"did":')[1].split('"')[1]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/agents/{alias}/did", tags=["Ajan Yönetimi"])
def get_agent_did(alias: str):
    if alias not in active_agents:
        raise HTTPException(status_code=404, detail="Agent bulunamadı (Önce Init yapın)")
    return json.loads(active_agents[alias].get_public_did_doc())

# ==============================================================================
# 2. SCHEMA (ŞABLON) VE CRED-DEF YÖNETİMİ
# ==============================================================================

@app.post("/api/v1/schema/create", tags=["Şablon İşlemleri"])
def create_schema(req: SchemaCreateReq):
    if req.agent_alias not in active_agents:
        raise HTTPException(status_code=404, detail="Agent aktif değil")
    agent = active_agents[req.agent_alias]
    try:
        schema_id = agent.issuer_create_schema(req.schema_name, req.attributes, req.version)
        return {"status": "success", "schema_id": schema_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/credential-definition/create", tags=["Şablon İşlemleri"])
def create_cred_def(req: CredDefCreateReq):
    if req.agent_alias not in active_agents:
        raise HTTPException(status_code=404, detail="Agent aktif değil")
    agent = active_agents[req.agent_alias]
    try:
        tag = get_timestamp_tag()
        cred_def_id = agent.issuer_create_credential_definition(req.schema_id, req.is_revokable, tag, 0, 1000)
        return {"status": "success", "cred_def_id": cred_def_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# 3. İHRAÇ (ISSUANCE) AKIŞI
# ==============================================================================

@app.post("/api/v1/issuer/create-offer", tags=["Veri İhracı"])
def create_offer(req: CredentialOfferReq):
    agent = active_agents.get(req.agent_alias)
    if not agent: raise HTTPException(status_code=404, detail="Agent aktif değil")
    
    import random
    nonce = str(random.getrandbits(80))
    offer = agent.issuer_create_credential_offer(req.cred_def_id, nonce)
    return {"offer": offer, "issuer_nonce": nonce}

@app.post("/api/v1/prover/create-request", tags=["Veri İhracı"])
def create_request(agent_alias: str, offer: Dict[str, Any] = Body(...)):
    agent = active_agents.get(agent_alias)
    if not agent: raise HTTPException(status_code=404, detail="Agent aktif değil")
    
    cred_req = agent.prover_create_credential_request(offer)
    return {"credential_request": cred_req}

@app.post("/api/v1/issuer/issue-credential", tags=["Veri İhracı"])
def issue_credential(req: CredentialIssueReq):
    agent = active_agents.get(req.agent_alias)
    if not agent: raise HTTPException(status_code=404, detail="Agent aktif değil")
    
    try:
        cred_info = agent.issuer_create_credential(req.cred_request, req.credential_values, req.issuer_nonce)
        return {"credential": cred_info["credential"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/prover/store-credential", tags=["Veri İhracı"])
def store_credential(agent_alias: str, credential: Dict[str, Any] = Body(...)):
    agent = active_agents.get(agent_alias)
    if not agent: raise HTTPException(status_code=404, detail="Agent aktif değil")
    
    agent.prover_store_credential(None, credential)
    return {"status": "success", "message": "Evrak Cüzdana Saklandı!"}

# ==============================================================================
# 4. DOĞRULAMA (VERIFICATION) - SIFIR BİLGİ İSPATI (ZKP)
# ==============================================================================

@app.post("/api/v1/prover/create-presentation", tags=["ZKP Doğrulama"])
def create_presentation(req: PresentationCreateReq):
    agent = active_agents.get(req.agent_alias)
    if not agent: raise HTTPException(status_code=404, detail="Agent aktif değil")
    
    try:
        vp = agent.prover_create_presentation(req.presentation_request, {})
        return {"presentation": vp}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/verifier/verify-presentation", tags=["ZKP Doğrulama"])
def verify_presentation(req: VerifyPresentationReq):
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
