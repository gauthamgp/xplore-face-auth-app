# Face Authentication App

A Python FastAPI app that verifies users by matching a live-captured face against reference photos stored per user. Use it to gate actions (e.g. form submit) behind face authentication.

## Features

- **3 users**: Alice, Bob, Charlie (simple sign-in by username)
- **Per-user reference photos**: Each user has a folder (`users/alice`, `users/bob`, `users/charlie`) where you store 3–5 photos of that person from different angles
- **Verify yourself**: From the dashboard, click “Verify yourself” to open the camera, capture a photo, and submit. The backend matches the face against that user’s folder
- **Strong matching**: Uses DeepFace (ArcFace/Facenet) and checks the captured face against every reference image in the user folder. Multiple detector backends (RetinaFace, MTCNN, OpenCV) are tried for better handling of side poses, chin up/down, and angled faces.
- **Clear outcome**: “Welcome, &lt;name&gt;!” on success, “User invalid” on failure

## Setup

### 1. Use Python 3.11 or 3.12 and create a virtual environment

**Important:** Use Python 3.11 or 3.12. Python 3.14 is not supported by TensorFlow/DeepFace (and building `dlib` on 3.14 can fail on some Macs).

```bash
python3.12 -m venv venv    # or python3.11 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

The app uses **DeepFace** for face verification (no dlib/CMake build required). DeepFace will download model files on first run (e.g. ArcFace, Facenet).

### 3. Add reference photos (or download samples)

**Option A – Sample images (quick test)**  
From the project root, run:

```bash
python scripts/download_sample_faces.py
```

This downloads one example face image into each user folder (from a public demo dataset). You can then sign in as **alice** or **bob** or **charlie** and verify using a photo of Obama/Biden (e.g. from the web or your camera pointed at the screen) to see the flow. Replace these with real user photos when you’re ready.

**Option B – Your own photos**  
- **users/alice/** – 3–5 photos of the person who will sign in as “alice”  
- **users/bob/** – 3–5 photos of the person who will sign in as “bob”  
- **users/charlie/** – 3–5 photos of the person who will sign in as “charlie”  

Use clear shots with good lighting. **For best results with side poses and chin up/down**, include at least one front-facing photo plus a few from different angles (e.g. slight side, chin up, chin down). Supported formats: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp`.  
Until there are valid face images in a user’s folder, verification will report “No reference face images found for this user.”

**Optional – better pose detection:** For stronger detection of non-frontal faces, you can install RetinaFace (e.g. `pip install retina-face`). The app will try RetinaFace first, then MTCNN, then OpenCV.

### 4. Run the app

```bash
python app.py
```

Or with uvicorn directly:

```bash
uvicorn app:app --reload --host 127.0.0.1 --port 5000
```

Open http://127.0.0.1:5000 in your browser. Sign in as one of the three users, then use “Verify yourself” to capture and submit a face; the app will verify against that user’s folder and show success or “User invalid.”

## Project layout

```
.
├── app.py              # FastAPI app: login, dashboard, /verify
├── face_utils.py       # Load reference encodings, verify face (tolerance, multi-image)
├── requirements.txt
├── users/
│   ├── alice/          # Reference photos for user alice
│   ├── bob/            # Reference photos for user bob
│   └── charlie/        # Reference photos for user charlie
├── static/
│   ├── style.css
│   └── app.js          # Camera capture, submit to /verify, toast
└── templates/
    ├── login.html
    └── dashboard.html
```

## APIs for frontend / DevOps (S3-backed)

Two APIs are exposed for integration:

| API | Method | Purpose |
|-----|--------|--------|
| **Register** | `POST /api/register` | Store a reference photo for a user (body: `user_id` + `image` base64 or file). Stored in S3 under `users/<user_id>/`. |
| **Verify** | `POST /api/verify` | Verify a user by face (body: `user_id` + `image`). Compares against that user’s reference photos in S3; returns `verified` and message. |

- **Test UI:** Open **[/api-test](http://127.0.0.1:5000/api-test)** to mimic both flows (register then verify) with camera capture.
- **API details:** [docs/API_REFERENCE.md](docs/API_REFERENCE.md)
- **AWS (S3 + IAM):** [docs/AWS_SETUP.md](docs/AWS_SETUP.md) — bucket, IAM policy, and env vars (`S3_BUCKET`, `AWS_REGION`, credentials).

## Documentation

- **[DOCUMENTATION.md](DOCUMENTATION.md)** — Full technical explanation: how the app works, how face verification works, what data is used, when it can break, and how to explain it to a non-technical audience.
- **[docs/FLOW_DIAGRAM.md](docs/FLOW_DIAGRAM.md)** — End-to-end and verification flow diagrams (Mermaid). Paste into [mermaid.live](https://mermaid.live) to export as PNG/SVG.

## Security note

This is a demo/utility app. For production you would add proper authentication (e.g. passwords or SSO), HTTPS, and secure session handling; face verification would then be an additional factor.
