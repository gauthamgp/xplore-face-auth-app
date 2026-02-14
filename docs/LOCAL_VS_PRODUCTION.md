# Complete Setup & Flow Guide: Local vs Production

This guide explains **two scenarios**: local development and EC2 production. Both work with the same code — only credentials and setup differ.

---

## Quick Summary

| Aspect | Local Development | EC2 Production |
|--------|-------------------|----------------|
| **Where to run** | Your Mac/laptop | AWS EC2 instance |
| **Credentials** | `.env` file (access keys) | IAM role (automatic) |
| **S3 access** | Via access keys in `.env` | Via instance metadata service |
| **Code changes** | None — same code | None — same code |
| **Setup complexity** | Simple (5 min) | Moderate (15 min) |

---

## SCENARIO 1: Local Development

### Step 1: Get AWS Access Keys

On your local Mac, you need temporary access keys for testing.

**Option A: Use existing AWS account**
```bash
# Go to AWS Console → IAM → Users → Your User → Security Credentials
# Create Access Key → Download CSV with:
#   - AWS_ACCESS_KEY_ID
#   - AWS_SECRET_ACCESS_KEY
```

**Option B: Create a dedicated IAM user for local dev** (recommended)
```bash
# AWS Console → IAM → Users → Create User "xplore-dev"
# → Attach policy: AmazonS3FullAccess (for testing)
# → Create Access Key → Download CSV
```

### Step 2: Create `.env` File on Your Mac

```bash
# In /Users/pgauthampai/Documents/Working Space/Xplore/.env
S3_BUCKET=xplore-face-auth-refs
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA1234567890ABCDEF
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
SECRET_KEY=my-dev-secret-key
VERIFICATION_MODEL=ArcFace
```

### Step 3: Install Dependencies Locally

```bash
cd "/Users/pgauthampai/Documents/Working Space/Xplore"
pip install -r requirements.txt
```

### Step 4: Run the App Locally

```bash
uvicorn app:app --reload --port 5000
```

**What happens:**
1. App starts
2. `load_dotenv()` reads `.env` file
3. boto3 sees `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in environment
4. S3 operations use those credentials
5. Upload/verify work as normal

### Step 5: Test Locally

```bash
# Register a user with a photo
curl -X POST http://localhost:5000/api/register \
  -F "user_id=alice" \
  -F "image=@alice_photo.jpg"

# Verify
curl -X POST http://localhost:5000/api/verify \
  -F "user_id=alice" \
  -F "image=@alice_live.jpg"
```

**Local Flow Diagram:**
```
Your Mac
├── .env (with AWS access keys)
├── app.py starts
│   ├── load_dotenv() reads .env
│   ├── boto3 sees AWS_ACCESS_KEY_ID in environment
│   └── uses those credentials
├── POST /api/register
│   ├── get_s3_client() → boto3 uses env credentials
│   └── Uploads image to S3 bucket
└── POST /api/verify
    ├── Downloads user refs from S3
    └── Verifies face
```

---

## SCENARIO 2: EC2 Production (Recommended)

### Step 1: Create S3 Bucket in AWS

```bash
# AWS Console → S3 → Create Bucket
# Bucket name: xplore-face-auth-refs
# Region: us-east-1
# Block public access: YES

# Or via CLI:
aws s3 mb s3://xplore-face-auth-refs --region us-east-1
```

### Step 2: Create IAM Role for EC2

**Create the role policy file** (`s3-policy.json`):
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
    }
  ]
}
```

**Create the IAM role:**
```bash
# 1. Create role with EC2 trust relationship
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

# 2. Attach the S3 policy
aws iam put-role-policy \
  --role-name XploreEC2Role \
  --policy-name XploreS3Access \
  --policy-document file://s3-policy.json

# 3. Create instance profile
aws iam create-instance-profile \
  --instance-profile-name XploreInstanceProfile

# 4. Add role to profile
aws iam add-role-to-instance-profile \
  --instance-profile-name XploreInstanceProfile \
  --role-name XploreEC2Role
```

### Step 3: Launch EC2 Instance with IAM Role

