# AWS S3 Setup

Object storage backs two distinct features — user file uploads (`services/storage_service.py`)
and encrypted MongoDB backups (`deploy/backup.sh`). They can use the same bucket with
different prefixes or two separate buckets; two buckets is cleaner for lifecycle/retention
policy differences.

## 1. Create the bucket(s)

```bash
aws s3 mb s3://synaptiq-prod-uploads --region eu-west-1
aws s3 mb s3://synaptiq-prod-backups --region eu-west-1
```

- Block all public access (default in modern AWS accounts — verify it's on).
- Enable versioning on the backups bucket (protects against accidental overwrite/delete).
- Enable default SSE (server-side encryption, SSE-S3 or SSE-KMS) on both buckets.

## 2. IAM policy

Create a dedicated IAM user (not your root/admin credentials) with a policy scoped to
only these two buckets:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:HeadBucket"],
      "Resource": ["arn:aws:s3:::synaptiq-prod-uploads/*", "arn:aws:s3:::synaptiq-prod-uploads"]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
      "Resource": ["arn:aws:s3:::synaptiq-prod-backups/*", "arn:aws:s3:::synaptiq-prod-backups"]
    }
  ]
}
```

Generate an access key for this IAM user (Security Credentials → Create access key —
prefer this over long-lived root keys; rotate periodically per [SECURITY.md](SECURITY.md)).

## 3. Environment variables

| Variable | Purpose |
|---|---|
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | IAM credentials, shared by both upload and backup paths |
| `AWS_REGION` | Region for both buckets (default `us-east-1` if unset — set explicitly to match where you created the buckets) |
| `S3_BUCKET_NAME` | Uploads bucket, read by `services/storage_service.py` |
| `S3_BACKUP_BUCKET` | Backups bucket, read by `deploy/backup.sh` |
| `S3_ENDPOINT_URL` | Optional — set only if using an S3-compatible provider (MinIO, Supabase Storage, Cloudflare R2 via S3 API) instead of real AWS |
| `BACKUP_ENCRYPTION_PASSPHRASE` | Not S3-specific, but required alongside the backup bucket — backups are `openssl enc -aes-256-cbc` encrypted before upload |

## 4. What the application does with S3

`services/storage_service.py`:
- `init_storage()` — calls `head_bucket` at startup to verify access; logged as a
  warning (not fatal) if `S3_BUCKET_NAME` is unset, per `server.py`'s startup sequence
  (`"Object storage init deferred: S3_BUCKET_NAME not configured"`).
- `put_object(path, data, content_type)` / `get_object(path)` — used by file upload/
  download endpoints (`routers/messaging.py` attachments, repository file storage).
- `build_path(user_id, ext)` — generates `synaptiq/uploads/{user_id}/{uuid}.{ext}` keys —
  files are never stored with user-controlled filenames, avoiding path traversal.

## 5. Verification

```bash
aws s3 ls s3://synaptiq-prod-uploads
curl https://api.synaptiq.academy/api/health   # does not currently check S3 — see below
```

## Missing Production Requirements

- **`/api/health` does not check S3 connectivity** — a misconfigured or unreachable
  bucket will only surface when a user attempts an upload/download, not proactively.
  Consider adding an S3 `head_bucket` check to the health/readiness endpoint.
- No lifecycle policy documented for the uploads bucket (e.g., transitioning old/unused
  files to Glacier, or expiring orphaned uploads) — set one in the S3 console based on
  your retention requirements.
- No CDN (e.g. CloudFront) in front of the uploads bucket for user-facing file downloads
  — currently served directly through the backend (`get_object` streams through the API),
  which works but doesn't benefit from edge caching for large/frequently-accessed files.
