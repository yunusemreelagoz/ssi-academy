import base64
import json
import logging
import random
from datetime import datetime

import cffi

from nixar.nixar_api import Nixar, CredDefIssuanceType
from nixar.nixar_error import NixarError

DB_HOST = "host.docker.internal"
DB_USERNAME = "nixar"
DB_PASSWORD = "123456"
MAX_CRED_NUM = 1000

logger = logging.getLogger(__name__)
ffi = cffi.FFI()

names = [
    "JALE",
    "ALİ",
    "MAHMUT",
    "MANSUR KÜRŞAD",
    "GAMZE",
    "MİRAÇ",
    "YÜCEL",
    "KUBİLAY",
    "HAYATİ",
    "BEDRİYE MÜGE",
    "BİRSEN",
    "SERDAL",
    "BÜNYAMİN",
    "ÖZGÜR",
    "FERDİ",
    "REYHAN",
    "İLHAN",
    "GÜLŞAH",
    "NALAN",
    "SEMİH",
    "ERGÜN",
    "FATİH",
    "ŞENAY",
    "SERKAN",
    "EMRE",
    "BAHATTİN",
    "IRAZCA",
    "HATİCE",
    "BARIŞ",
    "REZAN",
    "FATİH",
    "FUAT",
    "GÖKHAN",
    "ORHAN",
    "MEHMET",
    "EVREN",
    "OKTAY",
    "HARUN",
    "YAVUZ",
    "PINAR",
    "MEHMET",
    "UMUT",
    "MESUDE",
    "HÜSEYİN CAHİT",
    "HAŞİM ONUR",
    "EYYUP SABRİ",
    "MUSTAFA",
    "MUSTAFA",
    "UFUK",
    "AHMET ALİ",
    "MEDİHA",
    "HASAN",
    "KAMİL",
    "NEBİ",
    "ÖZCAN",
    "NAGİHAN",
    "CEREN",
    "SERKAN",
    "HASAN",
    "YUSUF KENAN",
    "ÇETİN",
    "TARKAN",
    "MERAL LEMAN",
    "ERGÜN",
    "KENAN AHMET",
    "URAL",
    "YAHYA",
    "BENGÜ",
    "FATİH NAZMİ",
    "DİLEK",
    "MEHMET",
    "TUFAN AKIN",
    "MEHMET",
    "TURGAY YILMAZ",
    "GÜLDEHEN",
    "GÖKMEN",
    "BÜLENT",
    "EROL",
    "BAHRİ",
    "ÖZEN ÖZLEM",
    "SELMA",
    "TUĞSEM",
    "TESLİME NAZLI",
    "GÜLÇİN",
    "İSMAİL",
    "MURAT",
    "EBRU",
    "TÜMAY",
    "AHMET",
    "EBRU",
    "HÜSEYİN YAVUZ",
    "BAŞAK",
    "AYŞEGÜL",
    "EVRİM",
    "YASER",
    "ÜLKÜ",
    "ÖZHAN",
    "UFUK",
    "AKSEL",
    "FULYA",
    "BURCU",
    "TAYLAN",
    "YILMAZ",
    "ZEYNEP",
    "BAYRAM",
    "GÜLAY",
    "RABİA",
    "SEVDA",
    "SERHAT",
    "ENGİN",
    "ASLI",
    "TUBA",
    "BARIŞ",
    "SEVGİ",
    "KALENDER",
    "HALİL",
    "BİLGE",
    "FERDA",
    "EZGİ",
    "AYSUN",
    "SEDA",
    "ÖZLEM",
    "ÖZDEN",
    "KORAY",
    "SENEM",
    "ZEYNEP",
    "EMEL",
    "BATURAY KANSU",
    "NURAY",
    "AYDOĞAN",
    "ÖZLEM",
    "DENİZ",
    "İLKNUR",
    "TEVFİK ÖZGÜN",
    "HASAN SERKAN",
    "KÜRŞAT",
    "SEYFİ",
    "ŞEYMA",
    "ÖZLEM",
    "ERSAGUN",
    "DİLBER",
    "MESUT",
    "ELİF",
    "MUHAMMET FATİH",
    "ÖZGÜR SİNAN",
    "MEHMET ÖZGÜR",
    "MAHPERİ",
    "ONUR",
    "İBRAHİM",
    "FATİH",
    "SEVİL",
    "SÜHEYLA",
    "VOLKAN",
    "İLKAY",
    "İLKNUR",
    "ZÜMRÜT ELA",
    "HALE",
    "YENER",
    "SEDEF",
    "FADIL",
    "SERPİL",
    "ZÜLFİYE",
    "SULTAN",
    "MUAMMER HAYRİ",
    "DERVİŞ",
    "YAŞAR GÖKHAN",
    "TUBA HANIM",
    "MEHRİ",
    "MUSTAFA FERHAT",
    "SERDAR",
    "MUSTAFA ERSAGUN",
    "ONAT",
    "ŞÜKRÜ",
    "OLCAY BAŞAK",
    "SERDAR",
    "YILDIZ",
    "AYDIN",
    "ALİ HALUK",
    "NİHAT BERKAY",
    "İSMAİL",
    "AYKAN",
    "SELÇUK",
    "MEHMET",
    "NEZİH",
    "MUSTAFA",
    "TİMUR",
    "ERHAN",
    "MUSTAFA",
    "MUTLU",
    "MEHMET HÜSEYİN",
    "İSMAİL EVREN",
    "OSMAN ERSEGUN",
    "MEHMET",
    "ELİF",
    "SERKAN",
    "MESUT",
    "MEHMET HİLMİ",
    "ASUDAN TUĞÇE",
    "AHMET GÖKHAN DAĞ",
]

