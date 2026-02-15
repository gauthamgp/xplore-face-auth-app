# Debugging Verification Failures on EC2

Your verification is working locally but failing on EC2. Here's what I've done and what to check:

---

## Changes Made ✅

### 1. Added Comprehensive Logging to `face_utils.py`
- Logs every step of the verification process with timestamps
- Shows which detector backend is being used
- Displays embedding distances for each reference vs. live image
- Logs why verification failed (distance too high, face not detected, etc.)

### 2. Fixed OpenCV Conflict
- Removed `opencv-python` (GUI-based)
- Kept only `opencv-python-headless` (headless version for servers)
- This prevents library conflicts on EC2

---

## How to Debug on EC2

### Step 1: Verify Logs are Printed

When you call `/api/verify`, you should now see detailed logs like:

```
2026-02-15 10:30:45 [INFO] xplore.face_utils: verify_image_file: START image=/tmp/xxx.jpg, folder=/home/ubuntu/xplore/data/alice
2026-02-15 10:30:45 [INFO] xplore.face_utils:   model=ArcFace, cache=True, backends=('retinaface', 'mtcnn', 'opencv')
2026-02-15 10:30:45 [INFO] xplore.face_utils: verify_image_file: Found 2 reference images in /home/ubuntu/xplore/data/alice
2026-02-15 10:30:45 [INFO] xplore.face_utils: verify_image_file: Using model=ArcFace, threshold=0.68
2026-02-15 10:30:45 [INFO] xplore.face_utils: verify_image_file: Loading cached reference embeddings...
2026-02-15 10:30:47 [INFO] xplore.face_utils: verify_image_file: Got 2 reference embeddings (1.234s)
2026-02-15 10:30:47 [INFO] xplore.face_utils: verify_image_file: Trying detector backend=retinaface
2026-02-15 10:30:48 [DEBUG] xplore.face_utils: _extract_embedding: Got 1 embeddings (0.567s)
2026-02-15 10:30:48 [INFO] xplore.face_utils: verify_image_file: Successfully extracted embedding with retinaface
2026-02-15 10:30:48 [INFO] xplore.face_utils: verify_image_file: Comparing to 2 reference embeddings...
2026-02-15 10:30:48 [DEBUG] xplore.face_utils:   Ref[0] alice_ref1.jpg: dist=0.4521
2026-02-15 10:30:48 [DEBUG] xplore.face_utils:   Ref[1] alice_ref2.jpg: dist=0.6234
2026-02-15 10:30:48 [INFO] xplore.face_utils: verify_image_file: VERIFIED! dist=0.4521 <= 0.68 (2.500s)
```

### Step 2: Check for Common Issues

**Issue 1: "No face detected"**
```
xplore.face_utils: verify_image_file: No face detected
```
- **Cause:** Image quality or face angle is different on EC2
- **Fix:** Try with clearer, frontal face photos

**Issue 2: "FAILED! best_dist=0.75 > 0.68"**
```
verify_image_file: FAILED! best_dist=0.75 > 0.68 (1.234s)
```
- **Cause:** Face similarity is below threshold (models sometimes behave differently across environments)
- **Fix:** Possible causes:
  - Different image compression on EC2 vs local
  - Different TensorFlow/DeepFace versions
  - Different lighting conditions in test images

**Issue 3: "Got 0 reference embeddings"**
```
verify_image_file: Got 0 reference embeddings (0.001s)
```
- **Cause:** Reference images failed to extract embeddings
- **Fix:** Make sure registration worked and images exist in S3

---

## Why It Might Be Different on EC2 vs Local

### 1. DeepFace Model Differences
- Local and EC2 might have different model versions
- Different CPU architectures (Mac arm64 vs EC2 x86_64)
- Can lead to slight embedding differences

**Fix:** Pin DeepFace version in requirements.txt:
```
deepface==0.0.98
```

### 2. Image Quality/Processing
- JPEG compression might be different
- Image resize operations might differ slightly

**Fix:** Ensure same image preprocessing on both systems

### 3. Detector Backend Availability
- On EC2, some backends (retinaface, mtcnn) might behave differently
- Fallback to opencv might give different results

**Fix:** Try registering and verifying with exact same test images on both systems

---

## Deploy to EC2 and Test

```bash
# SSH into EC2
ssh -i key.pem ubuntu@ec2-ip

# Pull latest code
cd xplore && git pull

# Clean install
pip3 install -r requirements.txt --force-reinstall

# Create .env
cat > .env << 'EOF'
S3_BUCKET=xplore-face-auth-refs
AWS_REGION=us-east-1
SECRET_KEY=your-secret-key
VERIFICATION_MODEL=ArcFace
EOF

# Run app (logs will now be detailed)
uvicorn app:app --host 0.0.0.0 --port 5000

# In another terminal, test
curl -X POST http://localhost:5000/api/verify \
  -F "user_id=alice" \
  -F "image=@alice_test.jpg"
```

Watch the logs in the first terminal — you'll see exactly what's happening.

---

## Possible Root Causes & Fixes

### Cause 1: Detector Backend Failing on EC2

**Symptom:** Logs show `Backend retinaface failed` repeatedly

**Fix:** Try forcing a specific backend by modifying `face_utils.py`:
```python
DETECTOR_BACKENDS = ("opencv",)  # Force OpenCV only
```

Then redeploy. This rules out retinaface/mtcnn issues.

### Cause 2: Model Mismatch

**Symptom:** Local uses ArcFace v1, EC2 uses ArcFace v2 (different embeddings)

**Fix:** Ensure both systems have same DeepFace version:
```bash
pip install deepface==0.0.98  # Pin version
```

### Cause 3: Cached Embeddings from Different DeepFace Version

**Symptom:** Works fine for new users (fresh embeddings), fails for existing users (cached)

**Fix:** Delete cached embeddings on EC2:
```bash
# Remove all .face_embeddings.pkl files from S3 or local
find . -name ".face_embeddings.pkl" -delete

# Force recomputation on next verification
```

### Cause 4: Image Preprocessing Differences

**Symptom:** Same photo works locally but not on EC2

**Fix:** Check if `align=True` and `enforce_detection=True` flags are consistent. Try:
```python
verify_image_file(image_path, user_folder, align=False, enforce_detection=False)
```

---

## Quick Diagnostic Script

Run this on EC2 to check if face detection works:

```bash
python3 << 'EOF'
from deepface import DeepFace
import sys

image = sys.argv[1] if len(sys.argv) > 1 else "test.jpg"

try:
    result = DeepFace.represent(image, model_name="ArcFace", detector_backend="opencv")
    print(f"✓ Face detected and embedded successfully")
    print(f"  Embeddings: {len(result)}")
except Exception as e:
    print(f"✗ Error: {e}")
EOF

# Test
python3 diagnostic.py alice_test.jpg
```

---

## Next Steps

1. **Deploy the updated code** with logging to EC2
2. **Run a verification** and capture the full log output
3. **Share the logs** — they'll tell us exactly where it fails
4. **Apply the appropriate fix** from the causes list above

With detailed logging, we'll be able to see exactly what distances are computed and why they're not matching.
