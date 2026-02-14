# Face Auth – API Reference for Frontend / DevOps

Base URL: your deployed app root (e.g. `https://api.yourcompany.com` or `http://localhost:5000`).

---

## 1. Register (store reference photo)

**Endpoint:** `POST /api/register`

**Purpose:** During sign-up, the user captures a reference photo. The frontend sends that image with a `user_id`; the backend stores it in S3 under `users/<user_id>/`.

**Request**

- **Content-Type:** `application/json` or `multipart/form-data`
- **JSON body:**
  ```json
  {
    "user_id": "alice",
    "image": "<base64 string or data URL>"
  }
  ```
  - `user_id` (or `username`): string, required.  
  - `image`: base64-encoded image, or data URL (e.g. `data:image/jpeg;base64,...`).

- **Form body (alternative):**
  - `user_id` (or `username`): string, required.  
  - `image`: file upload (e.g. from `<input type="file">` or camera blob).

**Response**

- **200**
  ```json
  {
    "success": true,
    "message": "Reference photo stored successfully.",
    "user_id": "alice",
    "stored_key": "users/alice/ref_abc123.jpg"
  }
  ```
- **400** – missing `user_id` or `image`
- **503** – S3 not configured (set `S3_BUCKET` and AWS credentials)
- **500** – upload failed (e.g. S3 error)

**Frontend flow:** After the user captures a photo during registration, send one request per photo (or multiple requests to store several angles). Use the same `user_id` for that user.

---

## 2. Verify (face check)

**Endpoint:** `POST /api/verify`

**Purpose:** User clicks “Verify yourself”. Frontend sends the captured face image and `user_id`. Backend downloads that user’s reference photos from S3, runs face recognition, and returns whether the face matches.

**Request**

- **Content-Type:** `application/json` or `multipart/form-data`
- **JSON body:**
  ```json
  {
    "user_id": "alice",
    "image": "<base64 string or data URL>"
  }
  ```
- **Form body (alternative):** `user_id` (or `username`) + `image` (file).

**Response**

- **200 – match**
  ```json
  {
    "success": true,
    "verified": true,
    "message": "User verified successfully."
  }
  ```
- **200 – no match**
  ```json
  {
    "success": false,
    "verified": false,
    "message": "User invalid. Face does not match the registered user."
  }
  ```
- **400** – missing `user_id` or `image`
- **404** – no reference photos for this user (register first)
- **503** – S3 not configured
- **500** – verification error

**Frontend flow:** On “Verify yourself”, capture one image, send it with the logged-in user’s `user_id`; show success or “User invalid” based on `verified` and `message`.

---

## Test UI

Open **`/api-test`** in the browser (e.g. `http://localhost:5000/api-test`) to:

1. **Register:** Enter User ID, open camera, capture, submit → calls `POST /api/register`.
2. **Verify:** Enter User ID, open camera, capture, submit → calls `POST /api/verify`.

Use this to validate the two flows before integrating into your UI.

---

## AWS and env

- **S3:** Reference images are stored in S3 with user-level segregation. See **[AWS_SETUP.md](AWS_SETUP.md)** for creating the bucket, IAM user/role, and required env vars (`S3_BUCKET`, `AWS_REGION`, and optionally `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`).