university = [
    "Abant İzzet Baysal Üniversitesi",
    "Abdullah Gül Üniversitesi",
    "Acıbadem Mehmet Ali Aydınlar Üniversitesi",
    "Adana Bilim Ve Teknoloji Üniversitesi",
    "Adıyaman Üniversitesi",
    "Adnan Menderes Üniversitesi",
    "Afyon Kocatepe Üniversitesi",
    "Ağrı İbrahim Çeçen Üniversitesi",
    "Ahi Evran Üniversitesi",
    "Akdeniz Üniversitesi",
    "Aksaray Üniversitesi",
    "Alanya Alaaddin Keykubat Üniversitesi",
    "Alanya Hamdullah Emin Paşa Üniversitesi",
    "Altınbaş Üniversitesi",
    "Amasya Üniversitesi",
    "Anadolu Üniversitesi",
    "Ankara Sosyal Bilimler Üniversitesi",
    "Ankara Üniversitesi",
    "Ankara Yıldırım Beyazıt Üniversitesi",
    "Antalya Akev Üniversitesi",
    "Antalya Bilim Üniversitesi",
    "Ardahan Üniversitesi",
    "Artvin Çoruh Üniversitesi",
    "Ataşehir Adıgüzel Meslek Yüksekokulu",
    "Atatürk Üniversitesi",
    "Atılım Üniversitesi",
    "Avrasya Üniversitesi",
    "Avrupa Meslek Yüksekokulu",
    "Bahçeşehir Üniversitesi",
    "Balıkesir Üniversitesi",
    "Bandırma Onyedi Eylül Üniversitesi",
    "Bartın Üniversitesi",
    "Başkent Üniversitesi",
    "Batman Üniversitesi",
    "Bayburt Üniversitesi",
    "Beykent Üniversitesi",
    "Beykoz Üniversitesi",
    "Bezm-İ Âlem Vakıf Üniversitesi",
    "Bilecik Şeyh Edebali Üniversitesi",
    "Bingöl Üniversitesi",
    "Biruni Üniversitesi",
    "Bitlis Eren Üniversitesi",
    "Boğaziçi Üniversitesi",
    "Bozok Üniversitesi",
    "Bursa Teknik Üniversitesi",
    "Bülent Ecevit Üniversitesi",
    "Canik Başarı Üniversitesi",
    "Cumhuriyet Üniversitesi",
    "Çağ Üniversitesi",
    "Çanakkale Onsekiz Mart Üniversitesi",
    "Çankaya Üniversitesi",
    "Çankırı Karatekin Üniversitesi",
    "Çukurova Üniversitesi",
    "Dicle Üniversitesi",
    "Doğuş Üniversitesi",
    "Dokuz Eylül Üniversitesi",
    "Dumlupınar Üniversitesi",
    "Düzce Üniversitesi",
    "Ege Üniversitesi",
    "Erciyes Üniversitesi",
    "Erzincan Üniversitesi",
    "Erzurum Teknik Üniversitesi",
    "Eskişehir Osmangazi Üniversitesi",
    "Faruk Saraç Tasarım Meslek Yüksekokulu",
    "Fatih Sultan Mehmet Vakıf Üniversitesi",
    "Fırat Üniversitesi",
    "Galatasaray Üniversitesi",
    "Gazi Üniversitesi",
    "Gaziantep Üniversitesi",
    "Gaziosmanpaşa Üniversitesi",
    "Gebze Teknik Üniversitesi",
    "Giresun Üniversitesi",
    "Gümüşhane Üniversitesi",
    "Hacettepe Üniversitesi",
    "Hakkari Üniversitesi",
    "Haliç Üniversitesi",
    "Harran Üniversitesi",
    "Hasan Kalyoncu Üniversitesi",
    "Hitit Üniversitesi",
    "Iğdır Üniversitesi",
    "Işık Üniversitesi",
    "İbn Haldun Üniversitesi",
    "İhsan Doğramacı Bilkent Üniversitesi",
    "İnönü Üniversitesi",
    "İskenderun Teknik Üniversitesi",
    "İstanbul 29 Mayıs Üniversitesi",
    "İstanbul Arel Üniversitesi",
    "İstanbul Aydın Üniversitesi",
    "İstanbul Ayvansaray Üniversitesi",
    "İstanbul Bilgi Üniversitesi",
    "İstanbul Bilim Üniversitesi",
    "İstanbul Esenyurt Üniversitesi",
    "İstanbul Gedik Üniversitesi",
    "İstanbul Gelişim Üniversitesi",
    "İstanbul Kavram Meslek Yüksekokulu",
    "İstanbul Kemerburgaz Üniversitesi",
    "İstanbul Kent Üniversitesi",
    "İstanbul Kültür Üniversitesi",
    "İstanbul Medeniyet Üniversitesi",
    "İstanbul Medipol Üniversitesi",
    "İstanbul Rumeli Üniversitesi",
    "İstanbul Sabahattin Zaim Üniversitesi",
    "İstanbul Şehir Üniversitesi",
    "İstanbul Şişli Meslek Yüksekokulu",
    "İstanbul Teknik Üniversitesi",
    "İstanbul Ticaret Üniversitesi",
    "İstanbul Üniversitesi",
    "İstanbul Yeni Yüzyıl Üniversitesi",
    "İstinye Üniversitesi",
    "İzmir Bakırçay Üniversitesi",
    "İzmir Demokrasi Üniversitesi",
    "İzmir Ekonomi Üniversitesi",
    "İzmir Katip Çelebi Üniversitesi",
    "İzmir Yüksek Teknoloji Enstitüsü",
    "Kadir Has Üniversitesi",
    "Kafkas Üniversitesi",
    "Kahramanmaraş Sütçü İmam Üniversitesi",
    "Kapadokya Üniversitesi",
    "Karabük Üniversitesi",
    "Karadeniz Teknik Üniversitesi",
    "Karamanoğlu Mehmetbey Üniversitesi",
    "Kastamonu Üniversitesi",
    "Kırıkkale Üniversitesi",
    "Kırklareli Üniversitesi",
    "Kilis 7 Aralık Üniversitesi",
    "Kocaeli Üniversitesi",
    "Koç Üniversitesi",
    "Konya Gıda Ve Tarım Üniversitesi",
    "Kto Karatay Üniversitesi",
    "Maltepe Üniversitesi",
    "Manisa Celâl Bayar Üniversitesi",
    "Mardin Artuklu Üniversitesi",
    "Marmara Üniversitesi",
    "Mef Üniversitesi",
    "Mehmet Akif Ersoy Üniversitesi",
    "Melikşah Üniversitesi",
    "Mersin Üniversitesi",
    "Mimar Sinan Güzel Sanatlar Üniversitesi",
    "Muğla Sıtkı Koçman Üniversitesi",
    "Munzur Üniversitesi",
    "Mustafa Kemal Üniversitesi",
    "Muş Alparslan Üniversitesi",
    "Namık Kemal Üniversitesi",
    "Necmettin Erbakan Üniversitesi",
    "Nevşehir Hacı Bektaş Veli Üniversitesi",
    "Niğde Ömer Halisdemir Üniversitesi",
    "Niğde Üniversitesi",
    "Nişantaşı Üniversitesi",
    "Nuh Naci Yazgan Üniversitesi",
    "Okan Üniversitesi",
    "Ondokuz Mayıs Üniversitesi",
    "Ordu Üniversitesi",
    "Orta Doğu Teknik Üniversitesi",
    "Osmaniye Korkut Ata Üniversitesi",
    "Özyeğin Üniversitesi",
    "Pamukkale Üniversitesi",
    "Piri Reis Üniversitesi",
    "Recep Tayyip Erdoğan Üniversitesi",
    "Sabancı Üniversitesi",
    "Sağlık Bilimleri Üniversitesi",
    "Sakarya Üniversitesi",
    "Sanko Üniversitesi",
    "Selçuk Üniversitesi",
    "Siirt Üniversitesi",
    "Sinop Üniversitesi",
    "Süleyman Demirel Üniversitesi",
    "Şırnak Üniversitesi",
    "Ted Üniversitesi",
    "Tobb Ekonomi Ve Teknoloji Üniversitesi",
    "Toros Üniversitesi",
    "Trakya Üniversitesi",
    "Türk Hava Kurumu Üniversitesi",
    "Türk-Alman Üniversitesi",
    "Ufuk Üniversitesi",
    "Uludağ Üniversitesi",
    "Uşak Üniversitesi",
    "Üsküdar Üniversitesi",
    "Yalova Üniversitesi",
    "Yaşar Üniversitesi",
    "Yeditepe Üniversitesi",
    "Yıldız Teknik Üniversitesi",
    "Yüksek İhtisas Üniversitesi",
    "Yüzüncü Yıl Üniversitesi",
]

