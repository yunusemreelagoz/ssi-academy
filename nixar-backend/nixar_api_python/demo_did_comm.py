import json
import logging

import test_utils
from nixar.nixar_api import NixarMessageType
from test_utils import create_nixar_agent_w_sqlite_wallet


def demo_did_comm():
  # Agent A create connection invitation

  # tag::GetInvitation[]
  inv_base64_seed = test_utils.encode_base64("00000000000000000000000000AGENTA")
  conn_inv = agent_a.connection_create_local_invitation("agent A", "http://localhost:8080", inv_base64_seed)
  logging.info("Agent A create connection invitation, conn_inv: {}".format(json.dumps(conn_inv)))
  # end::GetInvitation[]

  # tag::ConnectionCreateRequest[]
  # Agent B receive invitation and create connection request
  req_base64_seed = test_utils.encode_base64("00000000000000000000000000AGENTB")
  conn_req = agent_b.connection_create_request(conn_inv, req_base64_seed)
  logging.info("Agent B create connection request, conn_req: {}".format(json.dumps(conn_req)))
  # end::ConnectionCreateRequest[]

  # tag::ConnectionAcceptRequest[]
  # Agent A receive connection request and create connection response
  conn_res = agent_a.connection_accept_request(conn_req, None)
  logging.info("Agent A create connection response, conn_res: {}".format(json.dumps(conn_res)))
  # end::ConnectionAcceptRequest[]

  # tag::ConnectionAcceptResponse[]
  # Agent B receive connection response and finalize connection creation
  agent_b.connection_accept_response(conn_res)
  logging.info("Connection created between Agent A and Agent  B")
  # end::ConnectionAcceptResponse[]

  # Agent A Connections
  agent_a_conns = agent_a.connection_get_connections()
  logging.info("Agent A Connections {}".format(json.dumps(agent_a_conns)))
  assert len(agent_a_conns) == 1

  # Agent B Connections
  agent_b_conns = agent_b.connection_get_connections()
  logging.info("Agent B Connections{}".format(json.dumps(agent_b_conns)))
  assert len(agent_b_conns) == 1

  # Agent A Create Simpele Message
  from_did = agent_a_conns[0]["my_did"]
  their_did = agent_a_conns[0]["their_did"]
  message = "hello agent A"
  encrypted_message = agent_a.connection_encrypt(from_did, their_did, NixarMessageType.MESSAGE_TYPE_SIMPLE, message)
  logging.info("Agent A create message, encrypted_message:{}".format(json.dumps(encrypted_message)))

  # Agent B receive message and decrypt
  decrypted_message = agent_b.connection_decrypt(encrypted_message)
  logging.info("Agent B decrypt message, decrypted_message:{}".format(json.dumps(decrypted_message)))

  assert message == decrypted_message['content']


def demo_sign_and_verify():
  # tag::ProverSign[]
  # Sign and verify with did
  # agent_b get connections
  agent_b_conns = agent_b.connection_get_connections()
  from_did = agent_b_conns[0]["my_did"]
  their_did = agent_b_conns[0]["their_did"]

  data = "Data To Be Signed"
  signed_data = test_utils.encode_base64(data)
  logging.info("Data To Be Signed: {}".format(signed_data));
  base64_encoded_signature = agent_b.sign_with_did(from_did, signed_data)
  logging.info("Signature: {}".format(base64_encoded_signature));
  # end::ProverSign[]

  # tag::ProverEncryptMessage[]
  packed_signature = {}
  packed_signature['signedData'] = signed_data
  packed_signature['signature'] = base64_encoded_signature
  logging.info("Packed signature {}".format(packed_signature))
  encrypted_message = agent_b.connection_encrypt(from_did,
                                                 their_did,
                                                 NixarMessageType.MESSAGE_TYPE_SIMPLE,
                                                 packed_signature)
  logging.info("Agent B create message of signature info, encrypted_message: {}".format(encrypted_message))
  # end::ProverEncryptMessage[]

  # tag::IssuerDecryptMessageForVerification[]
  decrypted_message = agent_a.connection_decrypt(encrypted_message)
  logging.info("Agent A decrypt message, decrypted_message: {}".format(decrypted_message))
  unpacked_signature = json.loads(decrypted_message['content'])
  logging.info("Unpacked signature info: {}".format(unpacked_signature))
  # end::IssuerDecryptMessageForVerification[]

  # tag::IssuerVerifySignature[]
  # 1. verify with their did from connection.
  is_verified = agent_a.verify_signature_with_their_did(decrypted_message['senderDid'],
                                                        unpacked_signature['signedData'],
                                                        unpacked_signature['signature'])
  logging.info("Verification result with their did {}".format(is_verified))
  assert is_verified == True

  # 2. OR verify with their PUBLIC Key
  did_doc = agent_a.get_their_did_as_did_doc(decrypted_message['senderDid'])
  logging.info(did_doc)
  logging.info(did_doc['publicKeys'][0])
  is_verified = agent_b.verify_signature_with_did_public_key(did_doc['publicKeys'][0]['value'],
                                                             unpacked_signature['signedData'],
                                                             unpacked_signature['signature'])

  logging.info("Verification result with their PUBLIC Key {}".format(is_verified))
  assert is_verified == True

  # end::IssuerVerifySignature[]


def demo_local_did():
  base64_seed = test_utils.encode_base64("00000000000000000000000000000DID")
  local_did = agent_a.create_local_did(base64_seed)
  logging.info("Local did created {}".format(local_did))


if __name__ == '__main__':
  logging.info("Did Comm Demo was started")

  agent_a_password = test_utils.native_string("123456")
  agent_a = create_nixar_agent_w_sqlite_wallet("agent_a", lambda: agent_a_password, None)
  logging.info("The agent_a agent was created")

  agent_b_password = test_utils.native_string("123456")
  agent_b = create_nixar_agent_w_sqlite_wallet("agent_b", lambda: agent_b_password, None)
  logging.info("The agent_b agent was created")

  demo_did_comm()
  demo_sign_and_verify()
  demo_local_did()
