#include <stdbool.h>

typedef enum CredDefIssuanceType {
  ISSUANCE_BY_DEFAULT,
  ISSUANCE_ON_DEMAND,
} CredDefIssuanceType;

typedef enum NixarMessageType {
  MessageTypeSimple,
  MessageTypeCredentialOffer,
  MessageTypeCredentialRequest,
  MessageTypeCredential,
  MessageTypePresentationRequest,
  MessageTypePresentation,
  MessageTypeConnectionRequest,
  MessageTypeConnectionResponse,
} NixarMessageType;

typedef const char *NativeString;

typedef void (*ExternLogCallbackType)(unsigned int, NativeString);

typedef NativeString (*WalletPasswordCallback)(void);

typedef unsigned long long NixarAgentHandle;

#ifdef __cplusplus
#extern "C" {
#endif // __cplusplus

/**
 *
 * Create a local did and its keypair in the wallet
 *
 * # Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 * * `seed`: A 32 Characters long String that will be used as a SEED for generation of the keypair (OPTIONAL)
 * # Returns
 * The newly created did as a DidInfo
 *
 * # Example
 *
 * ```
 * const char *local_did = create_local_did(agent_handle, "000000000000000MyLovelyDid000001");
 * printf("%s", local_did);
 * ```
 * __Output__
 * ```
 * {
 *   "code": "OK",
 *   "value": {
 *     "id": "TDzjPekxmm8cmoiv6AbDWh",
 *     "metadata": null,
 *     "publicDID": false,
 *     "public_key": "FHzfPH62yMaTBZbVoBU9aTifW1u3wcB8B5jEcB4zNGzk",
 *     "seed": "4F7BsTMVPKFshM1MwLf6yJ1PgDXegnwCRCtUs4sotFsE"
 *   }
 * }
 * ```
 *
 */
NativeString create_local_did(NixarAgentHandle agent_handle,
                              NativeString seed);

NativeString change_password(NixarAgentHandle agent_handle,
                             WalletPasswordCallback wallet_password_callback);

/**
 *
 * Trustee agent register other agent to ledger, only trustee call this methods
 *
 * # Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 * * `registration_request`: A 32 Characters long String that will be used as a registration request info to register agent to ledger
 * # Returns
 *
 *
 * # Example
 *
 * ```
 * const char *reg_req_info="{
 *   "did": "EtJzMSvay4GA5ppKcs2Znv",
 *   "verkey": "8ZvScBiUdhhioQjTuKwxUc41UP9bdEDLSARirTykLD61",
 *   "role": "ENDORSER",
 *   "alias": "endorser_agent",
 * }"
 * const char *result = create_local_did(agent_handle, reg_req_info);
 * printf("%s", result);
 * ```
 * __Output__
 * ```
 * {
 *   "code": "OK"
 * }
 * ```
 *
 */
NativeString register_agent_to_ledger(NixarAgentHandle agent_handle,
                                      NativeString registration_request);

/**
 *
 * Set and update attribute of agent it is also submit attribute to ledger if the agent role is trustee or endorser or steward
 *
 *
 * # Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 * * `attr_name`: The name of attribute (MUST)
 * * `attr_value`: The value of attribute (MUST)
 *
 * # Example
 *
 * ```
 *  set_attribute(agent_handle, "endPoint", "192.168.1.1");
 *  printf("%s\n", schema_id);
 * ```
 * __Output__
 * ```
 * {
 *   "code": "OK"
 * }
 * ```
 *
 */
NativeString set_attribute(NixarAgentHandle agent_handle,
                           NativeString attr_name,
                           NativeString attr_value);

/**
 *
 * Gets the public invitation of this agent (possibly on the ledger)
 *
 *
 * # Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 * # Returns
 * The public invitation of this agent
 * # Example
 *
 * ```
 * const char *publ_inv = connection_get_public_invitation(agent_handle);
 * printf("%s", publ_inv);
 * ```
 * __Output__
 * ```
 * {
 *   "code": "OK",
 *   "value": {
 *     "did": "2GeokfvZby2r7KnaKJdsga",
 *     "endpoint": null,
 *     "label": "issuers public invitation",
 *     "recipient_keys": null
 *   }
 * }
 * ```
 *
 */
NativeString connection_get_public_invitation(NixarAgentHandle agent_handle);

/**
 *
 * Create local invitation (for local pairwise connections)
 *
 * # Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 * * `label`: A label for this invitation (MUST)
 * * `endpoint`: An endpoint for the connection (OPTIONAL)
 * * `seed`: an optional seed for to be used as a source for the pairwise did (Optional)
 *
 * # Example
 *
 * ```
 * const char *local_inv = connection_create_local_invitation(agent_handle, "my local invitation", "http://myserver/agent");
 * printf("%s", local_inv);
 * ```
 * __Output__
 * ```
 * {
 *   "code": "OK",
 *   "value": {
 *     "did": "W2JdUjYHFRy4fxqGJgewiK",
 *     "endpoint": "http://myserver/agent",
 *     "label": "my local invitation",
 *     "recipient_keys": "GpTZG6bAWEvdpas3c4UzUWQ49KRoDHPsmMRBg3t4Jd6u"
 *   }
 * }
 * ```
 *
 */
NativeString connection_create_local_invitation(NixarAgentHandle agent_handle,
                                                NativeString label,
                                                NativeString endpoint,
                                                NativeString seed);

/**
 *
 * Create a connection request for the invitation.
 *
 * The invitation must be received from another agent that we want to connect. It can be either
 * a public invitation or a local invitation.
 *
 *
 * # Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 * * `invitation`: The public or local invitation received from another agent (MUST)
 * * `seed`: an optional seed for to be used as a source for the pairwise did (Optional)
 *
 * # Returns
 * An encrypted connection request to be sent to the other agents `accept_connection_request` endpoint
 *
 * # Example
 *
 * ```
 * const char *invitation = "see connection_create_local_invitation or connection_get_public_invitation for a sample";
 * const char *request_message = connection_create_request(agent_handle, invitation, NULL);
 * printf("%s", request_message);
 * ```
 * __Output__
 * ```
 * {
 *   "code": "OK",
 *   "value": {
 *     "cipherText": "HL4uXa-kvuASd4lWDDWC_Cfk4e18deX76cBvrj-9AThN7LoJVr_n3BxRMaQfL4iCmd6YQDcvNFgCxuwIhveu-t-8TQOtxwuBvLEdxl-cUgwKUea3bbfMkTXFfR4aZy4KuzClw1oOhh1oay3jfxIaTd-K3uIcQUMLD4j3guY9drbMWeVIzZa_C-apTz0PznFWpZNZp7-zWzH5v1rP-q386Vo-n8LdNqj07kQuUdnJ07nV6-VfO2Ko15bWmJo1gWIJrBt1XICYRjFO2Z2mXfjwIruFPN5XpRvT-t6dEDpuOuIzonnCKchGEJmy-sb9qw208c1TqcOdFC4YVZNPdaAXxhmwa2HabzMHVtD0gs-xKrxPCG_yihf2LIAwe_vwN6GyGxge0dA11_4Kz93ArXhzwcTVwICfG6yf9WXWbu1xueuwjlamyUX7Xuohlw3la5c9uERNUGcebfrAdn0J-NIBOy7TxvUvQ7akOmj_ZBYmq06zsWCWKv5cDyzEVAkLdBBREFgIrqXPXZEoAdL69xFgY00b3Fs_1TcGNR8mP6KirPmk5Aof067KJjoyiOr0kk5Dnj9zvra2Pm8wn05bO8gcW6apiJBfjqneE20eWCyoPDfXiGDonjT6pURA1vVTyy6nVm-0ek2ZlPK-X-0ePwAWSZqKTXbiY5cVQfbZFDhlTpOi352NLOSFxyGG3ik6Bl2GwjK6ijdl48GtjTnhxTB3eyvMnHhlpvamX4dGakdozU65RMyitmRyh6VggZbzxkrkq5HN0hyK420XG8Z30e9ZYil8K4Wq2gv90ApUlqD1AC47zZ75PO1G651sqPZPgdinQ33ry6zi_0aPwxUNiGs2x4CCiUoR0kYStagBnyXkf4h1TJbqs70W4wNpKK8hw4DkWGSdgD_ymB2fW6mejg==",
 *     "iv": "3SoreBpSk2WdlmR2P0_CjFYYWBMjbirX",
 *     "protectedSender": "eyJlbmMiOiJ4Y2hhY2hhMjBwb2x5MTMwNV9pZXRmIiwidHlwIjoiSldNLzEuMCIsImFsZyI6IkFub25jcnlwdCIsInJlY2lwaWVudHMiOlt7ImVuY3J5cHRlZEtleSI6IlhMOG1XVHVHSzRiTFdZZlVSZ0g5WXE2cGpQWlJJMzlNZnpnVGpUSF9JeGhSeXdBbVg3X3cyaVdwbFFhczVfeXpQMFB5MjhiUFNLVHBMVkNEY1BvOEtWUFZtVjF2ZXJ2dGYxY09mb2NMRVJjPSIsImhlYWRlciI6eyJraWQiOiJIcHJudHZ2Y0huTnlWdzNFUG1DTVpocndtc2sycEdReThNdEFqVTVzZXhHTiIsInNlbmRlciI6bnVsbCwiaXYiOm51bGx9fV19",
 *     "tag": "hK-XVJYHBZ57G9S0ANypwA=="
 *   }
 * }
 * ```
 *
 */
