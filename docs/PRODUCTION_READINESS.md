# Production Readiness Checklist

Your code is **production-ready** for both local and EC2 deployments. Here's the validation status and deployment checklist.

---

## Code Status: ✅ PRODUCTION READY

### What the Code Handles

✅ **Local Development**
- Reads `.env` file with `load_dotenv()`
- Uses `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` from `.env`
- boto3 uses environment credentials automatically
- Works with any AWS credentials (IAM user, root, temporary keys)

✅ **EC2 Production**
- Detects if S3_BUCKET is configured (fails fast if not)
- boto3 automatically discovers EC2 IAM role credentials (no keys needed)
- IAM role credentials are automatically rotated hourly
- Validates S3 access on startup
- Detailed logging of credential source and setup

✅ **Secrets Manager (Optional)**
- If `SECRETS_MANAGER_SECRET_NAME` is set, loads secrets from AWS Secrets Manager
- Works with IAM role credentials (no keys needed)
- Falls back gracefully if secret not found

---

## Deployment Checklist

### Local Development (5 min)

```bash
# 1. Create .env file
cat > .env << 'EOF'
S3_BUCKET=xplore-face-auth-refs
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA1234567890ABCDEF
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
SECRET_KEY=dev-secret-key-change-in-prod
VERIFICATION_MODEL=ArcFace
EOF

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run app (startup will validate credentials)
uvicorn app:app --reload --port 5000
```

**Expected startup output:**
```
================================================================================
XPLORE FACE AUTH STARTUP
================================================================================
✓ S3_BUCKET: xplore-face-auth-refs
✓ AWS_REGION: us-east-1
✓ AWS credentials validated (found 5 buckets)
✓ S3 bucket 'xplore-face-auth-refs' is accessible
✓ SECRET_KEY configured (production)
================================================================================
STARTUP COMPLETE - Ready to accept requests
================================================================================
INFO:     Uvicorn running on http://127.0.0.1:5000
```

### EC2 Production (15 min)

```bash
# 1. Create S3 bucket (or use existing)
aws s3 mb s3://xplore-face-auth-refs --region us-east-1

# 2. Create IAM role with S3 permissions (s3-policy.json)
aws iam create-role \
  --role-name XploreEC2Role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {"Service": "ec2.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }
    ]
  }'

aws iam put-role-policy \
  --role-name XploreEC2Role \
  --policy-name XploreS3Access \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
        "Resource": ["arn:aws:s3:::xplore-face-auth-refs", "arn:aws:s3:::xplore-face-auth-refs/*"]
      }
    ]
  }'

aws iam create-instance-profile --instance-profile-name XploreInstanceProfile
aws iam add-role-to-instance-profile \
  --instance-profile-name XploreInstanceProfile \
  --role-name XploreEC2Role

# 3. Launch EC2 instance with IAM role
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.large \
  --iam-instance-profile Name=XploreInstanceProfile \
  --security-group-ids sg-xxxxxxxx \
  --key-name my-keypair \
  --region us-east-1

# 4. SSH into instance
ssh -i my-keypair.pem ubuntu@ec2-XXX-XXX-XXX-XXX.compute-1.amazonaws.com

# 5. Install dependencies on EC2
sudo apt update && sudo apt install -y python3 python3-pip git
git clone https://github.com/yourusername/xplore.git
cd xplore
pip3 install -r requirements.txt

# 6. Create .env on EC2 (NO AWS KEYS!)
cat > .env << 'EOF'
S3_BUCKET=xplore-face-auth-refs
AWS_REGION=us-east-1
SECRET_KEY=your-production-secret-key-here
VERIFICATION_MODEL=ArcFace
EOF

# 7. Test that IAM role works
python3 -c "
import boto3
s3 = boto3.client('s3', region_name='us-east-1')
response = s3.list_buckets()
print('✓ IAM role credentials working!')
print(f'Found buckets: {[b[\"Name\"] for b in response[\"Buckets\"]]}')
"

# 8. Run app (startup will validate IAM credentials)
uvicorn app:app --host 0.0.0.0 --port 5000 --workers 1
```

**Expected startup output:**
```
================================================================================
XPLORE FACE AUTH STARTUP
================================================================================
✓ S3_BUCKET: xplore-face-auth-refs
✓ AWS_REGION: us-east-1
✓ AWS credentials validated (found 3 buckets)
✓ S3 bucket 'xplore-face-auth-refs' is accessible
✓ SECRET_KEY configured (production)
================================================================================
STARTUP COMPLETE - Ready to accept requests
================================================================================
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:5000
```

---

## How It Works: Credential Discovery

When app starts, it follows this flow:

### Local Development

```
1. load_dotenv() reads .env file
   ↓
2. AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY set in os.environ
   ↓
3. app.startup_event() calls get_s3_client()
   ↓
4. boto3 checks environment variables
   ↓
5. ✓ Credentials found → Logs: "AWS credentials validated"
```

### EC2 Production

```
1. load_dotenv() reads .env file (no AWS keys in it)
   ↓
2. AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY NOT in os.environ
   ↓
3. app.startup_event() calls get_s3_client()
   ↓
4. boto3 checks environment variables (not found)
   ↓
5. boto3 checks ~/.aws/credentials file (not found on EC2)
   ↓
6. boto3 checks EC2 instance metadata service (http://169.254.169.254/...)
   ↓
7. ✓ IAM role credentials found → Logs: "AWS credentials validated"
```