department = [
    "Gemi Makineleri İşletme Mühendisliği",
    "Bilgisayar Mühendisliği",
    "Bilişim Sistemleri Mühendisliği",
    "Çevre Mühendisliği",
    "Makine Mühendisliği",
    "Elektrik Mühendisliği",
    "Elektrik-Elektronik Mühendisliği",
    "Endüstri Mühendisliği",
    "Enerji Sistemleri Mühendisliği",
    "Geomatik Mühendisliği",
    "İnşaat Mühendisliği",
    "Fizik Mühendisliği",
    "Jeoloji Mühendisliği",
    "Gıda Mühendisliği",
    "Harita Mühendisliği",
    "Havacılık ve Uzay Mühendisliği",
    "İç Mimarlık",
    "Kimya Mühendisliği",
    "Maden Mühendisliği",
    "Mekatronik Mühendisliği",
    "Malzeme Bilimi ve Mühendisliği",
    "Metalurji ve Malzeme Mühendisliği",
    "Nanoteknoloji Mühendisliği",
    "Orman Endüstri Mühendisliği",
    "Nükleer Enerji Mühendisliği",
    "Otomotiv Mühendisliği",
    "Tekstil Mühendisliği",
    "Yazılım Mühendisliği",
    "Ziraat Mühendisliği",
    "Endüstriyel Tasarım Mühendisliği",
    "Raylı Sistemler Mühendisliği",
    "Biyomühendislik",
]