NativeString connection_create_request(NixarAgentHandle agent_handle,
                                       NativeString invitation,
                                       NativeString seed);

/**
 *
 * Process (Accept) a connection request received from another agent.
 *
 * The request arrives as an encrypted json. The agent should be able to open
 * it via its previously created invitation
 *
 *
 * # Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 * * `request`: The encrypted connection request received from the other agent (MUST)
 *
 * # Returns
 * An encrypted connection response to be sent to the other agents `accept_connection_response` endpoint
 *
 * # Example
 *
 * ```
 * const char *request = "see connection_create_request for a sample";
 * const char *response_message = connection_accept_request(agent_handle, request);
 * printf("%s", response_message);
 * ```
 * __Output__
 * ```
 * {
 *   "code": "OK",
 *   "value": {
 *     "cipherText": "qLM969i9ZJP3esvnhDVYsXsNG89JN8HA85A-wA-miq5EJv5_oowvSW-SuEPO1Nz4uBmVaY9OD_727BU9zwGjlckvA-t56ihHzjgME2PLyeBgqELy5a8NL4K2-O5Kroc7P-gwEfEv4AytTRIk-kxzLGmcRD2L_AybAYwIFTVr7N6_OQL2XuhEJOBeMnkyOifETtxcJHIe2m4i1KidelBtW-epiY5aOGnwyBV7Y3aAnm1fLr63OkIPMuRe9x4Pg7NtaX26IXSzHIJaJkA8qWMyhwl27-965F1k6VaK0h4jPusjhw0UbA0WvLcq7Dwaj7l_gL66inErNM0FvLxuAu3dfLb8Xlva8grNW4grIeEp1L8be3SSgnebD5bFNTVB0pb02Jt7iipegnr3tz2LhAdR10b89nFhPC1jS20q3GcQl2t9he6r9DzR83mKTCk1vynyVdjUCSjfLKk8ylPbVnLlmVxAiv7pwloaJgcP8Km3sCng9CHgMzAfUfkV_zu_8O7_aaxxyRMaEBJ-IOVlVTquno387I3Fy6AIHmmns4ZHlCWfqXE5QfaTKFxmB4YpYxx6JY5J96aKtO7MC9mjHJGHtsQWLl86GiX_gHiyUg5eEAZGKLJM-tOpO7CtaWoqI0tderIMy6Opr89Aj7Ovb6rjl6Nh1zGQeVh-Fvqdxh2f-uKb6WqWT2htsGOeuNAsa6TVM3x9UO4wneDjqR2c-0HPfMVnFZwan6uZ4B6_yFxvkMu9q1U=",
 *     "iv": "ZncbO5ACF5IGQCoBeRgNiqMQFaRKTz0r",
 *     "protectedSender": "eyJlbmMiOiJ4Y2hhY2hhMjBwb2x5MTMwNV9pZXRmIiwidHlwIjoiSldNLzEuMCIsImFsZyI6IkFub25jcnlwdCIsInJlY2lwaWVudHMiOlt7ImVuY3J5cHRlZEtleSI6IjhxTXlHeXlSVGFjMjVVa25VWkZLclVYWTJxNGs1YjZUVVJEM0ZlVHBiVHpRdk83VjYwTnhNV2FRUmdYdE9iMXRaaTJlbXVXUEZmdEtTdldCbzlGazJiZjNyclVieHlDVEcxWXlBSllYclhNPSIsImhlYWRlciI6eyJraWQiOiJEbjlBdUdWZEpxb1MxNHVvV1BiS2RqcWN0U0ZQY1R5aTl5M2pRN2t0UVNwZSIsInNlbmRlciI6bnVsbCwiaXYiOm51bGx9fV19",
 *     "tag": "ZEWRlhCTK5wqV-gRkj7vPA=="
 *   }
 * }
 * ```
 *
 */
NativeString connection_accept_request(NixarAgentHandle agent_handle,
                                       NativeString message,
                                       NativeString alias);

/**
 *
 * Process (Accept) a connection response received from another agent.
 *
 * The request arrives as an encrypted json. The agent should be able to open
 * it via its previously created connection which is in pending state.
 * After this call, its pairwise connection is set to `active`.
 *
 *
 * # Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 * * `response`: The encrypted connection response received from the other agent (MUST)
 *
 * # Returns
 * Ok or Err
 *
 * # Example
 *
 * ```
 * const char *response = "see connection_accept_request for a sample";
 * const char *result = connection_accept_response(agent_handle, response);
 * printf("%s", result);
 * ```
 * __Output__
 * ```
 * {
 *   "code": "OK",
 *   "value": null
 * }
 * ```
 *
 */
NativeString connection_accept_response(NixarAgentHandle agent_handle, NativeString message);

