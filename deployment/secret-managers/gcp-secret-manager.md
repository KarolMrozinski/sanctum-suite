# GCP Secret Manager integration

## Recommended pattern
- Use Workload Identity Federation or a dedicated service account
- Grant `roles/secretmanager.secretAccessor` to the runtime identity
- Fetch or mount secrets at runtime

## Example grant
```bash
gcloud secrets add-iam-policy-binding sanctum-phase1 \
  --member="serviceAccount:sanctum-phase1-sa@sanctum-prod-482917.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```