def get_random_name():
    return random.choice(names)


def get_random_gender():
    return random.choice(["MALE", "FEMALE"])


def get_random_unv():
    return random.choice(university)


def get_random_dept():
    return random.choice(department)


def get_random_age():
    return random.randint(18, 40)


def get_random_grade():
    return "{:.2f}".format(random.uniform(2.0, 4.0))


def get_random_identity_number():
    return random.randint(10000000000, 99999999999)


def get_presentation_request(schema_id, cred_def_id):
    # region tag::CreatePresentationRequest[]
    # Default restriction operator or, the following restriction equal that
    # "restrictions": { "$or":
    #                   [
    #                     {"schema_id": schema_id},
    #                     {"cred_def_id": cred_def_id}
    #                 ]}
    pres_req = {
        "name": "IdentityPR",
        "version": "2.0",
        "nonce": "92210735",
        "requestedAttributes": {
            "attribute1_referent": {
                "name": "name",
                # Optional
                "restrictions": {
                    "$and": [{"schema_id": schema_id}, {"cred_def_id": cred_def_id}]
                },
            },
            "attribute2_referent": {"name": "surname"},
            "attribute3_referent": {"name": "gender"},
            "self_attested_referent": {"name": "hobies"},
        },
        "requestedPredicates": {
            "predicate1_referent": {"name": "age", "p_type": ">", "p_value": 10}
        },
    }
    # endregion end::CreatePresentationRequest[]
    return pres_req