/**
 *
 * Encrypt the given content (e.g. a json or a regular string).
 *
 * Encrypt and return an ancrypted Message json.
 * This function can be called __only after creating a successful connection__, because the underlying
 * connection object must exist in order to perform the `AutchCrypt` encryption for the receiving side
 *
 * # Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 * * `from_did`: The did value of the underlying connection (MUST)
 * * `message_type`: One of `NixarMessageType` enums (MUST) (see below)
 * * `content`: A string (MUST)
 *
 * # Returns
 * The encrypted message as json serialized Message object
 *
 * # NixarMessageType ENUM
 * ```
 * typedef enum NixarMessageType {
 *   MessageTypeSimple,
 *   MessageTypeCredentialOffer,
 *   MessageTypeCredentialRequest,
 *   MessageTypeCredential,
 *   MessageTypePresentationRequest,
 *   MessageTypePresentation,
 *   MessageTypeConnectionRequest,
 *   MessageTypeConnectionResponse,
 * } NixarMessageType;
 *```
 * # Example
 * ```
 * char* response = connection_encrypt(agent_handle, "E9Qh3yioe3aaGEYFxQHis2","J733GjadbHmXEPbXo1hgck" NixarMessageType.MessageTypeSimple, "Hello World");
 * printf("%s\n", response);
 * ```
 * __Output__
 * ```
 * {
 *   "code": "OK",
 *   "value": {
 *     "cipherText": "18oY-2XGQkuGog3TWnxbf0CzJQ7BWiZt79OgJROUDlFZrgPtvK2JM496d_vxKej_7_0sKxDH2iydr_fE0WHXCIMjbPyi8vCe8vHtM_14-wpUFpXuLCXjM4hQhoFuhMELFfIc7ePFWgDPBatsiwYCdg94Bwkp08w5Rgp5bVjweQsmUPOAyBj58ZvEaFuBsVF2K8Ba7tWP2VbCGoaLLw6GmoAju4vdNwQFTekfNTr-r_DRK8voWhCQNwACAg==",
 *     "iv": "LnnOBYo1p8KeWqpyIV7MzFdVXBfgi9HR",
 *     "protectedSender": "eyJlbmMiOiJ4Y2hhY2hhMjBwb2x5MTMwNV9pZXRmIiwidHlwIjoiSldNLzEuMCIsImFsZyI6IkF1dGhjcnlwdCIsInJlY2lwaWVudHMiOlt7ImVuY3J5cHRlZEtleSI6ImhYRDdKRlhNRTJMVlYtQXUwbHVkd1NRMzBiUk1IdnJ4VG9vekJoWTFiR3drRWF0QV9lckJ3MjlVeF9ES2t4YlkiLCJoZWFkZXIiOnsia2lkIjoiUTRyOEZhUW44NkJVQkJWbWRjYVFWMiIsInNlbmRlciI6IkFaLWJWLTR1Z3hWOWVQcmtkRm9aSW43N1hFSVBLUExKbGpQYldfLWdpbmNvRUJ6d1pBTnlEaFREdDhYdUphTnhDeHZFVXhJU0lnN0xiQjVPVDk2RXdsSkRVUi1sd1VtcU81UjVOeGwyQjRCNVN2cWNNUjc0dTdHV3VLcz0iLCJpdiI6InAwMDl4cFJodEhOejBtc3RTWDZxbm1LRWZnQlgzeDJlIn19XX0=",
 *     "tag": "UNU8Lcnqq38CZMXykhJ-IQ=="
 *   }
 * }
 * ```
 */
NativeString connection_encrypt(NixarAgentHandle agent_handle,
                                NativeString from_did,
                                NativeString to_did,
                                enum NixarMessageType message_type,
                                NativeString content);

/**
 *
 * Decrypt the given message.
 *
 * This method decrypts the given message that is packed in the json  string `message` and
 * returns a plain result.
 *
 * # Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 * * `message`: A string (possibly json) to be decrypted
 *
 * # Return
 * If the result code is OK, the `value` field contains the following data
 * * `T`: the content
 * * `The type of the message` (e.g. `NixarMessageType::MessageTypeSimple`)
 * * `The optional did value of the sending connection (i.e. from did)`
 *
 * # Example
 * ```
 * const char* encrypted = "see connection_encrypt for a sample";
 * const char* plain = connection_decrypt(agent_handle, encrypted);
 * printf("%s\n", plain);
 * ```
 * __Output__
 * ```json
 * {
 *   "code": "OK",
 *   "value": [
 *     "Hello Issuer",
 *     "MessageTypeSimple",
 *     "QSonmCLWwkLDQt5zMBpz2r"
 *   ]
 * }
 * ```
 *
 */
NativeString connection_decrypt(NixarAgentHandle agent_handle, NativeString message);

/**
 * # connection_get_connections
 * Get all the connections in the wallet
 * ## Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 *
 * ## Return
 * The connections as json or error with error code
 *
 * ## Example
 * ```
 * const char* conns = connection_get_connections(agent_handle);
 * printf("%s\n", conns);
 * ```
 * __Output__
 * ```
 * TODO: decorate with ApiResult
 * [{
 *   "my_did": "VxjUBPPwS856SJhBMMwXAb",
 *   "their_did": "S3irssVYqHQkXjniKVcsXH",
 *   "their_label": "Agent X",
 *   "invitation_key": "9TLxnVGVQ9DA5jmT2UUrKPaiRaocfuiDwjY39M21DDLy",
 *   "connection_state": "Active",
 *   "alias": "Agent X",
 *   "created_date_utc": 1619771445,
 * },
 * ...
 * ]
 */
NativeString connection_get_connections(NixarAgentHandle agent_handle);

/**
 *
 * Return a co
 *
 * #Create schema as an Issuer
 * create a schema with the given attributes and schema name and optionally the version.
 * The schema is registered to the ledger and then returned as a json string
 *
 * ## Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 * * `schema_name`: The name of the schema (MUST)
 * * `attribute_set`: A json sequence of attributes (MUST)
 * * `schema_version`: Optional version (Optional, default value is `"V1"`)
 * ## Return
 * The newly created schemas id
 *
 * ## Example
 * ```
 * const char *attributes = "[\"name\", \"gender\", \"age\"]";
 * const char* schema_id = issuer_create_schema(agent_handle, "mySchema", attributes, NULL);
 * printf("%s\n", schema_id);
 * ```
 * __Output__
 * ```
 * {"code":"OK","value":"Fm5yjeqpYZLyoG2RQqMcJN:2:myschema:2.0"}
 * ```
 *
 */
NativeString issuer_create_schema(NixarAgentHandle agent_handle,
                                  NativeString schema_name,
                                  NativeString attribute_set,
                                  NativeString schema_version);

/**
 * # issuer_get_schema
 * Get the schema with the given id from the wallet
 * ## Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 * * `schema_id`: The id of the schema (MUST)
 *
 * ## Return
 * The schema as json or error with error code
 *
 * ## Example
 * ```
 * const char *schema_id = "6qnvgJtqwK44D8LFYnV5Yf:2:mySchema:1.0.0";
 * const char* schema = issuer_get_schema(agent_handle, schema_id);
 * printf("%s\n", schema);
 * ```
 * __Output__
 * TODO: decorate with ApiResult
 * ```
 * {
 *   "id": "6qnvgJtqwK44D8LFYnV5Yf:2:mySchema:1.0.0",
 *   "name": "mySchema",
 *   "ver": "1.0",
 *   "version": "1.0",
 *   "attrNames": ["name", "gender", "age"]
 * }
 */
NativeString issuer_get_schema(NixarAgentHandle agent_handle, NativeString schema_id);

/**
 * # issuer_get_schemas
 * Get all the schemas created by this issuer
 * ## Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 *
 * ## Return
 * The schemas as json or error with error code
 *
 * ## Example
 * ```
 * const char* schemas = issuer_get_schemas(agent_handle);
 * printf("%s\n", schemas);
 * ```
 * __Output__
 * ```
 * TODO: decorate with ApiResult
 * [{
 *   "id": "6qnvgJtqwK44D8LFYnV5Yf:2:mySchema:1.0.0",
 *   "name": "mySchema",
 *   "ver": "1.0",
 *   "version": "1.0",
 *   "attrNames": ["name", "gender", "age"]
 * },
 * ...
 * ]
 */
NativeString issuer_get_schemas(NixarAgentHandle agent_handle);

