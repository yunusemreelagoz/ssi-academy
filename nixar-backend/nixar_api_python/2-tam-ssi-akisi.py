import json
import logging
import random

from nixar.nixar_api import CredDefIssuanceType
import test_utils
from test_utils import (
    create_nixar_agent_w_json_wallet,
    create_schema_if_not_exist,
    create_credential_definition,
    get_timestamp_tag
)

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    print("════════════════════════════════════════════════════════")
    print(" 2. ADIM: NIXAR KÜTÜPHANESİ İLE GERÇEK SSI UYGULAMASI")
    print("════════════════════════════════════════════════════════\n")

    # ---------------------------------------------------------
    # 1. AKTÖRLERİ OLUŞTURMA
    # ---------------------------------------------------------
    logger.info("1/5 Aktörler (Ajanlar) başlatılıyor...")
    
    itu_sifre = test_utils.native_string("ItuSecure123!")
    ahmet_sifre = test_utils.native_string("AhmetCuzdan123!")
    ziraat_sifre = test_utils.native_string("ZiraatBanka123!")

    itu_ajani = create_nixar_agent_w_json_wallet("itu_uni_demo", lambda: itu_sifre, "ENDORSER")
    ahmet_cuzdan = create_nixar_agent_w_json_wallet("ahmet_ogrenci", lambda: ahmet_sifre, None)
    ziraat_bankasi = create_nixar_agent_w_json_wallet("ziraat_bank", lambda: ziraat_sifre, None)

    # ---------------------------------------------------------
    # 2. ŞABLON (SCHEMA) BELİRLEME
    # ---------------------------------------------------------
    logger.info("2/5 İTÜ 'Diploma' şablonunu blokzincire yazıyor...")
    schema_name = "ITU_Diploma_v3"
    attributes = ["ad", "soyad", "departman", "mezuniyet_yili", "gpa"]
    
    schema_id = create_schema_if_not_exist(itu_ajani, schema_name, attributes)
    cred_def_id = create_credential_definition(itu_ajani, schema_id, False, get_timestamp_tag())

    # ---------------------------------------------------------
    # 3. DİPLOMA (VC) İHRACI (ISSUANCE)
    # ---------------------------------------------------------
    print("\n--------------------------------------------------------")
    logger.info("3/5 İTÜ, Ahmet'e Diploma (VC) veriyor...")

    # a) İTÜ bir VC teklifi (Offer) oluşturur
    issuer_nonce = str(random.getrandbits(80))
    cred_offer = itu_ajani.issuer_create_credential_offer(cred_def_id, issuer_nonce)
    
    # b) Ahmet teklife karşılık bir talep (Request) oluşturur
    cred_request = ahmet_cuzdan.prover_create_credential_request(cred_offer)
    
    # c) İTÜ, talebin içine notları (Credential Values) basar
    diploma_bilgileri = {
        "ad": {"raw": "Ahmet", "encoded": "1"},
        "soyad": {"raw": "Yılmaz", "encoded": "2"},
        "departman": {"raw": "Bilgisayar Muhendisligi", "encoded": "3"},
        "mezuniyet_yili": {"raw": "2024", "encoded": "2024"},
        "gpa": {"raw": "3.5", "encoded": "35"} # encode işlemi genelde integer yapılır
    }
    
    cred_info = itu_ajani.issuer_create_credential(cred_request, diploma_bilgileri, issuer_nonce)
    verifiable_credential = cred_info["credential"] # Gerçek İmzalı VC belgesi
    
    # d) Ahmet imzalı belgeyi cüzdanında saklar
    ahmet_cuzdan.prover_store_credential(None, verifiable_credential)
    logger.info("✅ Diploma başarıyla Ahmet'in cüzdanına eklendi!")

    # ---------------------------------------------------------
    # 4. SIFIR BİLGİ İSPATI (ZKP) VE VP OLUŞTURMA (PRESENTATION)
    # ---------------------------------------------------------
    print("\n--------------------------------------------------------")
    logger.info("4/5 Ahmet, Ziraat Bankasına Başvuruyor (ZKP/SD Hazırlığı)...")
    
    # Banka bir "Presentation Request" yollar. ("Sadece departman ve gpa'yı göster!")
    bankanin_taleb = {
        "name": "IseGiris_Belge_Istegi",
        "version": "1.0",
        "nonce": "1234567890",
        "requestedAttributes": {
            "req_attr_1": { "name": "departman", "restrictions": [ {"cred_def_id": cred_def_id} ] },
            "req_attr_2": { "name": "mezuniyet_yili", "restrictions": [ {"cred_def_id": cred_def_id} ] }
        },
        "requestedPredicates": {
             # "Adımı göstermiyorum, gpa değerimi göstermiyorum!"
             # SEYRET: BANKA SADECE "gpa > 3.0 (30)" OLDUĞUNU İSPATLAMASINI İSTİYOR!
             "req_pred_1": { "name": "gpa", "p_type": ">=", "p_value": 30, "restrictions": [ {"cred_def_id": cred_def_id} ] }
        }
    }
    
    # Ahmet gelen talebe göre Cüzdanındaki belgeyi paketler(VP) ve ZKP imzası atar
    verifiable_presentation = ahmet_cuzdan.prover_create_presentation(bankanin_taleb, {})
    logger.info("✅ Ahmet, ZKP destekli VP belgesini Banka'ya gönderdi.")

    # ---------------------------------------------------------
    # 5. BANKANIN DOĞRULAMASI (VERIFICATION)
    # ---------------------------------------------------------
    print("\n--------------------------------------------------------")
    logger.info("5/5 Ziraat Bankası gelen belgeleri ZKP kriptografisi ile doğruluyor...")
    
    dogrulama_sonucu = ziraat_bankasi.verifier_verify_presentation(bankanin_taleb, verifiable_presentation)
    
    if dogrulama_sonucu:
        # Banka'nın eline ne ulaştığını yazdıralım
        paylasilan_veriler = verifiable_presentation["requested_proof"]["revealed_attrs"]
        
        print("\n🎉 DOĞRULAMA BAŞARILI!")
        print(" Ziraat Bankası Gözünden Görünenler:")
        print(f"   Departman: {paylasilan_veriler['req_attr_1']['raw']}")
        print(f"   Mezuniyet Yılı: {paylasilan_veriler['req_attr_2']['raw']}")
        print(f"   GPA Değeri: GİZLİ (Fakat matematiksel olarak >= 3.0 kanıtlandı!) 🔐")
        print("\n Banka Ahmet'i İşe Aldı!")
    else:
        logger.error("❌ DOĞRULAMA BAŞARISIZ!")

if __name__ == '__main__':
    main()
