# Package Signing Key Custody (CueLiez)

CueLiez supports a real **HMAC-SHA256** package signing/verification workflow (`src/cueliez/signing.py`) over the canonical package hash. `package_signature` is excluded from the hash.

## Configuration
- `CUELIEZ_SIGNING_KEY` - HMAC key material (secret). Prefer secret managers/injected env, not committed files.
- `CUELIEZ_SIGNING_KEY_FILE` - path to a file containing key material (restricted permissions, e.g. `0600`).
- Use a strong, random key (e.g., 32+ bytes). Treat as a sensitive credential.

## Custody responsibilities (operator)
- **Generation:** generate keys using a cryptographically secure source; record key ID/fingerprint metadata separately from key material.
- **Storage:** store in approved secret management (vault/KMS/OS secret store) or protected files; never commit to git, packages, or logs.
- **Access control:** least privilege; limit which processes/users can read signing keys; audit access per policy.
- **Rotation:** define rotation periods/triggers; support overlap/verification of packages signed with previous keys as policy requires (current implementation verifies with the configured key).
- **Backup/recovery:** protect backups with equivalent controls; test recovery under policy.
- **Compromise response:** revoke/rotate keys, assess affected artifacts, and follow incident/custody procedures.

## Scope
HMAC-SHA256 provides integrity/authenticity relative to holders of the shared secret. For non-repudiation/public verification or PKI-based workflows, extend with asymmetric signing in an approved design (may require additional dependencies/policy).

## Safety
Signing does not change CueLiez’s observation/cue-only epistemic model. Signed packages remain observed indicators/cues only — never findings, diagnoses, or determinations.
