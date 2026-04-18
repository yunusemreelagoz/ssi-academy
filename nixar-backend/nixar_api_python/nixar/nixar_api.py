import base64
import cffi
import ctypes
import ctypes.util
import json
import logging
import os
import pathlib
import platform
from enum import Enum
from typing import Optional

from nixar.nixar_error import NixarError
from nixar.nixar_logging import NixarLogging

is_logging_init = False


class NixarMessageType(Enum):
  MESSAGE_TYPE_SIMPLE = 'MessageTypeSimple'
  MESSAGE_TYPE_CREDENTIAL_OFFER = 'MessageTypeCredentialOffer'
  MESSAGE_TYPE_CREDENTIAL_REQUEST = 'MessageTypeCredentialRequest'
  MESSAGE_TYPE_CREDENTIAL = 'MessageTypeCredential'
  MESSAGE_TYPE_PRESENTATION_REQUEST = 'MessageTypePresentationRequest'
  MESSAGE_TYPE_PRESENTATION = 'MessageTypePresentation'
  MESSAGE_TYPE_CONNECTION_REQUEST = 'MessageTypeConnectionRequest'
  MESSAGE_TYPE_CONNECTION_RESPONSE = 'MessageTypeConnectionResponse'


class CredDefIssuanceType(Enum):
  ISSUANCE_BY_DEFAULT = "IssuanceByDefault"
  ISSUANCE_ON_DEMAND = "IssuanceByDemand"