```bash
# Via AWS CLI
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.large \
  --iam-instance-profile Name=XploreInstanceProfile \
  --security-group-ids sg-xxxxxxxx \
  --key-name my-keypair \
  --region us-east-1 \
  --user-data file://init-script.sh
```

**Or manually in AWS Console:**
1. EC2 → Launch Instance
2. Select Ubuntu 20.04 LTS (or 22.04)
3. Instance Details → IAM Role → `XploreInstanceProfile`
4. Security Group → Inbound rules:
   - Port 22 (SSH) from your IP
   - Port 80 (HTTP) from 0.0.0.0/0
   - Port 443 (HTTPS) from 0.0.0.0/0
5. Review & Launch
6. Download `.pem` key file

### Step 4: SSH into EC2 Instance

```bash
ssh -i my-keypair.pem ubuntu@ec2-XXX-XXX-XXX-XXX.compute-1.amazonaws.com
```

### Step 5: Install App on EC2

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python & Git
sudo apt install -y python3 python3-pip git

# Clone repo (or upload via scp)
git clone https://github.com/yourusername/xplore.git
cd xplore

# Install dependencies
pip3 install -r requirements.txt
```

### Step 6: Create `.env` on EC2 (Production)

**Important:** No AWS keys here!

```bash
# On EC2 instance
cat > .env << 'EOF'
S3_BUCKET=xplore-face-auth-refs
AWS_REGION=us-east-1
SECRET_KEY=your-production-secret-key-here
VERIFICATION_MODEL=ArcFace

# NO AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY!
# EC2 IAM role provides credentials automatically
EOF
```

### Step 7: Verify IAM Role Works

```bash
# On EC2 instance, test S3 access
python3 << 'PYEOF'
import boto3

s3_client = boto3.client('s3', region_name='us-east-1')

try:
    response = s3_client.list_buckets()
    print("✓ S3 access works via IAM role!")
    for bucket in response['Buckets']:
        print(f"  - {bucket['Name']}")
except Exception as e:
    print(f"✗ Error: {e}")
PYEOF
```

### Step 8: Run App on EC2

```bash
# Option A: Simple (foreground)
cd xplore
uvicorn app:app --host 0.0.0.0 --port 5000

# Option B: Background with nohup
nohup uvicorn app:app --host 0.0.0.0 --port 5000 > app.log 2>&1 &