/**
 *
 * #issuer_create_credential_definition
 * Create and store a credential definition. The public parts of the credential definition are
 * saved to the wallet and the ledger, the private parts are saved into the wallet, and its
 * id is __returned__
 *
 * ## Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 * * `schema_id`: The id of a previously created schema (MUST)
 * * `is_revokable`: bool,
 * * `issuance_type`: One of `CredDefIssuanceType`
 * ## Return
 * The newly created credential definition id
 *
 * ## Example
 * ```
 * let cred_def_id = issuer_create_credential_definition(agent_handle, "6qnvgJtqwK44D8LFYnV5Yf:2:mySchema:1.0.0", true, CredDefIssuanceType.ISSUANCE_BY_DEFAULT);
 * printf("%s\n", cred_def_id)
 * ```
 * __Output__
 * ```
 * {"code":"OK","value":"Fm5yjeqpYZLyoG2RQqMcJN:3:CL:121203:bilgem"}
 * ```
 *
 */
NativeString issuer_create_credential_definition(NixarAgentHandle agent_handle,
                                                 NativeString schema_id,
                                                 bool is_revocable,
                                                 enum CredDefIssuanceType issuance_type,
                                                 NativeString max_cred_num,
                                                 NativeString tag);

/**
 *#issuer_get_tail
 *
 * get a tail file obtained from an _issuer_
 *
 * ##Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 * * `rev_reg_id`: Revocation Registry Id (MUST)
 * ##Return
 *  tail.
 *
 * ##Example
 * ```
 * tail=issuer_get_tail(agent_handle, "EtJzMSvay4GA5ppKcs2Znv:4:EtJzMSvay4GA5ppKcs2Znv:3:CL:91:bilgem:CL_ACCUM:bilgem")
 * ```
 * __Output__
 * ```
 * {"code":"OK","value":[
 * "11",
 * "...",
 * "...",
 * ]}
 * ```
 *
 */
NativeString issuer_get_tail(NixarAgentHandle agent_handle,
                             NativeString rev_reg_id);

/**
 *
 * #issuer_get_credential_definition
 * Get a previously created credential definition as json definition by its value.
 *
 * ## Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 * * `cred_def_id`: The id of a previously created credential definition (MUST)
 * ## Return
 * The credential definition as json
 *
 * ## Example
 * ```
 * let cred_def = issuer_get_credential_definition(agent_handle, "6qnvgJtqwK44D8LFYnV5Yf:3:CL:9:bilgem");
 * printf("%s\n", cred_def)
 * ```
 * __Output__
 * ```
 *  {
 *   "code": "OK",
 *   "value": {
 *     "id": "Hex3ENS6ngTMAWHRDsKPHd:3:CL:122002:bilgem",
 *     "schemaId": "Hex3ENS6ngTMAWHRDsKPHd:2:myschema:2.0",
 *     "tag": "bilgem",
 *     "type": "CL",
 *     "value": {
 *       "primary": { ... },
 *       "revocation": { ... }
 *     }
 *   }
 * }
 * ```
 *
 */
NativeString issuer_get_credential_definition(NixarAgentHandle agent_handle,
                                              NativeString cred_def_id);

/**
 *
 * #issuer_get_credential_definitions
 * Get a previously created credential definitions as json sequence
 *
 * ## Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 * ## Return
 * Credential definitions created by this agent
 *
 * ## Example
 * ```
 * const *char cred_defs = issuer_get_credential_definitions(agent_handle);
 * printf("%s\n", cred_defs)
 * ```
 * __Output__
 * ```
 *  //TODO: put a list of cred defs json sample
 * ```
 *
 */
NativeString issuer_get_credential_definitions(NixarAgentHandle agent_handle);

NativeString issuer_get_credential_definitions_for_schema(NixarAgentHandle agent_handle,
                                                          NativeString schema_id);

/**
 *
 * #issuer_create_credential_offer
 * Create an offer to create a credential for another agent. i.e. offer someone else
 * a credential for a credential definition
 *
 * ##Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 * * `cred_def_id`: The id of a previously created credential definition (MUST)
 * ##Return
 * a credential offer as a json string
 * ##Example
 * ```
 * const *char offer_json = issuer_create_credential_offer(agent_handle, "6qnvgJtqwK44D8LFYnV5Yf:3:CL:9:bilgem");
 * printf("%s\n", offer_json)
 * ```
 * __Output__
 * ```
 *{
 *   "code": "OK",
 *   "value": {
 *     "cred_def_id": "Fm5yjeqpYZLyoG2RQqMcJN:3:CL:121203:bilgem",
 *     "key_correctness_proof": {"..":"..."},
 *     "nonce": "197020426501519101410150",
 *     "schema_id": "Fm5yjeqpYZLyoG2RQqMcJN:2:myschema:2.0"
 *   }
 * }
 * ```
 *
 */
NativeString issuer_create_credential_offer(NixarAgentHandle agent_handle,
                                            NativeString cred_def_id,
                                            NativeString nonce);

/**
 *
 * #issuer_create_credential
 * Create a credential based on the received credential request
 *
 * ##Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 * * `cred_request`: The id of a previously created credential definition (MUST)
 * * `cred_values`: The credential values that needs to be assigned to the credential (MUST)
 * ##Return
 * A credential offer as a json string and its revocation index (i.e. `cred_rev_index`)
 * ##Example
 * ```
 * const *char cred_values=r#"
 *
 * "#
 * const *char cred_request= "see prover_create_cred_request";
 * const *char credential_json = issuer_create_credential(agent_handle, cred_request, cred_values);
 * printf("%s\n", credential_json)
 * ```
 * __Output__
 * ```
 *{
 *   "code": "OK",
 *   "value": [
 *     {
 *       "cred_def_id": "Fm5yjeqpYZLyoG2RQqMcJN:3:CL:121203:bilgem",
 *       "values": {
 *         "age": {
 *           "encoded": "30",
 *           "raw": "30"
 *         },
 *         "gender": {
 *           "encoded": "1835101285",
 *           "raw": "male"
 *         },
 *         "name": {
 *           "encoded": "1701733747",
 *           "raw": "Mehmet"
 *         },
 *         "surname": {
 *           "encoded": "521660491122",
 *           "raw": "Öztürk"
 *         }
 *       },
 *       "..": "..."
 *     },
 *     "1"
 *   ]
 * }
 * ```
 * You can see that the second item of the result sequence is "1" which is the `cred_rev_index`
 *
 */
NativeString issuer_create_credential(NixarAgentHandle agent_handle,
                                      NativeString cred_request,
                                      NativeString cred_values,
                                      NativeString issuer_nonce);

/**
 * #issuer_revoke_credential
 * Revoke a credential with its index and cred def id
 *
 * ##Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 * * `cred_rev_index`: Credential revocation index (MUST)
 * * `cred_def_id`: The id of a previously created credential definition (MUST)
 *
 *
 * ##Return
 *  {"code":"OK","value":null}
 *
 * ##Example
 *
 * ```clang
 * const char* cred_rev_index="1"
 * const char* cred_def_id="Hex3ENS6ngTMAWHRDsKPHd:3:CL:122002:bilgem"
 * const char* res = issuer_revoke_credential(angent_handle, cred_rev_idx, cred_def_id)
 * printf("%s\n", res);
 * ```
 * __Output__
 * ```
 * {"code":"OK","value":null}
 * ```
 *
 */
NativeString issuer_revoke_credential(NixarAgentHandle agent_handle,
                                      NativeString cred_rev_index,
                                      NativeString cred_def_id);

/**
 *#prover_create_credential_request
 *
 * Create a credential request from the __offer__ that was received from the _issuer_
 *
 * ##Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 * * `cred_offer`: A credential offer json received from the issuer (MUST)
 *
 * ##Return
 *  A credential request json that should be sent to the issuer for creating the credential
 *
 * ##Example
 * ```
 * const char *cred_offer = "..."; //see issuer_create_credential_offer return value for an example
 * const char* cred_request = prover_create_credential_request(agent_handle, cred_offer);
 * printf("%s\n", cred_request);
 * ```
 * __Output__
 * ```
 * {
 *   "code": "OK",
 *   "value": {
 *     "blinded_ms": {
 *       "...": "..."
 *     },
 *     "blinded_ms_correctness_proof": {
 *       "...": "..."
 *     },
 *
 *     "cred_def_id": "Fm5yjeqpYZLyoG2RQqMcJN:3:CL:121203:bilgem",
 *     "nonce": "792700915379815013552009",
 *     "prover_did": "Cwxv9QpZ6UUH5EHrmuQmp6"
 *   }
 * }
 * ```
 *
 */