class Nixar:
  """
  A Python wrapper for the Nixar
  """

  def __init__(
      self,
      name: str,
      password_cb,
      role: Optional[str] = None,
      base64_seed: Optional[str] = None,
      wallet_type: str = "json",
      db_wallet_host: Optional[str] = None,
      db_wallet_username: Optional[str] = None,
      db_wallet_password: Optional[str] = None,
      genesis_path: Optional[str] = None):

    self.genesis_path = genesis_path or f"{os.getcwd()}/genesis.txn"
    self.agen_name = name
    self.__load_nixar_library()
    self.wallet_password_cb = self.__create_wallet_password_cb(password_cb)
    self.__create_agent(name, role, base64_seed, wallet_type, db_wallet_host, db_wallet_username, db_wallet_password)

  def __load_nixar_library(self):
    self.ffi = cffi.FFI()
    # load header
    folder_path = os.path.dirname(os.path.abspath(__file__))
    with open(f"{folder_path}/nixar_api.h") as f:
      lines = [line for line in f if not line.startswith('#')]
      self.ffi.cdef(''.join(lines))

    # load library
    logging.info(f"Platform {platform.system()}")
    if platform.system() == 'Darwin':
      find_library = ctypes.util.find_library("libnixar_core")
      if find_library is None:
        raise Exception('Nixar library not found')
      logging.info(find_library)
      self.nixar = self.ffi.dlopen(find_library)
    elif platform.system() == 'Windows':
      self.nixar = self.ffi.dlopen("libnixar_core.dll")
    elif platform.system() == 'Linux':
      find_library = ctypes.util.find_library('nixar_core')
      if find_library is None:
        raise Exception('Nixar library not found')
      logging.info(find_library)
      self.nixar = self.ffi.dlopen(find_library)
    else:
      raise Exception('Operating system not determined')

    logging.info('libnixar_core was loaded')

    self.__set_nixar_home_path(".tmp")

    # init logging
    if not is_logging_init:
      nixar_logging = NixarLogging()
      self.nixar_logging_cb = self.ffi.callback('ExternLogCallbackType', nixar_logging.log)
      self.log_level = 1
      self.nixar.init_logging(self.log_level, self.nixar_logging_cb)

  def __set_nixar_home_path(self, folder_name: str):
    if not os.path.exists("./" + folder_name):
      os.makedirs("./" + folder_name)
    absolute_nixar_home_path = self.__native_string(str(pathlib.Path().absolute()) + "/" + folder_name)
    self.nixar.set_nixar_home_path(absolute_nixar_home_path)

  def __create_wallet_password_cb(self, password_cb):
    return self.ffi.callback('WalletPasswordCallback', password_cb)

  def __native_string(self, v):
    if v is None:
      return self.ffi.NULL
    else:
      if type(v) is str:
        return self.ffi.new('char[]', v.encode('utf-8'))
      elif type(v) is bytes:
        return self.ffi.new('char[]', base64.b64encode(v))
      else:
        return self.ffi.new('char[]', json.dumps(v).encode('utf-8'))

  def ntv_str(self,v):
    if v is None:
      return self.ffi.NULL
    else:
      if type(v) is str:
        return self.ffi.new('char[]', v.encode('utf-8'))
      elif type(v) is bytes:
        return self.ffi.new('char[]', base64.b64encode(v))
      else:
        return self.ffi.new('char[]', json.dumps(v).encode('utf-8'))

  def __externalize_sdk_result(self, result):
    result = self.ffi.string(result).decode('utf-8')
    json_result = json.loads(result)
    if json_result['code'] == 'OK':
      if 'value' in json_result:
        return json_result['value']
    else:
      logging.error(result)
      raise NixarError(json_result)

  def __create_agent(self, alias: str, role: str, base64_seed: str, wallet_type: str = "sqlite",
                     db_wallet_host: str = None, db_wallet_username: str = None, db_wallet_user_password: str = None):

    init_params = {
      "alias": alias,
      "base64Seed": base64_seed,
      "role": role,
      "genesisPath": self.genesis_path,
      "walletInitParams": {
        "jsonWalletInitParams": {
          "walletName": alias
        }
      }
    }

    if wallet_type == "pgsql":
      init_params["walletInitParams"] = {
        "postgresWalletInitParams": {
          "dbHost": db_wallet_host,
          "dbUsername": db_wallet_username,
          "dbPassword": db_wallet_user_password,
          "walletName": alias,
        }
      }
    elif wallet_type == "sqlite":
      init_params["walletInitParams"] = {
        "sqliteWalletInitParams": {
          "walletName": alias
        }
      }

    logging.info(f"Agent will be created with {json.dumps(init_params)}")

    init_params = self.__native_string(json.dumps(init_params))
    result = self.__externalize_sdk_result(self.nixar.create_agent(init_params, self.wallet_password_cb))
    self.agent_handle = result['handle']

  def open_agent(self, alias: str, password: str):
    self.password = password

    alias = self.__native_string(alias)
    genesis_path = self.__native_string(self.genesis)

    result = self.__externalize_sdk_result(
      self.nixar.open_agent(alias, genesis_path, self.wallet_password_cb))

    self.agent_handle = result['handle']

  def change_password(self, new_password_cb):
    new_wallet_password_cb = self.__create_wallet_password_cb(new_password_cb)
    result = self.__externalize_sdk_result(self.nixar.change_password(self.agent_handle, new_wallet_password_cb))

  def register_agent_to_ledger(self, registration_request: str):
    registration_request = self.__native_string(registration_request)

    self.__externalize_sdk_result(
      self.nixar.register_agent_to_ledger(self.agent_handle, registration_request))

  def create_local_did(self, base64_seed: str) -> dict:
    base64_seed = self.__native_string(base64_seed)

    result = self.__externalize_sdk_result(
      self.nixar.create_local_did(self.agent_handle, base64_seed))

    return result

  def set_attribute(self, attr_name: str, attr_value: str):
    attr_name = self.__native_string(attr_name)
    attr_value = self.__native_string(attr_value)

    result = self.__externalize_sdk_result(
      self.nixar.set_attribute(self.agent_handle, attr_name, attr_value))

  def connection_get_public_invitation(self) -> dict:
    result = self.__externalize_sdk_result(
      self.nixar.connection_get_public_invitation(self.agent_handle))

    return result

  def connection_create_local_invitation(self, label: str, endpoint: str, base64_seed: str = None) -> dict:
    label = self.__native_string(label)
    endpoint = self.__native_string(endpoint)
    base64_seed = self.__native_string(base64_seed)

    result = self.__externalize_sdk_result(
      self.nixar.connection_create_local_invitation(self.agent_handle, label, endpoint, base64_seed))

    return result

  def connection_create_request(self, invitation: dict, base64_seed: str = None) -> dict:
    invitation = self.__native_string(invitation)
    base64_seed = self.__native_string(base64_seed)

    result = self.__externalize_sdk_result(
      self.nixar.connection_create_request(self.agent_handle, invitation, base64_seed))

    return result

  def connection_accept_request(self, connection_request: dict, alias: str) -> dict:
    connection_request = self.__native_string(connection_request)
    alias = self.__native_string(alias)

    result = self.__externalize_sdk_result(
      self.nixar.connection_accept_request(self.agent_handle, connection_request, alias))

    return result

  def connection_accept_response(self, connection_response: dict):
    connection_response = self.__native_string(connection_response)

    self.__externalize_sdk_result(
      self.nixar.connection_accept_response(self.agent_handle, connection_response))

  def connection_encrypt(self, from_did: str, their_did: str, message_type: Enum, content: dict) -> dict:
    from_did = self.__native_string(from_did)
    their_did = self.__native_string(their_did)
    content = self.__native_string(content)

    tp = self.nixar.MessageTypeSimple
    if message_type == NixarMessageType.MESSAGE_TYPE_SIMPLE:
      tp = self.nixar.MessageTypeSimple
    elif message_type == NixarMessageType.MESSAGE_TYPE_CONNECTION_REQUEST:
      tp = self.nixar.MessageTypeConnectionRequest
    elif message_type == NixarMessageType.MESSAGE_TYPE_CONNECTION_RESPONSE:
      tp = self.nixar.MessageTypeConnectionResponse
    elif message_type == NixarMessageType.MESSAGE_TYPE_CREDENTIAL_OFFER:
      tp = self.nixar.MessageTypeCredentialOffer
    elif message_type == NixarMessageType.MESSAGE_TYPE_CREDENTIAL_REQUEST:
      tp = self.nixar.MessageTypeCredentialRequest
    elif message_type == NixarMessageType.MESSAGE_TYPE_CREDENTIAL:
      tp = self.nixar.MessageTypeCredential
    elif message_type == NixarMessageType.MESSAGE_TYPE_PRESENTATION_REQUEST:
      tp = self.nixar.MessageTypePresentationRequest
    elif message_type == NixarMessageType.MESSAGE_TYPE_PRESENTATION:
      tp = self.nixar.MessageTypePresentation
    else:
      raise Exception("Message type not found")

    result = self.__externalize_sdk_result(
      self.nixar.connection_encrypt(self.agent_handle, from_did, their_did, tp, content))

    return result

  def connection_decrypt(self, message: dict) -> list:
    message = self.__native_string(message)

    result = self.__externalize_sdk_result(
      self.nixar.connection_decrypt(self.agent_handle, message))

    return result

  def connection_get_connections(self) -> list:
    result = self.__externalize_sdk_result(
      self.nixar.connection_get_connections(self.agent_handle))

    return result

  def sign_with_did(self, from_did: str, data) -> str:
    from_did = self.__native_string(from_did)
    data = self.__native_string(data)

    result = self.__externalize_sdk_result(
      self.nixar.sign_with_did(self.agent_handle, from_did, data))

    return result

  def verify_signature_with_their_did(self, their_did, data, signature) -> bool:
    their_did = self.__native_string(their_did)
    data = self.__native_string(data)
    signature = self.__native_string(signature)

    result = self.__externalize_sdk_result(
      self.nixar.verify_with_their_did(self.agent_handle, their_did, data, signature))

    return result

  def verify_signature_with_did_public_key(self, did_public_key: str, data: str, signature: str) -> bool:
    did_public_key = self.__native_string(did_public_key)
    data = self.__native_string(data)
    signature = self.__native_string(signature)
    result = self.__externalize_sdk_result(
      self.nixar.verify_with_did_public_key(self.agent_handle, did_public_key, data, signature))

    return result

  def get_their_did_as_did_doc(self, their_did: str) -> dict:
    their_did = self.__native_string(their_did)
    result = self.__externalize_sdk_result(
      self.nixar.get_their_did_as_did_doc(self.agent_handle, their_did))

    return result

  def issuer_create_schema(self, schema_name: str, attribute_set: list, schema_version: str) -> dict:
    schema_name = self.__native_string(schema_name)
    attribute_set = self.__native_string(attribute_set)
    schema_version = self.__native_string(schema_version)

    result = self.__externalize_sdk_result(
      self.nixar.issuer_create_schema(self.agent_handle, schema_name, attribute_set, schema_version))

    return result

  def issuer_get_schema(self, schema_id: str) -> dict:
    schema_id = self.__native_string(schema_id)

    result = self.__externalize_sdk_result(
      self.nixar.issuer_get_schema(self.agent_handle, schema_id))

    return result

  def issuer_get_schemas(self) -> list:
    result = self.__externalize_sdk_result(
      self.nixar.issuer_get_schemas(self.agent_handle))

    return result

  def issuer_create_credential_definition(self, schema_id: str, is_revocable: bool, tag: str,
                                          issuance_type=CredDefIssuanceType.ISSUANCE_BY_DEFAULT,
                                          max_cred_num=1000) -> dict:
    schema_id = self.__native_string(schema_id)
    tag = self.__native_string(tag)
    max_cred_num = self.__native_string(max_cred_num)
    tp = self.nixar.ISSUANCE_BY_DEFAULT
    if issuance_type == CredDefIssuanceType.ISSUANCE_BY_DEFAULT:
      tp = self.nixar.ISSUANCE_BY_DEFAULT
    elif issuance_type == CredDefIssuanceType.ISSUANCE_ON_DEMAND:
      tp = self.nixar.ISSUANCE_ON_DEMAND
    else:
      raise Exception("Issuance type not found")

    result = self.__externalize_sdk_result(
      self.nixar.issuer_create_credential_definition(self.agent_handle, schema_id, is_revocable, tp,
                                                     max_cred_num, tag))

    return result

  # TODO review and update return type
  def issuer_get_tail(self, rev_reg_id: str) -> dict:
    rev_reg_id = self.__native_string(rev_reg_id)

    result = self.__externalize_sdk_result(
      self.nixar.issuer_get_tail(self.agent_handle, rev_reg_id))

    return result

  def issuer_get_credential_definition(self, cred_def_id: str) -> dict:
    cred_def_id = self.__native_string(cred_def_id)

    result = self.__externalize_sdk_result(
      self.nixar.issuer_get_credential_definition(self.agent_handle, cred_def_id))

    return result

  def issuer_get_credential_definitions(self) -> list:
    result = self.__externalize_sdk_result(
      self.nixar.issuer_get_credential_definitions(self.agent_handle))

    return result

  def issuer_create_credential_offer(self, cred_def_id: str, issuer_nonce: str) -> dict:
    cred_def_id = self.__native_string(cred_def_id)
    issuer_nonce = self.__native_string(issuer_nonce)

    result = self.__externalize_sdk_result(
      self.nixar.issuer_create_credential_offer(self.agent_handle, cred_def_id, issuer_nonce))

    return result

  def issuer_create_credential(self, cred_request: str, cred_values: str, issuer_nonce: str) -> dict:
    cred_request = self.__native_string(cred_request)
    cred_values = self.__native_string(cred_values)
    issuer_nonce = self.__native_string(issuer_nonce)

    result = self.__externalize_sdk_result(
      self.nixar.issuer_create_credential(self.agent_handle, cred_request, cred_values, issuer_nonce))
    return result

  def issuer_revoke_credential(self, cred_rev_index: str, cred_def_id: str):
    cred_rev_index = self.__native_string(cred_rev_index)
    cred_def_id = self.__native_string(cred_def_id)

    result = self.__externalize_sdk_result(
      self.nixar.issuer_revoke_credential(self.agent_handle, cred_rev_index, cred_def_id))

  def prover_create_credential_request(self, cred_offer: str) -> dict:
    cred_offer = self.__native_string(cred_offer)

    result = self.__externalize_sdk_result(
      self.nixar.prover_create_credential_request(self.agent_handle, cred_offer))

    return result

  def prover_store_credential(self, cred_id: str, credential: dict) -> bool:
    cred_id = self.__native_string(cred_id)
    credential = self.__native_string(credential)

    result = self.__externalize_sdk_result(
      self.nixar.prover_store_credential(self.agent_handle, cred_id, credential))

    return result

  def prover_get_credential(self, cred_id: str) -> dict:
    cred_id = self.__native_string(cred_id)

    result = self.__externalize_sdk_result(
      self.nixar.prover_get_credential(self.agent_handle, cred_id))

    return result

  def prover_get_credentials(self) -> dict:
    result = self.__externalize_sdk_result(
      self.nixar.prover_get_credentials(self.agent_handle))

    return result

  def prover_store_tail(self, rev_reg_id: str, tail: str):
    rev_reg_id = self.__native_string(rev_reg_id)
    tail = self.__native_string(tail)

    self.nixar.prover_store_tail(self.agent_handle, rev_reg_id, tail)

  def prover_fetch_credential_for_presentation_request(self, presentation_request: dict) -> dict:
    presentation_request = self.__native_string(presentation_request)

    result = self.__externalize_sdk_result(
      self.nixar.prover_fetch_credential_for_presentation_request(self.agent_handle, presentation_request))

    return result

  def prover_create_presentation(self, presentation_request: dict, self_attested_values: dict) -> dict:
    presentation_request = self.__native_string(presentation_request)
    self_attested_values = self.__native_string(self_attested_values)

    result = self.__externalize_sdk_result(
      self.nixar.prover_create_presentation(self.agent_handle, presentation_request, self_attested_values))

    return result

  def verifier_verify_presentation(self, presentation_request: dict, presentation: dict) -> bool:
    presentation_request = self.__native_string(presentation_request)
    presentation = self.__native_string(presentation)

    result = self.__externalize_sdk_result(
      self.nixar.verifier_verify_presentation(self.agent_handle, presentation_request, presentation))

    return result

  def get_connection_by_my_did(self, my_did: str) -> dict:
    my_did = self.__native_string(my_did)
    result = self.__externalize_sdk_result(
      self.nixar.get_connection_by_my_did(self.agent_handle, my_did))

    return result

  def get_connection_by_their_did(self, their_did: str) -> dict:
    their_did = self.__native_string(their_did)
    result = self.__externalize_sdk_result(
      self.nixar.get_connection_by_their_did(self.agent_handle, their_did))

    return result

  def get_connection_by_alias(self, alias: str) -> dict:
    alias = self.__native_string(alias)
    result = self.__externalize_sdk_result(
      self.nixar.get_connection_by_alias(self.agent_handle, alias))

    return result

  def get_connection_by_label(self, label: str) -> dict:
    label = self.__native_string(label)
    result = self.__externalize_sdk_result(
      self.nixar.get_connection_by_label(self.agent_handle, label))

    return result
