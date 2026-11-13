# GitHub Settings - Secrets

WINDOWS_CERT_PFX_BASE64
Value: <base64-encoded PFX certificate>

WINDOWS_CERT_PASSWORD
Value: <certificate password>

WINDOWS_CERT_THUMBPRINT
Value: <certificate thumbprint>

AZURE_TENANT_ID
Value: <azure-tenant-id>

AZURE_CLIENT_ID
Value: <azure-client-id>

AZURE_CLIENT_SECRET
Value: <azure-client-secret>

AZURE_TRUSTED_SIGNING_ENDPOINT
Value: <azure-trusted-signing-endpoint>

AZURE_TRUSTED_SIGNING_ACCOUNT_NAME
Value: <trusted-signing-account-name>

AZURE_TRUSTED_SIGNING_CERT_PROFILE_NAME
Value: <trusted-signing-profile-name>

AZURE_TRUSTED_SIGNING_POLICY
Value: <optional-policy>

ROOT_CA_CERT_PATH
Value: <path-to-root-ca-cert>

ROOT_CA_CHAIN_PATH
Value: <path-to-root-ca-chain>

MTLS_CLIENT_CERT_PATH
Value: <path-to-mtls-client-cert>

MTLS_CLIENT_CERT_PASSWORD
Value: <mtls-client-cert-password>

MTLS_CA_BUNDLE_PATH
Value: <path-to-mtls-ca-bundle>

BYO_PKI_CONFIG_PATH
Value: <path-to-byo-pki-config>

FIPS1403_HSM_MODULE_PATH
Value: <path-to-fips1403-module>

FIPS1403_KEY_LABEL
Value: <key-label>

NIAPC_NATO_PKI_PROFILE
Value: <niapc-nato-profile>

HSM_TOKEN
Value: <hsm-token>

HSM_KEY_ID
Value: <hsm-key-id>

WHQL_SIGNING_CERT_PATH
Value: <path-to-whql-cert>

WHQL_SIGNING_PASSWORD
Value: <whql-cert-password>

HLK_SIGNING_CERT_PATH
Value: <path-to-hlk-cert>

HLK_SIGNING_PASSWORD
Value: <hlk-cert-password>

ELAM_POLICY_SIGNING_CERT_PATH
Value: <path-to-elam-cert>

ELAM_POLICY_SIGNING_CERT_PASSWORD
Value: <elam-cert-password>

PPL_SIGNING_CERT_PATH
Value: <path-to-ppl-cert>

PPL_SIGNING_CERT_PASSWORD
Value: <ppl-cert-password>

MVI_SIGNING_CERT_PATH
Value: <path-to-mvi-cert>

MVI_SIGNING_CERT_PASSWORD
Value: <mvi-cert-password>

NSA_TYPE1_CERT_PATH
Value: <path-to-nsa-type1-cert>

NSA_TYPE1_CERT_PASSWORD
Value: <nsa-type1-cert-password>

# GitHub Settings - Variables

SIGNING_MODE
Value: auto

REQUIRE_SIGNED_BUILD
Value: true

BUILD_VERSION
Value: 1.0.0

PRODUCT_NAME
Value: Sanctum Suite

PUBLISHER
Value: Karol Mrozinski

RELEASE_TAG
Value: v1.0.0

WINDOWS_BUILD_RUNNER
Value: windows-latest

INSTALLER_OUTPUT_DIRECTORY
Value: release/installer

CHECKSUM_FILE_NAME
Value: sha256sum.txt

CERTIFICATE_TYPE
Value: EV

PKI_MODE
Value: standard

COMPLIANCE_PROFILE
Value: standard-public-release

WHQL_ENABLED
Value: false

HLK_ENABLED
Value: false

ELAM_ENABLED
Value: false

PPL_ENABLED
Value: false

MVI_ENABLED
Value: false

NSA_TYPE1_MODE
Value: false
