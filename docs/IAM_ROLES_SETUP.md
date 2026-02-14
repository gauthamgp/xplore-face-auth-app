# Using IAM Roles Instead of Access Keys

Best practice: Use EC2 IAM roles for automatic credential discovery. boto3 will fetch temporary credentials from the EC2 instance metadata service, rotating them automatically.

---

## How It Works

When boto3 is initialized without explicit `aws_access_key_id` and `aws_secret_access_key`, it follows this **credential chain**:

1. Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (if set)
2. Named profiles in `~/.aws/credentials`
3. **EC2 Instance IAM Role** (metadata service — **automatic & temporary**)
4. ECS container credentials (if running in ECS)
5. Default profile

With an **IAM role attached to the EC2 instance**, boto3 automatically:
- Fetches temporary security credentials from the metadata service (`http://169.254.169.254/latest/meta-data/...`)
- Rotates credentials hourly (you don't manage keys)
- Requires no credentials in environment or files

---

## Code Changes Required

### 1. Simplify `s3_utils.py`

**Current code:**
```python
def get_s3_client():
    """Return boto3 S3 client using env credentials (or default chain)."""
    import boto3
    kwargs = {"region_name": AWS_REGION}
    if os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"):
        kwargs["aws_access_key_id"] = os.environ.get("AWS_ACCESS_KEY_ID")
        kwargs["aws_secret_access_key"] = os.environ.get("AWS_SECRET_ACCESS_KEY")
    return boto3.client("s3", **kwargs)
```

**New code (IAM role optimized):**
```python
def get_s3_client():
    """
    Return boto3 S3 client.
    
    Credential chain (in order):
    1. Environment vars (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY) — if explicitly set
    2. AWS credentials file (~/.aws/credentials)
    3. EC2 IAM Role (automatic — RECOMMENDED for production)
    4. ECS task credentials
    
    For production on EC2, attach an IAM role with S3 permissions and this will
    automatically use temporary, rotating credentials.
    """
    import boto3
    return boto3.client("s3", region_name=AWS_REGION)
```

**What changed:**
- Removed explicit credential passing
- boto3 now uses the default credential chain
- On EC2 with an IAM role, this automatically uses the role credentials

---

### 2. Update `app.py` Secrets Manager Loading (Optional)

If you're using AWS Secrets Manager to load secrets, it will also use IAM role credentials:

```python
def _load_aws_secrets_from_secrets_manager():
    """
    If `SECRETS_MANAGER_SECRET_NAME` is set, fetch that secret (JSON) and
    populate os.environ with its keys.
    
    Uses IAM role credentials automatically (no explicit keys needed).
    """
    name = os.environ.get("SECRETS_MANAGER_SECRET_NAME") or os.environ.get("SECRETS_NAME")
    if not name:
        return
    try:
        import json
        import boto3

        # boto3 will use IAM role credentials from metadata service
        client = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION"))
        resp = client.get_secret_value(SecretId=name)
        secret_str = resp.get("SecretString")
        if not secret_str:
            return
        data = json.loads(secret_str)
        if not isinstance(data, dict):
            return
        for k, v in data.items():
            os.environ[str(k)] = str(v)
        print(f"✓ Loaded secrets from Secrets Manager: {name}")
    except Exception as e:
        print(f"Warning: could not load secrets from Secrets Manager '{name}': {e}")
```

No changes needed — it already uses the credential chain.

---

## EC2 Setup Steps

### 1. Create IAM Role with S3 Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::xplore-face-auth-refs",
        "arn:aws:s3:::xplore-face-auth-refs/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:123456789012:secret:xplore/*"
    }
  ]
}
```

### 2. Create Instance Profile

```bash
# Create the role
aws iam create-role \
  --role-name XploreEC2Role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "ec2.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }'

# Attach the policy
aws iam put-role-policy \
  --role-name XploreEC2Role \
  --policy-name XploreS3Access \
  --policy-document file://s3-policy.json

# Create instance profile
aws iam create-instance-profile \
  --instance-profile-name XploreInstanceProfile

# Add role to instance profile
aws iam add-role-to-instance-profile \
  --instance-profile-name XploreInstanceProfile \
  --role-name XploreEC2Role
```

### 3. Launch EC2 Instance with IAM Role

**AWS CLI:**
```bash
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.large \
  --iam-instance-profile Name=XploreInstanceProfile \
  --security-group-ids sg-xxxxxxxx \
  --key-name my-key-pair \
  --region us-east-1