def generate_sample_cred_values(attr_names):
    cred_values = {}
    for attr_name in attr_names:
        if attr_name == "age":
            age = get_random_age()
            cred_values[attr_name] = {"raw": str(age), "encoded": str(age)}
        elif attr_name == "name":
            name = get_random_name()
            cred_values[attr_name] = {
                "raw": name,
                "encoded": str(
                    int.from_bytes(name.encode(), byteorder="big", signed=False)
                ),
            }
        elif attr_name == "surname":
            name = get_random_name()
            cred_values[attr_name] = {
                "raw": name,
                "encoded": str(
                    int.from_bytes(name.encode(), byteorder="big", signed=False)
                ),
            }
        elif attr_name == "identity_number":
            identity_number = get_random_identity_number()
            cred_values[attr_name] = {
                "raw": str(identity_number),
                "encoded": str(identity_number),
            }
        elif attr_name == "surname":
            surname = get_random_name()
            cred_values[attr_name] = {
                "raw": surname,
                "encoded": str(
                    int.from_bytes(surname.encode(), byteorder="big", signed=False)
                ),
            }
        elif attr_name == "grade":
            grade = get_random_grade()
            cred_values[attr_name] = {"raw": str(grade), "encoded": str(grade)}
        elif attr_name == "university":
            university = get_random_unv()
            cred_values[attr_name] = {
                "raw": university,
                "encoded": str(
                    int.from_bytes(university.encode(), byteorder="big", signed=False)
                ),
            }
        elif attr_name == "department":
            department = get_random_dept()
            cred_values[attr_name] = {
                "raw": department,
                "encoded": str(
                    int.from_bytes(department.encode(), byteorder="big", signed=False)
                ),
            }
        elif attr_name == "gender":
            gender = get_random_gender()
            cred_values[attr_name] = {
                "raw": gender,
                "encoded": str(
                    int.from_bytes(gender.encode(), byteorder="big", signed=False)
                ),
            }

    return cred_values


def get_timestamp_tag():
    return datetime.now().strftime("%Y%m%d%H%M")


def create_nixar_agent_w_json_wallet(name, password_cb, role=None, base64_seed=None):
    try:
        return Nixar(name, password_cb, role, base64_seed)
    except NixarError as err:
        # Register the agent to the ledger. This operation must be done by different authority or process
        if "AgentNotRegistered" == err.code:
            logger.warning(err)
            registration_info = json.loads(err.message)
            registration_info["alias"] = name
            registration_info["role"] = "ENDORSER" if role == "ENDORSER" else None
            _register_agent_to_ledger(registration_info)
            try:
                return Nixar(name, password_cb, role, base64_seed)
            except Exception:
                return Nixar(name, password_cb, role, base64_seed)
        else:
            raise err


