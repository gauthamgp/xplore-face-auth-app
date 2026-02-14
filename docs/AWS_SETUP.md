# AWS Setup for Face Auth (S3 + IAM)

This app stores user reference photos in **Amazon S3** and uses **IAM** credentials to access the bucket. Follow these steps to create the bucket and credentials, then configure the app with placeholders replaced.

---

## 1. Create an S3 bucket

1. In the **AWS Console**, go to **S3** (search “S3” in the top bar).
2. Click **Create bucket**.
3. **Bucket name:** Choose a globally unique name (e.g. `your-company-face-auth-refs` or `face-auth-refs-<account-id>`).
4. **Region:** Choose the same region you will run the app in (e.g. `us-east-1`).
5. **Block Public Access:** Leave “Block all public access” **on** (reference images should not be public).
6. **Bucket Versioning:** Optional; you can enable if you want to recover overwritten objects.
7. Click **Create bucket**.

**Note the bucket name and region** — you will set them in the app as `S3_BUCKET` and `AWS_REGION`.

---

## 2. Create an IAM user (or role) for the app

You need an identity that has permission only to read/write objects (and list) in this bucket.

### Option A: IAM user (for dev or when running on a non-AWS host)

1. Go to **IAM** → **Users** → **Create user**.
2. **User name:** e.g. `face-auth-app`.
3. **Access type:** **Programmatic access** (access key).
4. **Permissions:** Attach policy directly (see policy below).
5. Create the user, then **Create access key**.
6. **Save the Access Key ID and Secret Access Key** — you will set them as `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`. You cannot view the secret again after leaving the page.

### Option B: IAM role (for app running on EC2 / ECS / Lambda)

1. Go to **IAM** → **Roles** → **Create role**.
2. **Trusted entity:** e.g. **EC2** or **ECS** or **Lambda**, depending on where the app runs.
3. **Permissions:** Attach the same policy (or a custom policy with the same effect).
4. Name the role (e.g. `FaceAuthAppRole`). When the app runs on that service, it will use this role automatically — **no access key needed** in the app (boto3 uses the instance/task role).

---

## 3. IAM policy (minimal permissions)

Create a **custom policy** with the following JSON (replace `YOUR_BUCKET_NAME` with your actual bucket name):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListBucket",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME"
    },
    {
      "Sid": "ObjectAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME/users/*"
    }
  ]
}
```

- **ListBucket** is needed so the app can list objects under `users/<user_id>/` for verification.
- **GetObject / PutObject** are used to download reference images and upload new ones during registration.
- **DeleteObject** is optional; include it only if you plan to delete reference photos via the app.

Attach this policy to the IAM user (Option A) or the IAM role (Option B).

---

## 4. Environment variables (placeholders in code)

Set these in your deployment environment (or `.env` if you load it in the app). The code uses these; replace placeholders with real values.

| Variable | Description | Example |
|----------|-------------|---------|
| **S3_BUCKET** | Name of the S3 bucket you created | `your-company-face-auth-refs` |
| **AWS_REGION** | AWS region of the bucket | `us-east-1` |
| **AWS_ACCESS_KEY_ID** | IAM user access key (only if using IAM user, not role) | `AKIA...` |
| **AWS_SECRET_ACCESS_KEY** | IAM user secret key (only if using IAM user) | `...` |

- If the app runs on **EC2/ECS/Lambda** with an **IAM role** attached, you **do not** need to set `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY`; boto3 will use the role automatically. You still must set **S3_BUCKET** and **AWS_REGION**.

**Where to set them:**

- **Local / dev:** Create a `.env` file (do not commit it) and load it, or export in the shell:
  ```bash
  export S3_BUCKET=your-company-face-auth-refs
  export AWS_REGION=us-east-1
  export AWS_ACCESS_KEY_ID=AKIA...
  export AWS_SECRET_ACCESS_KEY=...
  ```
- **Production (e.g. ECS task definition, Lambda config, or CI/CD):** Set the same variables in your deployment configuration so the app can read them via `os.environ`.

---

## 5. S3 layout used by the app

- **Prefix:** `users/`
- **Per user:** `users/<user_id>/` (e.g. `users/alice/`, `users/bob/`).
- **Files:** Any object key under that prefix with image extensions (`.jpg`, `.jpeg`, `.png`, etc.) is treated as a reference image. The app uploads with names like `ref_<uuid>.jpg` during registration and lists all such keys for verification.

No other AWS resources (e.g. Lambda, API Gateway) are required for the app logic; the app runs as a normal FastAPI server and talks to S3 via boto3.

---

## 6. Checklist for DevOps

- [ ] S3 bucket created; name and region noted.
- [ ] IAM user or role created with the policy above (bucket name replaced).
- [ ] If using IAM user: access key and secret stored securely and set as env vars where the app runs.
- [ ] Env vars **S3_BUCKET** and **AWS_REGION** set in the app’s runtime environment.
- [ ] App can reach the internet (or VPC endpoint for S3) so boto3 can call S3.

After this, the **Register** API will store photos in `users/<user_id>/` and the **Verify** API will read from the same prefix for the given `user_id`.
