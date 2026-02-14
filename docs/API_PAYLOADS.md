# API Payloads Reference

Sample request and response payloads for integration with the Face Auth API endpoints.

---

## POST /api/register

Register a new user with a reference face photo.

### Input: JSON with Base64 Image

```json
{
  "user_id": "alice",
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAIBAQIBAQICAgICAgICAwUDAwwDAwUGBAMFBwYHBwcGBwcICQsJCAgKCAcHCg0KCgsMDAwMBwkODw0MDgsMDAz/2wBDAQICAgMDAwYDAwYMCAcIDAwIDAwIDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAz/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8VAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCwAA8A/9k="
}
```

**Base64 Note:** The `image` field should be:
- Either full data URI: `data:image/jpeg;base64,<base64-string>` (system will strip prefix)
- Or raw base64 string: `<base64-string>` (system will decode directly)

To generate test base64 from a JPG file:
```bash
base64 -i your_photo.jpg
```

### Input: Form-Data with File Upload

```
POST /api/register HTTP/1.1
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="user_id"

alice
------WebKitFormBoundary
Content-Disposition: form-data; name="image"; filename="alice_ref.jpg"
Content-Type: image/jpeg

[BINARY IMAGE DATA]
------WebKitFormBoundary--
```

**curl example:**
```bash
curl -X POST http://localhost:5000/api/register \
  -F "user_id=alice" \
  -F "image=@alice_ref.jpg"
```

### Expected Success Response (200 OK)

```json
{
  "success": true,
  "message": "Reference photo stored successfully.",
  "user_id": "alice",
  "stored_key": "users/alice/ref_a1b2c3d4e5f6.jpg"
}
```

### Expected Error Responses

**Missing user_id (400 Bad Request):**
```json
{
  "success": false,
  "message": "user_id (or username) is required"
}
```

**Missing image (400 Bad Request):**
```json
{
  "success": false,
  "message": "image (file or base64) is required"
}
```

**S3 not configured (503 Service Unavailable):**
```json
{
  "success": false,
  "message": "S3 is not configured. Set S3_BUCKET (and AWS credentials) in environment."
}
```

**Upload failed (500 Internal Server Error):**
```json
{
  "success": false,
  "message": "Upload failed: [error details]"
}
```

---

## POST /api/verify

Verify a user's face against their registered reference photos.

### Input: JSON with Base64 Image

```json
{
  "user_id": "alice",
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAIBAQIBAQICAgICAgICAwUDAwwDAwUGBAMFBwYHBwcGBwcICQsJCAgKCAcHCg0KCgsMDAwMBwkODw0MDgsMDAz/2wBDAQICAgMDAwYDAwYMCAcIDAwIDAwIDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAz/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8VAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCwAA8A/9k="
}
```

### Input: Form-Data with File Upload

```
POST /api/verify HTTP/1.1
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="user_id"

alice
------WebKitFormBoundary
Content-Disposition: form-data; name="image"; filename="alice_live.jpg"
Content-Type: image/jpeg

[BINARY IMAGE DATA]
------WebKitFormBoundary--
```

**curl example:**
```bash
curl -X POST http://localhost:5000/api/verify \
  -F "user_id=alice" \
  -F "image=@alice_live.jpg"
```

### Expected Success Response (200 OK) — Face Matched

```json
{
  "success": true,
  "verified": true,
  "message": "User verified successfully."
}
```

### Expected Failure Response (200 OK) — Face Not Matched

```json
{
  "success": false,
  "verified": false,
  "message": "User invalid. Face does not match the registered user."
}
```

### Expected Error Responses

**Missing user_id (400 Bad Request):**
```json
{
  "success": false,
  "verified": false,
  "message": "user_id (or username) is required"
}
```

**Missing image (400 Bad Request):**
```json
{
  "success": false,
  "verified": false,
  "message": "image (file or base64) is required"
}
```

**No reference photos registered (404 Not Found):**
```json
{
  "success": false,
  "verified": false,
  "message": "No reference images found in S3 for user_id=alice"
}
```

**S3 not configured (503 Service Unavailable):**
```json
{
  "success": false,
  "verified": false,
  "message": "S3 is not configured. Set S3_BUCKET (and AWS credentials) in environment."
}
```

**Verification failed (500 Internal Server Error):**
```json
{
  "success": false,
  "verified": false,
  "message": "Verification failed: [error details]"
}
```

---

## Integration Notes

### Image Format Support
- **Formats:** JPEG, PNG
- **Size:** Recommended 256×256 px to 512×512 px (larger images will be auto-resized)
- **Quality:** 80+ JPEG quality (compression artifacts can hurt face detection)

### User ID Conventions
- Use lowercase alphanumeric: `alice`, `bob123`, `user_001`
- Avoid special chars; `-`, `_` are safe
- Max 64 characters recommended

### Response Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success (check `success` and `verified` flags in body) |
| 400 | Bad request (missing/invalid input) |
| 403 | Forbidden (auth required for `/verify` on UI) |
| 404 | Not found (no reference photos for user) |
| 500 | Server error (DeepFace/S3 failure) |
| 503 | Service unavailable (S3 not configured) |

### cURL Workflow Example

**1. Register alice:**
```bash
curl -X POST http://localhost:5000/api/register \
  -F "user_id=alice" \
  -F "image=@alice_reference.jpg" \
  | jq
```

**2. Verify alice:**
```bash
curl -X POST http://localhost:5000/api/verify \
  -F "user_id=alice" \
  -F "image=@alice_livecapture.jpg" \
  | jq
```

### Python Requests Example

```python
import requests
import base64

# Register
with open("alice_ref.jpg", "rb") as f:
    response = requests.post(
        "http://localhost:5000/api/register",
        json={
            "user_id": "alice",
            "image": "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()
        }
    )
print(response.json())

# Verify
with open("alice_live.jpg", "rb") as f:
    response = requests.post(
        "http://localhost:5000/api/verify",
        json={
            "user_id": "alice",
            "image": "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()
        }
    )
print(response.json())
```

### JavaScript/Fetch Example

```javascript
// Register from canvas or input file
async function register(userId, imageFile) {
  const formData = new FormData();
  formData.append("user_id", userId);
  formData.append("image", imageFile);
  
  const res = await fetch("/api/register", {
    method: "POST",
    body: formData
  });
  return await res.json();
}

// Verify from base64 canvas
async function verify(userId, canvasDataUrl) {
  const res = await fetch("/api/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: userId,
      image: canvasDataUrl  // "data:image/jpeg;base64,..."
    })
  });
  return await res.json();
}
```

---

## Debugging Tips

1. **Check logs:** App logs each step with timestamps (look for `[INFO]` lines with elapsed time).
2. **Test S3 access:** Verify `S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` are set.
3. **Face detection issues:** Ensure image is clear, well-lit, and face is centered and at least 80×80 px.
4. **Embedding mismatch:** High lighting/angle differences between registration and verification can reduce match confidence.
5. **Performance:** First verify is slower (embeddings computed); subsequent verifies use cached embeddings from S3.
