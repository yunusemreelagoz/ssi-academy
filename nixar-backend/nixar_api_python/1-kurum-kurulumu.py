import json
import logging
import cffi

from nixar.nixar_api import Nixar
import test_utils
from test_utils import create_nixar_agent_w_json_wallet, create_schema_if_not_exist, create_credential_definition, get_timestamp_tag

# Konsol loglarını daha rahat görebilmemiz için log seviyesini ayarlıyoruz
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    print("════════════════════════════════════════════════════════")
    print(" 1. ADIM: İTÜ (Issuer - Kurum) Kurulumu ve Şablon Yayını")
    print("════════════════════════════════════════════════════════\n")

    # 1. Nixar Ajanı (Agent) Oluşturma
    # İTÜ için güvenli bir cüzdan şifresi belirliyoruz
    itu_sifre = test_utils.native_string("ItuSecure123!")
    
    logger.info("İTÜ Ajanı (Agent) cüzdanı oluşturuluyor ve Indy Ledger (Blockchain)'e bağlanılıyor...")
    
    # "ENDORSER" rolü: Blockchain'e veri yazabilme yetkisine sahip kurum demek.
    # Nixar otomatik olarak cüzdanı kurup, public DID'sini blokzincirine yazar.
    itu_ajani = create_nixar_agent_w_json_wallet("itu_uni", lambda: itu_sifre, "ENDORSER")
    
    logger.info(f"✅ İTÜ Ajanı Başarıyla Kuruldu!")
    
    # 2. Schema (Diploma Şablonu) Oluşturma
    print("\n--------------------------------------------------------")
    logger.info("Blockchain üzerinde 'ITU_Diploma' şablonu oluşturuluyor...")
    
    schema_name = "ITU_Bilgisayar_Muhendisligi_Diplomasi"
    attributes = ["ad", "soyad", "departman", "mezuniyet_yili", "gpa"]
    
    schema_id = create_schema_if_not_exist(itu_ajani, schema_name, attributes)
    logger.info(f"✅ Schema Yayınlandı! ID: {schema_id}")

    # 3. Credential Definition (Sertifika Tanımı) Oluşturma
    # Bu tanım, kurumun bu şemayı kendi imzasıyla (DID) basacağını ilan eder.
    print("\n--------------------------------------------------------")
    logger.info("Credential Definition (Sertifika Tanımı) blockchain'e yazılıyor...")
    
    tag = get_timestamp_tag() # Benzersiz numara
    is_revokable = True # Diplomanın ileride iptal edilebilir (revoke) olmasını istiyoruz
    
    # Gerçek ZKP matematiğini üreten şifrelemeler burada devreye girer
    cred_def_id = create_credential_definition(itu_ajani, schema_id, is_revokable, tag)
    logger.info(f"✅ Credential Definition Yayınlandı! ID: {cred_def_id}")
    
    print("\n════════════════════════════════════════════════════════")
    print(" 🎉 HARİKA! Kurum tarafı hazır.")
    print(" İTÜ, Blokzinciri (von-network) üzerinde resmi olarak")
    print(" bir kimlik (DID) edindi ve Diploma formatını yayınladı.")
    print("════════════════════════════════════════════════════════")

if __name__ == '__main__':
    main()