def create_nixar_agent_w_sqlite_wallet(name, password_cb, role=None):
    # region tag::CreateAgent[]
    try:
        return Nixar(name, password_cb, role, None, "sqlite")
    except NixarError as err:
        # Register the agent to the ledger. This operation must be done by different authority or process
        if "AgentNotRegistered" == err.code:
            logger.warning(err)
            registration_info = json.loads(err.message)
            registration_info["alias"] = name
            registration_info["role"] = "ENDORSER"
            _register_agent_to_ledger(registration_info)
            return Nixar(name, password_cb, role, None, "sqlite")
        else:
            raise err
    # endregion end::CreateAgent[]


def create_nixar_agent_w_pqsgl_wallet(name, password_cb, role=None):
    try:
        return Nixar(
            name, password_cb, role, None, "pgsql", DB_HOST, DB_USERNAME, DB_PASSWORD
        )
    except NixarError as err:
        # Register the agent to the ledger. This operation must be done by different authority or process
        if "AgentNotRegistered" == err.code:
            logger.warning(err)
            registration_info = json.loads(err.message)
            registration_info["alias"] = name
            registration_info["role"] = "ENDORSER"
            _register_agent_to_ledger(registration_info)
            return Nixar(
                name,
                password_cb,
                role,
                None,
                "pgsql",
                DB_HOST,
                DB_USERNAME,
                DB_PASSWORD,
            )
        else:
            raise err


def _register_agent_to_ledger(registration_info):
    logger.info(f"Agent registration info {json.dumps(registration_info)}")
    trustee.register_agent_to_ledger(json.dumps(registration_info))


def create_schema_if_not_exist(issuer, schema_name, attribute_set):
    schemas = issuer.issuer_get_schemas()
    for schema in schemas:
        if schema["name"] == schema_name:
            return schema["id"]
    # region tag::CreateSchema[]
    schema_version = "2.0"
    schema_id = issuer.issuer_create_schema(schema_name, attribute_set, schema_version)
    logger.info("The issuer created a schema created, schema_id: {}".format(schema_id))
    # endregion end::CreateSchema[]
    return schema_id


def create_credential_definition(
    issuer,
    schema_id: str,
    is_revocable: bool,
    tag: str,
    issuance_type=CredDefIssuanceType.ISSUANCE_BY_DEFAULT,
):
    # region tag::CreateCredentialDefinition[]
    # if it is not revocable, issuance_type, max_cred_num will be ignored in nixar
    cred_def_id = issuer.issuer_create_credential_definition(
        schema_id, is_revocable, tag, issuance_type, MAX_CRED_NUM
    )
    logger.info("Credential definition created, cred_def_id: " + cred_def_id)
    # endregion end::CreateCredentialDefinition[]
    return cred_def_id


def native_string(v):
    if v is None:
        return ffi.NULL
    else:
        if type(v) is str:
            return ffi.new("char[]", v.encode("utf-8"))
        elif type(v) is bytes:
            return ffi.new("char[]", base64.b64encode(v))
        else:
            return ffi.new("char[]", json.dumps(v).encode("utf-8"))


def copy_native_string(dest, src):
    ffi.memmove(dest, src, len(src))


def encode_base64(text: str):
    if text is None:
        return None
    text_bytes = text.encode("utf-8")
    return base64.b64encode(text_bytes).decode("utf-8")


trustee_password = native_string("123456")
base64_inv_seed = encode_base64("000000000000000000000000Trustee1")
trustee = Nixar("trustee", lambda: trustee_password, "TRUSTEE", base64_inv_seed)

def create_holder_agent_w_json_wallet(name, password_cb, base64_seed=None):
    try:
        return Nixar(name, password_cb, None, base64_seed)
    except NixarError as err:
        if "AgentNotRegistered" == err.code:
            logger.info(f"Holder '{name}' initialization triggered AgentNotRegistered; purposefully avoiding ledger write.")
            try:
                return Nixar(name, password_cb, None, base64_seed)
            except Exception:
                return Nixar(name, password_cb, None, base64_seed)
        else:
            raise err