NativeString prover_create_credential_request(NixarAgentHandle agent_handle,
                                              NativeString cred_offer);

/**
 *#prover_store_credential
 *
 * Store a credential that was received from the _issuer_ into the wallet
 *
 * ##Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 * * `cred_id`: An optional id that you may want to assing to your credential (OPTIONAL)
 * * `credential`: A credential that was received from an _issuer_
 *
 * ##Return
 *  Ok.
 *
 * ##Example
 * ```
 * const char *credential = "..."; //see issuer_create_credential_offer return value for an example
 * const char *cred_id = "my_lovely_credential"; //optional, may be NULL
 * const char* result = prover_store_credential(agent_handle, cred_id, credential);
 * printf("%s\n", result);
 * ```
 * __Output__
 * ```
 * {"code":"OK","value":true}
 * ```
 *
 */
NativeString prover_store_credential(NixarAgentHandle agent_handle,
                                     NativeString cred_id,
                                     NativeString credential);

/**
 * # prover_get_credential
 * Get the schema with the given id from the wallet
 * ## Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 * * `cred_id`: The id of the credential (MUST)
 *
 * ## Return
 * The the credential as json or error with error code
 *
 * ## Example
 * ```
 * const char *cred_id = "989461a6-d13b-4e4a-afa2-7e7fb97355d4";
 * const char* credential = prover_get_credential(agent_handle, cred_id);
 * printf("%s\n", credential);
 * ```
 * __Output__
 * ```
 * {
 *       "cred_def_id": "RUMNHC7qLbwSwLw5okvexA:3:CL:19:bilgem",
 *       "rev_reg": {
 *         "accum": "21 11C3C7C6535C24C9B8392362649DBC19C4CD4AE9537206D6F53651FFF45F5E0DB 21 11D16FF51D1059061925D0DD0D1FEDB34D48A31A4E96ADCB6C6CC1371B650CE61 6 8086AAEE1037CA6D2DD2F87991FCC7DDDC6A4E136389D555F61AC31B7EBB3086 4 435CB1FE47300E8F4597A7455282B6821D9A514FB6C8082109A58C35966D0065 6 8CD9CDCD80681E82AC06DC85AE2B92FFEF2727FC66FF099153B3B93215379C25 4 48F8F3858A6D14E8528C0F740BD17803C9D3C91588B838545D3F85F13AE3058C"
 *       },
 *       "rev_reg_id": "RUMNHC7qLbwSwLw5okvexA:4:RUMNHC7qLbwSwLw5okvexA:3:CL:19:bilgem:CL_ACCUM:bilgem",
 *       "schema_id": "RUMNHC7qLbwSwLw5okvexA:2:myschema:2.0",
 *       "signature": {
 *         "p_credential": { ... },
 *         "r_credential": { ... }
 *       },
 *       "signature_correctness_proof": { ... },
 *       "values": {
 *         "age": {
 *           "encoded": "30",
 *           "raw": "30"
 *         },
 *         "gender": {
 *           "encoded": "1835101285",
 *           "raw": "male"
 *         },
 *         "name": {
 *           "encoded": "1701733747",
 *           "raw": "Mehme"
 *         },
 *         "surname": {
 *           "encoded": "521660491122",
 *           "raw": "Öztürk"
 *         }
 *       },
 *       "witness": { ... }
 *     }
 */
NativeString prover_get_credential(NixarAgentHandle agent_handle,
                                   NativeString cred_id);

/**
 * # prover_get_credentials
 * Get all the credential created by this issuer
 * ## Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 *
 * ## Return
 * The credentials as json or error with error code
 *
 * ## Example
 * ```
 * const char* credentials = prover_get_credentials(agent_handle, schema_id);
 * printf("%s\n", credentials);
 * ```
 * __Output__
 * ```
 * TODO: decorate with ApiResult
 * [{
 *       "cred_def_id": "RUMNHC7qLbwSwLw5okvexA:3:CL:19:bilgem",
 *       "rev_reg": {
 *         "accum": "21 11C3C7C6535C24C9B8392362649DBC19C4CD4AE9537206D6F53651FFF45F5E0DB 21 11D16FF51D1059061925D0DD0D1FEDB34D48A31A4E96ADCB6C6CC1371B650CE61 6 8086AAEE1037CA6D2DD2F87991FCC7DDDC6A4E136389D555F61AC31B7EBB3086 4 435CB1FE47300E8F4597A7455282B6821D9A514FB6C8082109A58C35966D0065 6 8CD9CDCD80681E82AC06DC85AE2B92FFEF2727FC66FF099153B3B93215379C25 4 48F8F3858A6D14E8528C0F740BD17803C9D3C91588B838545D3F85F13AE3058C"
 *       },
 *       "rev_reg_id": "RUMNHC7qLbwSwLw5okvexA:4:RUMNHC7qLbwSwLw5okvexA:3:CL:19:bilgem:CL_ACCUM:bilgem",
 *       "schema_id": "RUMNHC7qLbwSwLw5okvexA:2:myschema:2.0",
 *       "signature": {
 *         "p_credential": { /// },
 *         "r_credential": { /// },
 *       "signature_correctness_proof": { /// },
 *       "values": {
 *         "age": {
 *           "encoded": "30",
 *           "raw": "30"
 *         },
 *         "gender": {
 *           "encoded": "1835101285",
 *           "raw": "male"
 *         },
 *         "name": {
 *           "encoded": "1701733747",
 *           "raw": "Mehme"
 *         },
 *         "surname": {
 *           "encoded": "521660491122",
 *           "raw": "Öztürk"
 *         }
 *       },
 *       "witness": { /// }
 *     },
 *  ...
 * ]
 */
NativeString prover_get_credentials(NixarAgentHandle agent_handle);

/**
 *#prover_store_tail
 *
 * Store a tail file obtained from an _issuer_
 *
 * ##Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 * * `rev_reg_id`: Revocation Registry Id (MUST)
 * * `tail_json`: A json string (containing a sequence of base58 encoded string) (MUST)
 * ##Return
 *  Ok.
 *
 * ##Example
 * ```
 * TODO:
 * ```
 * __Output__
 * ```
 * {"code":"OK","value":true}
 * ```
 *
 */
NativeString prover_store_tail(NixarAgentHandle agent_handle,
                               NativeString rev_reg_id,
                               NativeString tail);