---

## Error Scenarios & Fixes

### Scenario 1: Local with Missing `.env`

**Error:**
```
S3_BUCKET is not configured! Set S3_BUCKET in environment or .env
Cannot proceed without valid S3 bucket.
```

**Fix:**
```bash
# Create .env file with S3_BUCKET
echo "S3_BUCKET=xplore-face-auth-refs" >> .env
echo "AWS_REGION=us-east-1" >> .env
echo "AWS_ACCESS_KEY_ID=AKIA..." >> .env
echo "AWS_SECRET_ACCESS_KEY=wJal..." >> .env
```

### Scenario 2: Local with Invalid AWS Keys

**Error:**
```
Credential error creating S3 client: The provided credentials could not be validated.
For local: set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env
```

**Fix:**
```bash
# Verify keys in AWS Console → IAM → Users → Security Credentials
# Copy fresh access key and update .env
# Ensure key is still active (not deleted)
```

### Scenario 3: EC2 without IAM Role

**Error:**
```
Credential error creating S3 client: Unable to locate credentials.
For EC2: attach IAM role with S3 permissions to instance
```

**Fix:**
```bash
# 1. Check if IAM role is attached
aws ec2 describe-instances --instance-ids i-xxxxxxxx | grep IamInstanceProfile

# 2. If empty, stop instance and attach role
aws ec2 associate-iam-instance-profile \
  --iam-instance-profile Name=XploreInstanceProfile \
  --instance-id i-xxxxxxxx

# 3. Restart instance and app
sudo reboot
```

### Scenario 4: EC2 IAM Role without S3 Permissions

**Error:**
```
AccessDenied: An error occurred (AccessDenied) when calling the PutObject operation
```

**Fix:**
```bash
# Verify IAM role has S3 permissions
aws iam get-role-policy --role-name XploreEC2Role --policy-name XploreS3Access

# If missing, attach S3 policy
aws iam put-role-policy --role-name XploreEC2Role --policy-name XploreS3Access \
  --policy-document file://s3-policy.json
```

---

## Production Hardening (Beyond Basic Setup)

These are optional but recommended for production:

### 1. Use systemd Service (EC2)

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

Start:
```bash
sudo systemctl start xplore
sudo systemctl enable xplore
sudo systemctl status xplore
```

### 2. Add nginx Reverse Proxy + SSL

```bash
sudo apt install -y nginx certbot python3-certbot-nginx

# Configure nginx
sudo tee /etc/nginx/sites-available/xplore > /dev/null << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/xplore /etc/nginx/sites-enabled/

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Start nginx
sudo systemctl restart nginx
```

### 3. Use CloudWatch for Logs (EC2)

```bash
# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i -E ./amazon-cloudwatch-agent.deb

# Configure to send logs to CloudWatch
# (requires CloudWatch IAM permissions added to role)
```

### 4. Use Secrets Manager for Sensitive Values

```bash
# Store SECRET_KEY in Secrets Manager
aws secretsmanager create-secret \
  --name xplore/prod-secrets \
  --secret-string '{"SECRET_KEY": "your-secret-key"}'

# Update .env to use Secrets Manager
echo "SECRETS_MANAGER_SECRET_NAME=xplore/prod-secrets" >> .env

# Add permission to IAM role
# (include secretsmanager:GetSecretValue action)
```

---

## Validation Checklist

Before deploying to production:

- [ ] S3 bucket created and name is correct
- [ ] IAM role created with S3 permissions
- [ ] EC2 instance has IAM role attached
- [ ] `.env` file created (local: with AWS keys, EC2: without)
- [ ] App starts without errors (check startup logs)
- [ ] S3 bucket is accessible (test with curl or Python)
- [ ] `/api/register` endpoint works
- [ ] `/api/verify` endpoint works
- [ ] Logs show detailed timing information
- [ ] No AWS credentials in git history
- [ ] SECRET_KEY is changed from default

---

## Quick Test Commands

### Local

```bash
# Test registration
curl -X POST http://localhost:5000/api/register \
  -F "user_id=testuser" \
  -F "image=@sample.jpg"

# Test verification
curl -X POST http://localhost:5000/api/verify \
  -F "user_id=testuser" \
  -F "image=@sample.jpg"
```

### EC2

```bash
# SSH into instance
ssh -i key.pem ubuntu@ec2-ip

# Test S3 access
python3 -c "import boto3; print('✓' if boto3.client('s3').list_buckets() else '✗')"

# Test app
curl http://localhost:5000/

# View logs
tail -f app.log
```

---

## Summary

Your code **IS production-ready**. Deploy it with confidence:

| Scenario | Status | Setup Time |
|----------|--------|------------|
| Local development | ✅ Ready | 5 min |
| EC2 with IAM role | ✅ Ready | 15 min |
| With Secrets Manager | ✅ Ready | 20 min |
| With nginx + SSL | ✅ Ready | 30 min |

The startup validation ensures credentials are correct before accepting requests. If something is misconfigured, the app logs exactly what's wrong and how to fix it.
