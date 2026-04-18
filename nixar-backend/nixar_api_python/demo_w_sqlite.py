import json
import logging
import random

import test_utils
from nixar.nixar_api import CredDefIssuanceType
from test_utils import create_nixar_agent_w_sqlite_wallet, create_schema_if_not_exist, create_credential_definition, \
  get_timestamp_tag, get_presentation_request, generate_sample_cred_values


def demo_revocable():
  schema_name = "PythonSchemaRevocableV.0.3"
  attribute_set = ["name", "surname", "age", "gender"]
  schema_id = create_schema_if_not_exist(issuer, schema_name, attribute_set)

  tag = get_timestamp_tag()
  cred_def_id = create_credential_definition(issuer, schema_id, True, tag, CredDefIssuanceType.ISSUANCE_BY_DEFAULT)
  logging.info("The issuer created credential definition for schema_id: {}, cred_def_id:{}".format(schema_id, cred_def_id))

  # region tag::CreateCredentialOffer[]
  issuer_nonce = str(random.getrandbits(80))
  cred_offer = issuer.issuer_create_credential_offer(cred_def_id, issuer_nonce)
  logging.info("The Issuer created a credential offer for the prover with cred_def_id: {}, cred_offer:{}".format(cred_def_id, json.dumps(cred_offer)))
  # endregion end::CreateCredentialOffer[]

  # region tag::CreateCredentialRequest[]
  cred_request = prover.prover_create_credential_request(cred_offer)
  logging.info("The prover create a credential request, cred_request: {}".format(cred_def_id, json.dumps(cred_request)))
  # endregion end::CreateCredentialRequest[]

  # region tag::CreateCredential[]
  cred_values = generate_sample_cred_values(attribute_set)
  cred_info = issuer.issuer_create_credential(cred_request, cred_values, issuer_nonce)
  cred = cred_info["credential"]
  cred_rev_id = cred_info["credRevId"]
  logging.info("The issuer created a credential, cred: {}".format(cred_def_id, json.dumps(cred)))
  # endregion end::CreateCredential[]

  # region tag::StoreCredential[]
  store_cred = prover.prover_store_credential(None, cred)
  logging.info("The prover stored the credential, store_cred: {}".format(store_cred))
  # endregion end::StoreCredential[]

  # get tail from issuer
  if "rev_reg_id" in cred and cred["rev_reg_id"] is not None:
    # region tag::GetTail[]
    tail_name_of_rev_reg = cred["rev_reg_id"]
    tail = issuer.issuer_get_tail(tail_name_of_rev_reg)
    # endregion end::GetTail[]

    # region tag::StoreTail[]
    prover.prover_store_tail("P_" + tail_name_of_rev_reg, tail)
    logging.info("The prover stored the tail")
    # endregion end::StoreTail[]

  # region tag::CreatePresentation[]
  self_attested_values = {"self_attested_referent": "swim"}

  pres_req = get_presentation_request(schema_id, cred_def_id)
  pres = prover.prover_create_presentation(pres_req, self_attested_values)
  logging.info("The prover created presentation, pres: {}".format(json.dumps(pres)))
  # endregion end::CreatePresentation[]

  # region tag::VerifyPresentation[]
  v_result = verifier.verifier_verify_presentation(pres_req, pres)
  logging.info("The verifier verified the presentation, result: {}".format(v_result))
  assert v_result == True
  # endregion end::VerifyPresentation[]

  # region tag::RevokeCredential[]
  issuer.issuer_revoke_credential(cred_rev_id, cred_def_id)
  logging.info("The issuer revoked the credential")
  # endregion end::RevokeCredential[]

  pres = prover.prover_create_presentation(pres_req, self_attested_values)
  logging.info("The prover created the presentation, pres: {}".format(json.dumps(pres)))

  v_result = verifier.verifier_verify_presentation(pres_req, pres)
  logging.info("The verifier verified the presentation, result: {}".format(v_result))
  assert v_result == False


def demo_non_revocable():
  schema_name = "PythonSchemaNonRevocableV.0.3"
  attribute_set = ["name", "surname", "age", "gender"]
  schema_id = create_schema_if_not_exist(issuer, schema_name, attribute_set)

  tag = get_timestamp_tag()
  cred_def_id = create_credential_definition(issuer, schema_id, False, tag)
  logging.info("The issuer created credential definition for schema_id: {}, cred_def_id:{}".format(schema_id, cred_def_id))

  issuer_nonce = str(random.getrandbits(80))
  cred_offer = issuer.issuer_create_credential_offer(cred_def_id, issuer_nonce)
  logging.info("The Issuer created a credential offer for the prover with cred_def_id: {}, cred_offer:{}".format(cred_def_id, json.dumps(cred_offer)))

  cred_request = prover.prover_create_credential_request(cred_offer)
  logging.info("The prover create a credential request, cred_request: {}".format(cred_def_id, json.dumps(cred_request)))

  cred_values = generate_sample_cred_values(attribute_set)
  cred_info = issuer.issuer_create_credential(cred_request, cred_values, issuer_nonce)
  cred = cred_info["credential"]
  logging.info("The issuer created a credential, cred: {}".format(cred_def_id, json.dumps(cred)))

  store_cred = prover.prover_store_credential(None, cred)
  logging.info("The prover stored the credential, store_cred: {}".format(store_cred))

  self_attested_values = {"self_attested_referent": "swim"}
  pres_req = get_presentation_request(schema_id, cred_def_id)
  pres = prover.prover_create_presentation(pres_req, self_attested_values)
  logging.info("The prover created presentation, pres: {}".format(json.dumps(pres)))

  v_result = verifier.verifier_verify_presentation(pres_req, pres)
  logging.info("The verifier verified the presentation, result: {}".format(v_result))
  assert v_result == True


if __name__ == '__main__':
  logging.info("Demo with SQLite was started")

  issuer_password = test_utils.native_string("123456")
  issuer = create_nixar_agent_w_sqlite_wallet("python_issuer_w_sqlite", lambda: issuer_password, "ENDORSER")
  logging.info("Thw issuer agent was created")

  prover_password = test_utils.native_string("123456")
  prover = create_nixar_agent_w_sqlite_wallet("python_prover_w_sqlite", lambda: prover_password, None)
  logging.info("The holder agent was created")

  verifier_password = test_utils.native_string("123456")
  verifier = create_nixar_agent_w_sqlite_wallet("python_verifier_w_sqlite", lambda: verifier_password, None)
  logging.info("The verifier agent was created")

  demo_revocable()
  demo_non_revocable()

  # tag::changePassword[]
  logging.info("Prover Credential list: {}".format(json.dumps(prover.prover_get_credentials())))
  prover_new_password = test_utils.native_string("Nixar123456")
  prover.change_password(lambda: prover_new_password)
  prover_password = prover_new_password
  logging.info("Prover Credential list: {}".format(json.dumps(prover.prover_get_credentials())))
  # end::changePassword[]