/**
 *
 * Fetch all credential infos which's attributes name match with requested attribute and requested predicate in _Presentation Request_ received from _verifier_
 *
 * # Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 * * `presentation_request`: Presentation Request (MUST)
 * # Return
 * Presentation as json
 *
 * # Examples
 * ```
 * const char *presentation_request = "{
 *   "code": "OK",
 *   "value": {
 *     "name": "IdPR",
 *     "non_revoked": null,
 *     "nonce": "1108056213536999145798231",
 *     "requested_attributes": {
 *       "attribute1_referent": {
 *         "name": "name",
 *         "non_revoked": null,
 *         "restrictions": null
 *       },
 *       "attribute2_referent": {
 *         "name": "surname",
 *         "non_revoked": null,
 *         "restrictions": null
 *       },
 *       "attribute3_referent": {
 *         "name": "gender",
 *         "non_revoked": null,
 *         "restrictions": null
 *       }
 *     },
 *     "requested_predicates": {
 *       "predicate1_referent": {
 *         "name": "age",
 *         "non_revoked": null,
 *         "p_type": ">=",
 *         "p_value": 10,
 *         "restrictions": null
 *       }
 *     },
 *     "ver": "2.0",
 *     "version": "2.0"
 *   }
 * }"; //received from verifier
 * const char* result = prover_create_presentation(agent_handle, presentation_request);
 * printf("%s\n", result);
 * ```
 * __Output:__
 * ```
 *{
 *   "code": "OK",
 *   "value": {
 *     "attribute1_referent": [
 *       {
 *         "attrs": {
 *           "age": "30",
 *           "gender": "male",
 *           "name": "Mehme",
 *           "surname": "Öztürk"
 *         },
 *         "cred_def_id": "4fVPTarumDm9eFCcx3oSfg:3:CL:27:bilgem",
 *         "cred_rev_id": "1",
 *         "referent": "f31393ee-1920-4d91-a6a4-30d5fdc6add4",
 *         "rev_reg_id": "4fVPTarumDm9eFCcx3oSfg:4:4fVPTarumDm9eFCcx3oSfg:3:CL:27:bilgem:CL_ACCUM:bilgem",
 *         "schema_id": "4fVPTarumDm9eFCcx3oSfg:2:myschema:2.0"
 *       }
 *     ],
 *     "attribute2_referent": [
 *       {
 *         "attrs": {
 *           "age": "30",
 *           "gender": "male",
 *           "name": "Mehme",
 *           "surname": "Öztürk"
 *         },
 *         "cred_def_id": "4fVPTarumDm9eFCcx3oSfg:3:CL:27:bilgem",
 *         "cred_rev_id": "1",
 *         "referent": "f31393ee-1920-4d91-a6a4-30d5fdc6add4",
 *         "rev_reg_id": "4fVPTarumDm9eFCcx3oSfg:4:4fVPTarumDm9eFCcx3oSfg:3:CL:27:bilgem:CL_ACCUM:bilgem",
 *         "schema_id": "4fVPTarumDm9eFCcx3oSfg:2:myschema:2.0"
 *       }
 *     ],
 *     "attribute3_referent": [
 *       {
 *         "attrs": {
 *           "age": "30",
 *           "gender": "male",
 *           "name": "Mehme",
 *           "surname": "Öztürk"
 *         },
 *         "cred_def_id": "4fVPTarumDm9eFCcx3oSfg:3:CL:27:bilgem",
 *         "cred_rev_id": "1",
 *         "referent": "f31393ee-1920-4d91-a6a4-30d5fdc6add4",
 *         "rev_reg_id": "4fVPTarumDm9eFCcx3oSfg:4:4fVPTarumDm9eFCcx3oSfg:3:CL:27:bilgem:CL_ACCUM:bilgem",
 *         "schema_id": "4fVPTarumDm9eFCcx3oSfg:2:myschema:2.0"
 *       }
 *     ],
 *     "predicate1_referent": [
 *       {
 *         "attrs": {
 *           "age": "30",
 *           "gender": "male",
 *           "name": "Mehme",
 *           "surname": "Öztürk"
 *         },
 *         "cred_def_id": "4fVPTarumDm9eFCcx3oSfg:3:CL:27:bilgem",
 *         "cred_rev_id": "1",
 *         "referent": "f31393ee-1920-4d91-a6a4-30d5fdc6add4",
 *         "rev_reg_id": "4fVPTarumDm9eFCcx3oSfg:4:4fVPTarumDm9eFCcx3oSfg:3:CL:27:bilgem:CL_ACCUM:bilgem",
 *         "schema_id": "4fVPTarumDm9eFCcx3oSfg:2:myschema:2.0"
 *       }
 *     ]
 *   }
 * }
 *
 */
NativeString prover_fetch_credential_for_presentation_request(NixarAgentHandle agent_handle,
                                                              NativeString presentation_request);

/**
 *
 * Create a presentation from the _Presentation Request_ received from a _verifier_
 *
 * # Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 * * `presentation_request`: Presentation Request (MUST)
 * * `self_attested_values`: Self Attested Values
 * # Return
 * Presentation as json
 *
 * # Examples
 * ```
 * const char *presentation_request = "{
 *   "code": "OK",
 *   "value": {
 *     "name": "IdPR",
 *     "non_revoked": null,
 *     "nonce": "1108056213536999145798231",
 *     "requested_attributes": {
 *       "attribute1_referent": {
 *         "name": "name",
 *         "non_revoked": null,
 *         "restrictions": null
 *       },
 *       "attribute2_referent": {
 *         "name": "surname",
 *         "non_revoked": null,
 *         "restrictions": null
 *       },
 *       "attribute3_referent": {
 *         "name": "gender",
 *         "non_revoked": null,
 *         "unrevealed": false
 *         "restrictions": null
 *       },
 *       "attribute4_referent": {
 *         "name": "midle_name",
 *         "non_revoked": null,
 *         "restrictions": null
 *       },
 *       "attribute5_referent": {
 *         "name": "hobby",
 *         "non_revoked": null,
 *         "restrictions": null
 *       }
 *     },
 *     "requested_predicates": {
 *       "predicate1_referent": {
 *         "name": "age",
 *         "non_revoked": null,
 *         "p_type": ">=",
 *         "p_value": 10,
 *         "restrictions": null
 *       }
 *     },
 *     "ver": "2.0",
 *     "version": "2.0"
 *   }
 * }";
 *
 * const char *self_attested_values = "{
 *   "code": "OK",
 *   "value": {
 *     "attribute4_referent": "berke",
 *     "attribute5_referent": "chess"
 *   }
 * }"; //received from verifier
 * const char* result = prover_create_presentation(agent_handle, presentation_request);
 * printf("%s\n", result);
 * ```
 * __Output:__
 * ```
 * {
 *  "code": "OK",
 *  "value": {
 *    "identifiers": [
 *      {
 *        "cred_def_id": "Fm5yjeqpYZLyoG2RQqMcJN:3:CL:121203:bilgem",
 *        "rev_reg_id": "Fm5yjeqpYZLyoG2RQqMcJN:4:Fm5yjeqpYZLyoG2RQqMcJN:3:CL:121203:bilgem:CL_ACCUM:bilgem",
 *        "schema_id": "Fm5yjeqpYZLyoG2RQqMcJN:2:myschema:2.0",
 *        "timestamp": 1617889206
 *      }
 *    ],
 *    "proof": {
 *      "aggregated_proof": "too long skipped",
 *      "proofs": ["too long skipped"]
 *    },
 *    "requested_proof": {
 *      "predicates": {
 *        "predicate1_referent": {
 *          "sub_proof_index": 0
 *        }
 *      },
 *      "revealed_attrs": {
 *        "attribute1_referent": {
 *          "encoded": "1701733747",
 *          "raw": "Mehme",
 *          "sub_proof_index": 0
 *        },
 *        "attribute2_referent": {
 *          "encoded": "521660491122",
 *          "raw": "Öztürk",
 *          "sub_proof_index": 0
 *        },
 *        "attribute3_referent": {
 *          "encoded": "1835101285",
 *          "raw": "male",
 *          "sub_proof_index": 0
 *        }
 *      },
 *      "self_attested_attrs": {"attribute4_referent":"berke","attribute5_referent":"chess"},
 *      "unrevealed_attrs": {"attribute3_referent":{"sub_proof_index":0}}
 *    }
 *  }
 *}
 * ```
 *
 */
NativeString prover_create_presentation(NixarAgentHandle agent_handle,
                                        NativeString presentation_request,
                                        NativeString self_attested_values);