```

**Or via Console:**
1. EC2 → Launch Instance
2. Choose Ubuntu 20.04 LTS (or 22.04)
3. Instance Details → IAM Role → `XploreInstanceProfile`
4. Security Group → allow inbound 22 (SSH), 80 (HTTP), 443 (HTTPS)
5. Launch

### 4. No Environment Variables Needed!

On the EC2 instance, you only need:
```bash
# .env or systemd service env
S3_BUCKET=xplore-face-auth-refs
AWS_REGION=us-east-1
SECRET_KEY=your-secret-key-here
VERIFICATION_MODEL=ArcFace

# NO AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY needed!
```

---

## Verification

SSH into the EC2 instance and test:

```bash
# SSH
ssh -i my-key.pem ubuntu@ec2-xxx-xxx-xxx-xxx.compute-1.amazonaws.com

# Install Python & pip
sudo apt update && sudo apt install -y python3 python3-pip

# Test boto3 with IAM role
python3 << 'EOF'
import boto3

s3_client = boto3.client('s3', region_name='us-east-1')

try:
    response = s3_client.list_buckets()
    print("✓ S3 Buckets accessible via IAM role:")
    for bucket in response['Buckets']:
        print(f"  * {bucket['Name']}")
except Exception as e:
    print(f"✗ Error accessing S3: {e}")
EOF
```

Expected output:
```
✓ S3 Buckets accessible via IAM role:
  * xplore-face-auth-refs
  * my-other-bucket
```

---

## Why This Is Better

| Aspect | Access Keys | IAM Role |
|--------|-------------|----------|
| **Credentials in files** | ❌ Risk (leaked in git, logs) | ✅ None needed |
| **Credential rotation** | ❌ Manual/risky | ✅ Automatic (hourly) |
| **Scope** | ❌ Full account access | ✅ Limited per role |
| **Scalability** | ❌ Share keys across instances | ✅ Each instance gets own temporary creds |
| **Audit trail** | ⚠️ Hard to track | ✅ CloudTrail logs principal ARN |
| **MFA support** | ❌ Not supported | ✅ Can require MFA |

---

## Complete Updated `s3_utils.py` Snippet

```python
"""
S3 utilities for storing and retrieving user reference images.
Uses IAM role for credential management (recommended for production).
Falls back to environment variables if explicitly provided.
"""
import os
import boto3
from pathlib import Path

S3_BUCKET = os.environ.get("S3_BUCKET", "YOUR_BUCKET_NAME_PLACEHOLDER")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

def get_s3_client():
    """
    Return boto3 S3 client using automatic credential discovery.
    
    Priority:
    1. Environment variables (if set — for dev/testing)
    2. EC2 IAM role (production — recommended)
    3. ~/.aws/credentials file
    4. ECS task credentials
    
    Production EC2 instances should have an IAM role attached with S3 permissions.
    No explicit credentials needed in environment or files.
    """
    return boto3.client("s3", region_name=AWS_REGION)


def upload_reference_image(user_id: str, image_bytes: bytes, file_extension: str = "jpg") -> str:
    """Upload reference image to S3."""
    user_id = user_id.strip().lower()
    import uuid
    name = f"ref_{uuid.uuid4().hex[:12]}.{file_extension.lstrip('.')}"
    key = f"users/{user_id}/{name}"
    
    client = get_s3_client()
    client.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=image_bytes,
        ContentType=f"image/{'jpeg' if file_extension.lower() in ('jpg', 'jpeg') else 'png'}",
    )
    return key


def list_user_reference_keys(user_id: str) -> list[str]:
    """List all reference images for a user."""
    user_id = user_id.strip().lower()
    prefix = f"users/{user_id}/"
    
    client = get_s3_client()
    response = client.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
    
    if "Contents" not in response:
        return []
    
    return [obj["Key"] for obj in response["Contents"] if obj["Key"] != prefix]
```

---

## For Your DevOps Engineer

Share this summary:

> **Migration from Access Keys to IAM Roles:**
>
> 1. **Code change:** Remove `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` from `get_s3_client()` — boto3 uses automatic credential discovery.
> 2. **EC2 setup:** Attach an IAM role with S3/Secrets Manager permissions to the instance.
> 3. **Environment:** Only set `S3_BUCKET`, `AWS_REGION`, `SECRET_KEY` — no AWS credentials needed.
> 4. **Benefits:** Automatic credential rotation, no keys in files, audit trail, better security posture.
> 5. **Verification:** Run test script to confirm S3 access works with IAM role.

---

## Additional Resources

- [AWS: IAM Roles for EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html)
- [boto3: Credentials](https://boto3.amazonaws.com/en/latest/guide/credentials.html)
- [AWS: Best Practices for IAM](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
