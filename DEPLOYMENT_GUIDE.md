# Deployment & API Guide

## API Endpoints

### 1. **POST /api/register** - Register a user with reference photo(s)

**Purpose:** Store a reference photo for a user in S3 for later face verification.

**Input Format (JSON):**
```json
{
  "user_id": "alice",
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAA..." 
}
```

**Input Format (Form Data/Multipart):**
```
user_id: alice
image: <binary file data>
```

**Response (Success - 200):**
```json
{
  "success": true,
  "message": "Reference photo stored successfully.",
  "user_id": "alice",
  "stored_key": "users/alice/ref_uuid.jpg"
}
```

**Response (Error - 400/500/503):**
```json
{
  "success": false,
  "message": "Error description here"
}
```

---

### 2. **POST /api/verify** - Verify a user's face

**Purpose:** Compare a submitted face image against the user's reference photos stored in S3.

**Input Format (JSON):**
```json
{
  "user_id": "alice",
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAA..."
}
```

**Input Format (Form Data/Multipart):**
```
user_id: alice
image: <binary file data>
```

**Response (Success - 200):**
```json
{
  "success": true,
  "verified": true,
  "message": "Face matches registered user.",
  "user_id": "alice"
}
```

**Response (No Match - 200):**
```json
{
  "success": true,
  "verified": false,
  "message": "User invalid. Face does not match the registered user."
}
```

**Response (Error - 400/500/503):**
```json
{
  "success": false,
  "verified": false,
  "message": "Error description here"
}
```

---

## Frontend Example Code

### JavaScript - Register API Call
```javascript
async function registerUser(username, imageBase64) {
  const response = await fetch('/api/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      user_id: username,
      image: imageBase64
    })
  });
  
  const result = await response.json();
  if (result.success) {
    console.log('✓ Registered:', result.stored_key);
  } else {
    console.error('✗ Error:', result.message);
  }
}
```

### JavaScript - Verify API Call
```javascript
async function verifyUser(username, imageBase64) {
  const response = await fetch('/api/verify', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      user_id: username,
      image: imageBase64
    })
  });
  
  const result = await response.json();
  if (result.verified) {
    console.log('✓ Face verified!');
  } else {
    console.log('✗ Face mismatch.');
  }
}
```

---

## FREE Hosting Options (No Credentials Exposure)

### **Option 1: Render (Recommended)**
- **Free tier:** 750 hours/month
- **Setup:** Auto-deploys from GitHub
- **Credentials:** Uses environment variables (NOT in code)
- **Cost:** Free for hobby projects

**Steps:**
1. Push code to GitHub (without `.env` file)
2. Connect Render to GitHub repo
3. Create new Web Service on Render
4. Set environment variables in Render dashboard:
   - `S3_BUCKET`
   - `AWS_REGION`
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
5. Deploy!

**Link:** https://render.com

---

### **Option 2: Railway**
- **Free tier:** $5/month credits
- **Setup:** Git-based deployment
- **Credentials:** Secure environment variable storage

**Steps:**
1. Push code to GitHub
2. Connect Railway to your repo
3. Add environment variables in Railway dashboard
4. Deploy automatically

**Link:** https://railway.app

---

### **Option 3: Fly.io**
- **Free tier:** 3 shared-cpu-1x 256MB VMs
- **Credentials:** Stored securely in Fly Secrets
- **Global:** Deployed near users

**Steps:**
```bash
flyctl auth login
flyctl launch  # In your app directory
# Follow prompts, then set secrets:
flyctl secrets set S3_BUCKET=xplore-face-auth-refs
flyctl secrets set AWS_REGION=us-east-1
flyctl secrets set AWS_ACCESS_KEY_ID=your-key
flyctl secrets set AWS_SECRET_ACCESS_KEY=your-secret
flyctl deploy
```

**Link:** https://fly.io

---

## **How to Keep Credentials SAFE**