# Option C: systemd service (recommended for production)
# Create /etc/systemd/system/xplore.service (see setup below)
sudo systemctl start xplore
sudo systemctl enable xplore  # Start on reboot
```

### Production Flow Diagram

```
EC2 Instance
├── IAM Role attached (XploreInstanceProfile)
├── .env (NO AWS keys)
├── app.py starts
│   ├── load_dotenv() reads .env
│   ├── boto3.client() called
│   │   └── Queries metadata service (http://169.254.169.254/...)
│   │       └── Gets temporary credentials from IAM role
│   └── Uses temporary credentials for S3
├── POST /api/register
│   ├── get_s3_client() → boto3 auto-discovers IAM role
│   └── Uploads image to S3 (authenticated via IAM role)
└── POST /api/verify
    ├── Downloads user refs from S3 (authenticated via IAM role)
    └── Verifies face
```

---

## Can You Run Code Locally AND Deploy to EC2?

**YES! Absolutely.** The code is identical. Only the `.env` file differs:

### Local `.env`
```
S3_BUCKET=xplore-face-auth-refs
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=wJal...
```

### EC2 `.env`
```
S3_BUCKET=xplore-face-auth-refs
AWS_REGION=us-east-1
# (No AWS keys — IAM role provides them)
```

**Same code, different credentials.**

---

## Credential Discovery Chain

When `get_s3_client()` is called, boto3 looks for credentials in this order:

```
1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
   ↓ [Found on local] → Use them
   ↓ [Not found on EC2] → Continue

2. ~/.aws/credentials file (named profiles)
   ↓ [Found] → Use them
   ↓ [Not found] → Continue

3. EC2 Instance Metadata Service (IAM Role)
   ↓ [Found on EC2] → Use temporary credentials (rotated hourly)
   ↓ [Not found] → Error
```

**Local:** Stops at step 1 (uses `.env` keys)  
**EC2 with IAM role:** Skips to step 3 (uses metadata service)

---

## Step-by-Step Setup Summary

### Local Development (5 min)
```
1. Get AWS access keys (from AWS Console IAM)
2. Create .env with AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
3. pip install -r requirements.txt
4. uvicorn app:app --reload --port 5000
5. Test with curl or Postman
```

### EC2 Production (15 min)
```
1. Create S3 bucket (AWS Console or CLI)
2. Create IAM role with S3 permissions
3. Create instance profile and attach role
4. Launch EC2 instance with instance profile
5. SSH into instance
6. git clone repo, pip install -r requirements.txt
7. Create .env (NO AWS keys)
8. Run: uvicorn app:app --host 0.0.0.0 --port 5000
9. Test: curl http://ec2-ip:5000/api/verify
```

---

## Comparison Table

| Action | Local | EC2 |
|--------|-------|-----|
| Create S3 bucket? | Optional (can use DevOps' bucket) | **Required** |
| Get AWS keys? | **Yes** (for `.env`) | No — use IAM role |
| Create IAM role? | No | **Yes** |
| Create `.env` file? | **Yes** (with keys) | **Yes** (no keys) |
| Key rotation needed? | Manual/risky | Automatic (hourly) |
| Code changes? | None | None |

---

## Security Best Practices

### ❌ DON'T
- Commit `.env` to git (even locally)
- Use your main AWS account access keys
- Share access keys in Slack/email
- Hardcode credentials in code

### ✅ DO
- Add `.env` to `.gitignore`
- Use IAM roles for EC2 (no keys needed)
- Create dedicated IAM users for local dev with limited permissions
- Rotate local access keys quarterly
- Use Secrets Manager for sensitive data (API keys, encryption keys)

---

## Example: systemd Service (EC2 Production)

Create `/etc/systemd/system/xplore.service`:

```ini
[Unit]
Description=Xplore Face Auth Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/xplore
Environment="PATH=/home/ubuntu/xplore/venv/bin"
ExecStart=/home/ubuntu/xplore/venv/bin/uvicorn app:app --host 0.0.0.0 --port 5000 --workers 1
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl start xplore
sudo systemctl enable xplore
sudo systemctl status xplore
```

---

## Troubleshooting

### Local: "S3 not configured"
```
Error: S3 is not configured. Set S3_BUCKET (and AWS credentials) in environment.

Fix: Check .env has:
  - S3_BUCKET=xplore-face-auth-refs
  - AWS_ACCESS_KEY_ID=AKIA...
  - AWS_SECRET_ACCESS_KEY=wJal...
```

### Local: "Access Denied"
```
Error: An error occurred (AccessDenied) when calling the PutObject operation

Fix: Your access key doesn't have S3 permissions
  - AWS Console → IAM → Your User → Add Policy: AmazonS3FullAccess
```

### EC2: "Unable to locate credentials"
```
Error: NoCredentialsError: Unable to locate credentials

Fix: IAM role not attached correctly
  - EC2 Console → Instance → Check IAM Role field
  - If empty, stop instance, attach role, restart
  - Or test: curl http://169.254.169.254/latest/meta-data/iam/security-credentials/
```

### EC2: "Access Denied"
```
Error: AccessDenied: PutObject on S3

Fix: IAM role policy missing S3 permissions
  - AWS Console → IAM → XploreEC2Role → Check attached policies
  - Attach s3-policy.json with GetObject, PutObject, ListBucket
```

---

## Next Steps

1. **Local:** Set up `.env` with access keys, run `uvicorn`, test endpoints
2. **EC2:** Create IAM role, launch instance, deploy app
3. **Both:** Share API payloads with frontend team (see [API_PAYLOADS.md](API_PAYLOADS.md))
4. **Production:** Add nginx reverse proxy, SSL certificate (Let's Encrypt), auto-scaling