/**
 * # verifier_verify_presentation
 *
 * Verify a __proof presentation__ received from the _prover_
 *
 * ## Parameters
 * * `agent_handle`: The native handle created by `init_agent` call (MUST)
 * * `presentation_request`: Proof request that the verifier (this agent) created (MUST)
 * * `presentation`: Proof presentation that was created by the prover (MUST)
 * ## Return
 *  Ok.
 *
 * ## Example
 * ```
 * const char *presentation_request = "//created manually by the business layer, see nixar docs";
 * const char *presentation = "//see prover_create_presentation example output";
 * const char* result = verifier_verify_presentation(agent_handle, presentation_request, presentation);
 * printf("%s\n", result);
 * ```
 * __Output__
 * ```
 * {"code":"OK","value":true}
 * ```
 *
 */
NativeString verifier_verify_presentation(NixarAgentHandle agent_handle,
                                          NativeString presentation_request,
                                          NativeString presentation);

/**
 * # sign_with_did
 * Sign the given data (encoded as `base64` in `data_base64`) with
 * the private key of the `did` that exists in my wallet.
 *
 * This did is usually the __my did__ of a pairwise connection.
 *
 * ## Parameters
 * * `agent_handle`: The agent handle
 * * `did`: The `DID` of the pairwise connection
 * * `data_base64`: The data to be signed
 * ## Return
 * The return value is an SDK result containing the
 * base 64 encoded signature
 *
 *
 */
NativeString sign_with_did(NixarAgentHandle agent_handle,
                           NativeString did,
                           NativeString data_base64);

/**
 *
 * # verify_with_their_did
 * Given the signed data, the signature and the DID of the signer,
 * resolves the Did Document from the pairwise connection and using the
 * `public key` of the sender, verifies the signature
 *
 * # Parameters
 * * agent_handle: The native handle of the agent object
 * * their_did: The pairwise DID of the sender
 * * data_base64: Base64 encoded data that has been signed
 * * signatre_base64: Base64 encoded signature
 *
 * # Returns
 *
 * The result of the verification (boolean value `true/false`) as and SDK Result
 *
 */
NativeString verify_with_their_did(NixarAgentHandle agent_handle,
                                   NativeString their_did,
                                   NativeString data_base64,
                                   NativeString signature_base64);

/**
 *
 * # verify_with_did_public_key
 * Given the signed data, the signature and the DID of the signer,
 * and the public key of the signer, perform a signature verification directly
 *
 * # Parameters
 * * agent_handle: The native handle of the agent object
 * * did_public_key_base58: **Base 58** encoded PUBLIC KEY of the signer
 * * data_base64: Base64 encoded data that has been signed
 * * signatre_base64: Base64 encoded signature
 *
 * # Returns
 *
 * The result of the verification (boolean value `true/false`) as and SDK Result
 *
 */
NativeString verify_with_did_public_key(NixarAgentHandle agent_handle,
                                        NativeString did_public_key_base58,
                                        NativeString data_base64,
                                        NativeString signature_base64);

/**
 *
 * # get_their_did_as_did_doc
 * Given the pairwise `did` of the other side of the connection,
 * return the `DIDDocument` of the sender, which contains the following data:
 *
 * ```
 * DidDoc {
 *    public_keys: List<DidPublicKey>
 *    services: List<Service>,
 *    authentications: Vec<String>,
 *    id: String,
 *    context: String, // = "https://w3id.org/did/v1",
 * },
 * ```
 * and A `DidPublicKey` is as follows
 * ```
 * DidPublicKey {
 *    did: String,
 *    id: String,
 *    ///base 58 encoded public key
 *    value: String,
 *    pkType: PublicKeyType,
 *    controller: String,
 *    authn: bool, //= false,
 * }
 * ```
 * and the `PublicKeyType` resolves to `ED25519SIG2018`.
 *
 * # Parameters
 * * agent_handle: The native handle of the agent object
 * * their_did: The pairwise DID of the sender
 *
 * # Returns
 * The resolved `DidDocument` of the pairwise connection
 *
 */
NativeString get_their_did_as_did_doc(NixarAgentHandle agent_handle, NativeString their_did);

/**
 *
 * # get_did_info
 * Given the `did` return the `DIDInfo` assoicated.
 *
 * ```
 * pub struct DIDInfo {
 *    pub id: String,
 *    pub public_key: String,
 *    pub seed: Option<String>,
 *    #[serde(rename = "publicDID")]
 *    pub publicDID: bool,
 *    pub metadata: Option<HashMap<String, String>>,
 * }
 *
 * # Parameters
 * * agent_handle: The native handle of the agent object
 * * did: The did for the DIDInfo
 *
 * # Returns
 * The resolved `DIDInfo`
 *
 */
NativeString get_did_info(NixarAgentHandle agent_handle, NativeString did);

/**
 *
 * # get_connection_by_my_did
 * Given `my_did` return the associated `Connection` or null.
 *
 * ```#[derive(Serialize, Deserialize, Debug, PartialEq, Clone)]
 * pub struct Connection {
 *    pub my_did: Option<String>,
 *    pub their_did: Option<String>,
 *    pub their_label: Option<String>,
 *    pub their_role: Option<String>,
 *    //bs58 encoded public key
 *    pub invitation_key: String,
 *    pub connection_state: ConnectionState,
 *    pub alias: Option<String>,
 *    pub created_date_utc: u64,//timestamp
 * }
 *```
 *
 * # Parameters
 * * agent_handle: The native handle of the agent object
 * * my_did: The did for the Connection
 *
 * # Returns
 * The resolved `Connection` or null
 *
 */
NativeString get_connection_by_my_did(NixarAgentHandle agent_handle, NativeString my_did);

/**
 *
 * # get_connection_by_their_did
 * Given `their_did` return the associated `Connection` or null.
 *
 * ```#[derive(Serialize, Deserialize, Debug, PartialEq, Clone)]
 * pub struct Connection {
 *    pub my_did: Option<String>,
 *    pub their_did: Option<String>,
 *    pub their_label: Option<String>,
 *    pub their_role: Option<String>,
 *    //bs58 encoded public key
 *    pub invitation_key: String,
 *    pub connection_state: ConnectionState,
 *    pub alias: Option<String>,
 *    pub created_date_utc: u64,//timestamp
 * }
 *```
 *
 * # Parameters
 * * agent_handle: The native handle of the agent object
 * * their_did: The did for the Connection
 *
 * # Returns
 * The resolved `Connection` or null
 *
 */
NativeString get_connection_by_their_did(NixarAgentHandle agent_handle, NativeString their_did);

/**
 *
 * # get_connection_by_alias
 * Given `alias` return the associated `Connection` or null.
 *
 * ```#[derive(Serialize, Deserialize, Debug, PartialEq, Clone)]
 * pub struct Connection {
 *    pub my_did: Option<String>,
 *    pub their_did: Option<String>,
 *    pub their_label: Option<String>,
 *    pub their_role: Option<String>,
 *    //bs58 encoded public key
 *    pub invitation_key: String,
 *    pub connection_state: ConnectionState,
 *    pub alias: Option<String>,
 *    pub created_date_utc: u64,//timestamp
 * }
 *```
 *
 * # Parameters
 * * agent_handle: The native handle of the agent object
 * * alias: The alias for the Connection
 *
 * # Returns
 * The resolved `Connection` or null
 *
 */
NativeString get_connection_by_alias(NixarAgentHandle agent_handle, NativeString alias);