### ❌ **NEVER DO THIS:**
```python
# BAD - Hardcoded credentials
S3_BUCKET = "my-bucket"
AWS_ACCESS_KEY_ID = "AKIASIHBA36DZFF2SKXL"
```

```python
# BAD - Credentials in code
app.py contains: 
AWS_SECRET = "QZePgLOQHZmoP52oyDjEEJhri/tpqJZ/fJtGeBe9"
```

### ✅ **DO THIS INSTEAD:**

**1. Use Environment Variables (Current Setup)**
```python
# app.py & s3_utils.py (already set up)
S3_BUCKET = os.environ.get("S3_BUCKET", "placeholder")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
```

**2. Local Development: Use `.env` file (NEVER commit to Git)**
```bash
# .env (DO NOT PUSH TO GITHUB)
S3_BUCKET=xplore-face-auth-refs
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIASIHBA36DZFF2SKXL
AWS_SECRET_ACCESS_KEY=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
```

**3. Production: Use Hosting Platform Env Variables**
```bash
# Render, Railway, Fly dashboard sets these:
# S3_BUCKET → xplore-face-auth-refs
# AWS_REGION → us-east-1
# AWS_ACCESS_KEY_ID → AKIASIHBA36DZFF2SKXL
# AWS_SECRET_ACCESS_KEY → QZePgLOQHZmoP52oyDjEEJhri/tpqJZ/fJtGeBe9
```

---

## **GitHub Setup (Safe Deployment)**

### **Step 1: Add `.gitignore` (if not present)**
```bash
# .gitignore
.env
.env.local
__pycache__/
*.pyc
venv/
.DS_Store
```

This prevents accidentally pushing `.env` with credentials!

### **Step 2: Push to GitHub**
```bash
git add .
git commit -m "Add face auth app with safe credential handling"
git push origin main
```

### **Step 3: Deploy to Render/Railway/Fly**
- Connect your GitHub repo
- Set environment variables in their dashboard
- No credentials in your git history! ✓

---

## **API Testing from Frontend**

### **Using Fetch API (Browser JavaScript)**

**Capture image from camera:**
```javascript
// Get canvas from video stream
const canvas = document.getElementById('canvas');
const context = canvas.getContext('2d');
// Draw from video element
context.drawImage(videoElement, 0, 0, canvas.width, canvas.height);

// Convert to base64
const imageBase64 = canvas.toDataURL('image/jpeg');

// Remove 'data:image/jpeg;base64,' prefix if needed
const base64String = imageBase64.split(',')[1];
```

**Register:**
```javascript
const registerResponse = await fetch('https://your-app.onrender.com/api/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: document.getElementById('username').value,
    image: imageBase64
  })
});
```

**Verify:**
```javascript
const verifyResponse = await fetch('https://your-app.onrender.com/api/verify', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: document.getElementById('username').value,
    image: imageBase64
  })
});
```

---

## **Recommended Deployment Path**

1. ✅ **Local Testing** → Confirm app works with `.env` file
2. ✅ **GitHub** → Push code (without `.env`)
3. ✅ **Render** → Connect GitHub repo, add env vars
4. ✅ **Share URL** → Anyone can use your API!

**Your deployed endpoints will be:**
- `https://your-app-name.onrender.com/api/register`
- `https://your-app-name.onrender.com/api/verify`

---

## **AWS Credentials Security Note**

The credentials in your `.env` are **AWS Access Keys**. Consider:

1. **Rotate them periodically** in AWS Console
2. **Use IAM role** if deploying to AWS EC2/Lambda instead
3. **Limit permissions** - Create IAM user with S3-only access
4. **Monitor usage** - Set up CloudTrail alerts for unusual activity

For production, use AWS IAM roles instead of hardcoded keys!

---

## **Testing Your Deployed API**

Once deployed, test with curl:

```bash
# Register
curl -X POST https://your-app.onrender.com/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "image": "data:image/jpeg;base64,..."
  }'

# Verify
curl -X POST https://your-app.onrender.com/api/verify \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "image": "data:image/jpeg;base64,..."
  }'
```
