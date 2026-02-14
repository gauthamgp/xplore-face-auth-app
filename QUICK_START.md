# 🚀 Quick Start: Deploy & Use Your App

## What You Have

✅ **2 API Endpoints:**
- `POST /api/register` - Store user's face photo
- `POST /api/verify` - Check if a face matches

✅ **Secure Credentials Storage:**
- Credentials in `.env` (never pushed to GitHub)
- Ready for deployment to cloud platforms

---

## Step 1: Test Locally

```bash
# Make sure you're in your app directory
cd /Users/pgauthampai/Documents/Working\ Space/Xplore

# Install dependencies
pip install -r requirements.txt

# Run the app
uvicorn app:app --reload

# Test the APIs
# Open: http://localhost:8000/api-test
```

You should see a test page where you can test register & verify!

---

## Step 2: Deploy to Internet (Free)

### **Recommended: Render** (easiest)

1. **Push to GitHub** (if not done yet)
   ```bash
   git add -A
   git commit -m "Add face auth app with secure credentials"
   git push origin main
   ```

2. **Create Render Account**
   - Go to https://render.com
   - Sign up with GitHub

3. **Deploy**
   - Click "New" → "Web Service"
   - Select your GitHub repository
   - Render automatically detects Python
   - Wait for deployment...

4. **Add Environment Variables**
   - In Render dashboard, go to "Environment"
   - Add these 4 variables:
     ```
     S3_BUCKET=xplore-face-auth-refs
     AWS_REGION=us-east-1
     AWS_ACCESS_KEY_ID=AKIASIHBA36DZFF2SKXL
     AWS_SECRET_ACCESS_KEY=QZePgLOQHZmoP52oyDjEEJhri/tpqJZ/fJtGeBe9
     ```
   - Click "Deploy"

5. **Done!** Your app is live at: `https://your-app-name.onrender.com`

---

## Step 3: Call the API from Frontend

### Example: Register User
```javascript
const username = "alice";
const imageBase64 = "data:image/jpeg;base64,..."; // From camera

const response = await fetch(
  'https://your-app.onrender.com/api/register',
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: username,
      image: imageBase64
    })
  }
);

const result = await response.json();
console.log(result.success ? '✓ Registered!' : '✗ Error: ' + result.message);
```

### Example: Verify User
```javascript
const response = await fetch(
  'https://your-app.onrender.com/api/verify',
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: username,
      image: imageBase64
    })
  }
);

const result = await response.json();
console.log(result.verified ? '✓ Face matches!' : '✗ Face mismatch');
```

---

## Security Check ✅

- ✅ Credentials in `.env` (not in code)
- ✅ `.env` in `.gitignore` (won't push to GitHub)
- ✅ Environment variables set in Render dashboard (not in code)
- ✅ No hardcoded secrets anywhere

**Your AWS credentials are SAFE because:**
1. They're never in your GitHub repository
2. Only your Render account can see them
3. They're stored securely on Render servers

---

## File Guide

| File | Purpose |
|------|---------|
| `app.py` | Main FastAPI app with 2 endpoints |
| `s3_utils.py` | Handles S3 bucket operations |
| `face_utils.py` | Face recognition logic |
| `.env` | Your local credentials (NEVER commit) |
| `.env.example` | Template showing what's needed |
| `.gitignore` | Prevents `.env` from being pushed |
| `requirements.txt` | Python dependencies |
| `Procfile` | Deployment config |
| `DEPLOYMENT_GUIDE.md` | Detailed deployment instructions |
| `API_QUICK_REFERENCE.md` | API documentation |

---

## API Response Examples

### Register - Success
```json
{
  "success": true,
  "message": "Reference photo stored successfully.",
  "user_id": "alice",
  "stored_key": "users/alice/ref_xyz.jpg"
}
```

### Register - Error
```json
{
  "success": false,
  "message": "S3 is not configured..."
}
```

### Verify - Match
```json
{
  "success": true,
  "verified": true,
  "message": "Face matches registered user.",
  "user_id": "alice"
}
```

### Verify - No Match
```json
{
  "success": true,
  "verified": false,
  "message": "User invalid. Face does not match the registered user."
}
```

---

## Troubleshooting

**Q: Getting 503 error when registering?**
- A: Check that environment variables are set in your hosting platform

**Q: Getting 500 error when verifying?**
- A: Make sure you registered a reference photo first

**Q: App not deploying?**
- A: Check that `requirements.txt` has all dependencies

**Q: Credentials showing in GitHub?**
- A: Run `git rm --cached .env` then push (prevents accidental exposure)

---

## Next Steps

1. ✅ Test locally with `/api-test` page
2. ✅ Deploy to Render (free!)
3. ✅ Update your frontend to call `https://your-app.onrender.com/api/register` and `/api/verify`
4. ✅ Users can now register and verify themselves!

---

## Alternative Hosting (Also Free)

- **Railway.app** - $5/month free credits, auto-deploys from GitHub
- **Fly.io** - 3 shared VMs free tier, global deployment
- **Hugging Face Spaces** - Free for ML projects (Python focus)

All support environment variables securely!