/**
 *
 * # get_connection_by_label
 * Given `label` return the associated `Connection` or null.
 *
 * ```#[derive(Serialize, Deserialize, Debug, PartialEq, Clone)]
 * pub struct Connection {
 *    pub my_did: Option<String>,
 *    pub their_did: Option<String>,
 *    pub their_label: Option<String>,
 *    pub their_role: Option<String>,
 *    //bs58 encoded public key
 *    pub invitation_key: String,
 *    pub connection_state: ConnectionState,
 *    pub alias: Option<String>,
 *    pub created_date_utc: u64,//timestamp
 * }
 *```
 *
 * # Parameters
 * * agent_handle: The native handle of the agent object
 * * label: The label for the Connection
 *
 * # Returns
 * The resolved `Connection` or null
 *
 */
NativeString get_connection_by_label(NixarAgentHandle agent_handle, NativeString label);

/**
 *
 * Create and initialize, or open and initialize the agent
 *
 * # Parameters
 * * `agent_init_params`: The initial data and the agent specific information (MUST)
 * * `password_callback`: A callback that requests password from the user in order to access
 * the sensitive data in the wallet (MUST)
 *
 * If the agent is created/opened successfully and initialization result json is returned.
 * The data structure is as follows
 * ```
 * typedef struct _InitAgentResult {
 *   NixarAgentHandle handle,
 * } InitAgentResult, *PInitAgentResult;
 * ```
 * The handle value will then be used throughout the entire api as `agent_handle`
 * (the first parameter of almost all the functions)
 *
 * # Example
 * ``` SQLite Wallet
 * const char* agent_init_params {
 *   "alias": "NixarAgent",
 *   "role": null, # (Optional, may also be "ENDORSER" or "TRUSTEE)
 *   "seed": null,  # (may also be seed)
 *   "genesis_path": "../genesis.txn",
 *   "wallet_init_params": {
 *     "sqlite_init_params": {
 *       "wallet_name": "NixarAgent" # database name
 *     }
 *   }
 * }
 * ```
 * ``` PostgreSQL Wallet
 * const char* agent_init_params {
 *   "alias": "NixarAgent",
 *   "role": null, # (Optional, may also be "ENDORSER" or "TRUSTEE)
 *   "seed": null,  # (may also be seed)
 *   "genesis_path": "../genesis.txn",
 *   "wallet_init_params": {
 *     "postgres_init_params": {
 *       "db_host": "localhost", # database host
 *       "db_username": "nixar", # database user name
 *       "db_password": "123456", # database user name's password
 *       "wallet_name": "NixarAgent" # database name
 *     }
 *   }
 * }
 * ```
 *
 * __Output__
 * ```
 * {
 *   "code": "OK",
 *   "value": {
 *     "handle": 1453
 *    }
 * }
 * ```
 * # Remarks
 * If the agent cannot be created, please check out the error code.
 *
 * When you want to create the agent with a role (e.g. TRUSTEE or ENDORSER),
 * nixar will try to check if its public did exists in the ledger, if not, then
 * it will return an error with error code <span style="color:red">`AgentNotRegistered`</span>. In that case
 * the error message will contain a Json string that includes the `did` which
 * must afterwards be registered to the ledger by another agent that has
 * a ___TRUSTEE___ role in that ledger.
 * The error message that implies this is a follows:
 * ```
 * {
 *   "code": "AgentNotRegistered",
 *   "value": "{\"did\":\"PMGeMibQPrstdhRBh7Nawy\",\"verkey\":\"DBWeCvxv7fYAAya7yqXH2yLt3YqEp2eoHp15zpgUL3NH\"}"
 * }
 * ```
 *
 * After the trustee has registered your agent, you can start/init it without a problem.
 *
 * If the error code is someting other than <span style="color:red">`AgentNotRegistered`</span> then you should seek for other issues.
 *
 *
 */
NativeString create_agent(NativeString agent_init_params,
                          WalletPasswordCallback wallet_password_callback);

/**
 *
 * Open an existing agent and
 *
 * # Parameters
 * * `agent_alias`: The alias of the agent you want to open (MUST)
 * * `genesis_path`: The initial data and the agent specific information (MUST)
 * * `password_callback`: A callback that requests password from the user in order to access
 * the sensitive data in the wallet (MUST)
 *
 * If the agent is opened successfully and initialization result json is returned.
 * The data structure is as follows
 * ```
 * typedef struct _InitAgentResult {
 *   NixarAgentHandle handle,
 * } InitAgentResult, *PInitAgentResult;
 * ```
 * The handle value will then be used throughout the entire api as `agent_handle`
 * (the first parameter of almost all the functions)
 *
 * # Example
 * ```
 * const char* alias= "issuer_agent",
 * const char* genesis_path= "./tests/genesis-bcovrin.txn",
 * ```
 * __Output__
 * ```
 * {
 *   "code": "OK",
 *   "value": {
 *     "handle": 1453
 *    }
 * }
 * ```
 * # Remarks
 * If the agent cannot be created, please check out the error code.
 *
 * When you want to create the agent with a role (e.g. TRUSTEE or ENDORSER),
 * nixar will try to check if its public did exists in the ledger, if not, then
 * it will return an error with error code <span style="color:red">`AgentNotRegistered`</span>. In that case
 * the error message will contain a Json string that includes the `did` which
 * must afterwards be registered to the ledger by another agent that has
 * a ___TRUSTEE___ role in that ledger.
 * The error message that implies this is a follows:
 * ```
 * {
 *   "code": "AgentNotRegistered",
 *   "value": "{\"did\":\"PMGeMibQPrstdhRBh7Nawy\",\"verkey\":\"DBWeCvxv7fYAAya7yqXH2yLt3YqEp2eoHp15zpgUL3NH\"}"
 * }
 * ```
 *
 * After the trustee has registered your agent, you can start/init it without a problem.
 *
 * If the error code is someting other than <span style="color:red">`AgentNotRegistered`</span> then you should seek for other issues.
 *
 *
 */
NativeString open_agent(NativeString agent_alias,
                        WalletPasswordCallback wallet_password_callback);

/**
 *
 * initialize logging level.
 *
 * 0 is off
 *
 * 1 is ERR
 *
 * 2 is warn
 *
 * 3 is info
 *
 * 4 is debug
 *
 * 5 and more is trace
 *
 * `callback` should be function pointer that takes an unsigned int (level) and a const char * (log message)
 *
 * ## Example
 *  ```
 * unsigned int level=3;
 *
 * void log_message(int level, const char* log_message){
 *   printf("%d %s", level, log_message);
 * }
 *
 * init_logging(level, log_message);
 *
 * ```
 * In platforms like Java you can bind it to a logging framework
 *
 */
NativeString init_logging(unsigned int level,
                          ExternLogCallbackType callback);

/**
 *
 * Set nixar home path for all agents.
 *
 * # Parameters
 * * `local_dir`: The **absolute** file path.
 *
 * # Example
 * ```
 * const *char path = "/home/yerlibilgin/myAgentFilesLocation"
 * set_nixar_home_path(char_path);
 * ```
 *
 */
NativeString set_nixar_home_path(NativeString local_dir);

/**
 * Explain the detail of the given code
 *
 * # Parameters
 * * `error_code`: The code that returned by the API in an error case
 *
 * # Return
 * The detailed description of the error
 *
 * # Example
 *
 * ```
 * const *char some_code = "WalletLoginFailed"
 * printf("%s", some_code, explaing_error_code(some_code));
 * ```
 * __Output__
 * ```
 * {
 *   "code": "OK",
 *   "value": {
 *       "code": "WalletLoginFailed",
 *       "description":"Cannot access the wallet, is the pin correct?"
 *    }
 * }
 * ```
 */
NativeString explain_error_code(NativeString error_code);

#ifdef __cplusplus
#} // extern "C"
#endif // __cplusplus
