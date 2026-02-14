# GitHub & Render Deployment Guide

## Step 1: Initialize Git (if not done)

```bash
cd /Users/pgauthampai/Documents/Working\ Space/Xplore

# Check if git is already initialized
git status

# If not initialized, initialize it
git init
```

---

## Step 2: Create GitHub Repository

### Option A: Create on GitHub Website (Recommended)

1. Go to https://github.com/new
2. Create a new repository:
   - **Repository name:** `xplore-face-auth` (or your choice)
   - **Description:** Face Authentication App with S3 & FastAPI
   - **Visibility:** Public (for free Render deployment)
   - **Initialize:** Do NOT initialize with README (we have one)
3. Click "Create repository"
4. Copy the repository URL (e.g., `https://github.com/YOUR_USERNAME/xplore-face-auth.git`)

### Option B: Using GitHub CLI

```bash
# Install GitHub CLI if needed
brew install gh

# Login
gh auth login

# Create repository
gh repo create xplore-face-auth --public --source=. --remote=origin --push
```

---

## Step 3: Add Remote & Push to GitHub

```bash
# Navigate to your project directory
cd /Users/pgauthampai/Documents/Working\ Space/Xplore

# Add remote (replace with your repo URL)
git remote add origin https://github.com/YOUR_USERNAME/xplore-face-auth.git

# Verify remote is added
git remote -v
# Should show:
# origin  https://github.com/YOUR_USERNAME/xplore-face-auth.git (fetch)
# origin  https://github.com/YOUR_USERNAME/xplore-face-auth.git (push)
```

---

## Step 4: Stage and Commit Files

```bash
# Check what will be committed
git status

# Stage all files (respects .gitignore)
git add -A

# Verify .env is NOT staged (should be in .gitignore)
git status
# .env should NOT appear in the list

# Commit
git commit -m "Initial commit: Face auth app with S3 integration and embedding caching"
```

---

## Step 5: Push to GitHub

```bash
# Push to main branch
git branch -M main
git push -u origin main

# Verify on GitHub by visiting:
# https://github.com/YOUR_USERNAME/xplore-face-auth
```

**What gets pushed:**
- ✅ All source code (.py files)
- ✅ requirements.txt
- ✅ Templates & static files
- ✅ Documentation files
- ✅ .gitignore
- ❌ .env (credentials safe!)
- ❌ __pycache__
- ❌ venv

---

## Step 6: Prepare for Render Deployment

### Create render.yaml (Optional but Recommended)

Create a file called `render.yaml` in your project root:

```bash
cat > render.yaml << 'EOF'
services:
  - type: web
    name: xplore-face-auth
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: S3_BUCKET
        scope: run
      - key: AWS_REGION
        scope: run
      - key: AWS_ACCESS_KEY_ID
        scope: run
      - key: AWS_SECRET_ACCESS_KEY
        scope: run
      - key: SECRET_KEY
        scope: run
EOF

# Stage and commit
git add render.yaml
git commit -m "Add render.yaml for deployment configuration"
git push
```

---

## Step 7: Deploy to Render

### Create Render Account

1. Go to https://render.com
2. Sign up with GitHub (easiest!)
3. Authorize Render to access your GitHub account

### Deploy Your App

1. **Dashboard** → Click "New +"
2. Select **"Web Service"**
3. **Connect GitHub**:
   - Select your GitHub account
   - Choose repository: `xplore-face-auth`
   - Authorize
4. **Configure Service**:
   - **Name:** `xplore-face-auth`
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free (750 hrs/month)
5. Click "Create Web Service"

Render will start building! (2-3 minutes)

### Add Environment Variables

While Render is building, add your secrets:

1. Go to your Render service dashboard
2. Click **"Environment"** tab
3. Add these environment variables:

```
S3_BUCKET = xplore-face-auth-refs
AWS_REGION = us-east-1
AWS_ACCESS_KEY_ID = AKIASIHBA36DZFF2SKXL
AWS_SECRET_ACCESS_KEY = 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
SECRET_KEY = generate-random-key-here
```

**To generate SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

4. Click "Save"

---

## Step 8: Verify Deployment

Once the build completes:

1. Render shows your app URL:
   ```
   https://xplore-face-auth.onrender.com
   ```

2. **Test endpoints:**

   **Test page:** https://xplore-face-auth.onrender.com/api-test
   
   **Register API:**
   ```bash
   curl -X POST https://xplore-face-auth.onrender.com/api/register \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "alice",
       "image": "data:image/jpeg;base64,..."
     }'
   ```

   **Verify API:**
   ```bash
   curl -X POST https://xplore-face-auth.onrender.com/api/verify \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "alice",
       "image": "data:image/jpeg;base64,..."
     }'
   ```

---

## Step 9: Enable Auto-Deployment (Optional)

By default, Render auto-deploys on every push to main!

To disable or configure:
1. Service Dashboard → Settings
2. Scroll to "Auto-Deploy"
3. Toggle on/off as needed

---

## Complete Workflow for Future Updates

After you make changes locally:

```bash
# Make your changes
# ... edit files ...

# Check status
git status

# Stage changes
git add -A

# Commit
git commit -m "Your descriptive message"

# Push to GitHub
git push

# Render automatically deploys! 🚀
```

---

## Troubleshooting

### Build Fails

Check logs in Render dashboard:
1. Service → Logs
2. Look for error messages
3. Common issues:
   - Missing environment variables
   - Python version mismatch
   - Missing dependencies

### App Starts but 500 Error

1. Check Render logs for error details
2. Verify all environment variables are set
3. Check S3 bucket name and credentials

### Slow Deployment

First deployment can be 3-5 minutes. Subsequent deployments are faster!

---

## Update .env.example

After adding secrets in Render, update your `.env.example` to document what's needed:

```bash
cat > .env.example << 'EOF'
# AWS S3 Configuration
S3_BUCKET=your-bucket-name
AWS_REGION=us-east-1

# AWS Credentials (get from AWS IAM)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Session Secret (generate: python -c "import secrets; print(secrets.token_hex(32))")
SECRET_KEY=your-secret-key-here
EOF

git add .env.example
git commit -m "Update env example"
git push
```

---

## Summary of URLs

After deployment:

| Endpoint | URL |
|----------|-----|
| Test Page | https://xplore-face-auth.onrender.com/api-test |
| Register | https://xplore-face-auth.onrender.com/api/register |
| Verify | https://xplore-face-auth.onrender.com/api/verify |
| Login | https://xplore-face-auth.onrender.com/login |
| Dashboard | https://xplore-face-auth.onrender.com/dashboard |

---

## Quick Commands Reference

```bash
# Check git status
git status

# View recent commits
git log --oneline -5

# Push changes
git push

# Check remote
git remote -v

# See which branch you're on
git branch

# Switch branch
git checkout branch-name

# Create new branch
git checkout -b feature-name
```

---

## Security Best Practices

✅ **Keep .env local only**
- Never commit .env
- Check .gitignore includes it

✅ **Use Render Environment Variables**
- Secrets stored securely
- Not in code or git history

✅ **Rotate AWS Keys Periodically**
- Go to AWS IAM Console
- Create new access keys
- Update in Render
- Delete old keys

✅ **Monitor S3 Access**
- Enable CloudTrail in AWS
- Alert on unusual activity

---

## Next Steps

1. ✅ Initialize GitHub repo
2. ✅ Push code to GitHub
3. ✅ Create Render account
4. ✅ Deploy to Render
5. ✅ Test endpoints
6. ✅ Share URL with frontend team

Your app is now **live on the internet!** 🎉
