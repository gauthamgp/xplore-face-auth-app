"""
Face Authentication App: login as a user, fill a form, and verify yourself
via camera. Backend matches the captured face against reference images in
the user's folder (local or S3). FastAPI version.

Exposes two APIs for frontend/DevOps integration:
- POST /api/register: register user with reference photo(s) → stored in S3
- POST /api/verify: verify user by face image → compare against S3 refs
"""
import os
import base64
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

# Load environment variables from .env file
load_dotenv()

# Reduce TensorFlow log noise and limit CPU threads to reduce contention on Render
# Set these before any TensorFlow/DeepFace import so they take effect early.
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
from face_utils import get_user_folder, verify_image_file
from s3_utils import (
    upload_reference_image,
    download_user_refs_to_temp_dir,
    upload_embeddings_cache,
    S3_BUCKET,
)

app = FastAPI(title="Face Auth App")

# Session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SECRET_KEY", "dev-secret-change-in-production"),
    max_age=86400,  # 24 hours
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# In-memory user store (no password for demo; you can add later)
USERS = {"alice": "Alice", "bob": "Bob", "charlie": "Charlie"}
USERNAMES = list(USERS.keys())

# Base directory for user face folders
USERS_BASE = Path(__file__).resolve().parent / "users"


def ensure_user_folders():
    """Create user folders if they don't exist."""
    for u in USERNAMES:
        folder = USERS_BASE / u
        folder.mkdir(parents=True, exist_ok=True)


def get_username(request: Request) -> Optional[str]:
    """Get username from session."""
    return request.session.get("username")


def require_auth(request: Request) -> str:
    """Require authentication, return username or raise 401."""
    username = get_username(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not logged in")
    return username


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Redirect to dashboard if logged in, else login."""
    if request.session.get("username"):
        return RedirectResponse(url="/dashboard", status_code=303)
    return RedirectResponse(url="/login", status_code=303)


@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    """Show login page."""
    return templates.TemplateResponse("login.html", {"request": request, "users": USERS})


@app.post("/login", response_class=RedirectResponse)
async def login_post(request: Request, username: str = Form(...)):
    """Handle login form submission."""
    username = username.strip().lower()
    if username in USERS:
        request.session["username"] = username
        request.session["display_name"] = USERS[username]
        return RedirectResponse(url="/dashboard", status_code=303)
    return RedirectResponse(url="/login", status_code=303)


@app.get("/logout", response_class=RedirectResponse)
async def logout(request: Request):
    """Clear session and redirect to login."""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Show dashboard (requires auth)."""
    username = get_username(request)
    if not username:
        return RedirectResponse(url="/login", status_code=303)
    
    display_name = request.session.get("display_name", username)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "username": username,
            "display_name": display_name,
        },
    )


@app.post("/verify")
async def verify(request: Request):
    """Verify face from uploaded image or base64 data."""
    username = require_auth(request)
    user_folder = get_user_folder(username, str(USERS_BASE))

    # Accept either file upload or base64 image (from canvas)
    image_data = None
    content_type = request.headers.get("content-type", "")
    
    # Try JSON body first (base64 from canvas - most common case)
    if "application/json" in content_type:
        try:
            data = await request.json()
            raw = data.get("image") or data.get("image_base64") or ""
            if raw.startswith("data:"):
                raw = raw.split(",", 1)[-1]
            if raw:
                image_data = base64.b64decode(raw)
        except Exception:
            pass
    
    # Try form data (file upload)
    if not image_data and ("multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type):
        try:
            form = await request.form()
            if "image" in form:
                file = form["image"]
                if hasattr(file, "read"):
                    image_data = await file.read()
                elif hasattr(file, "file"):
                    image_data = await file.file.read()
        except Exception:
            pass

    if not image_data:
        return JSONResponse(
            {"success": False, "message": "No image received"},
            status_code=400,
        )

    suffix = ".jpg"
    if "png" in content_type:
        suffix = ".png"
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(image_data)
        tmp_path = tmp.name
    
    try:
        verified, message = verify_image_file(tmp_path, user_folder)
        display_name = request.session.get("display_name", username)
        
        if verified:
            return JSONResponse({
                "success": True,
                "message": f"Welcome, {display_name}! Authentication successful.",
                "verified": True,
            })
        else:
            return JSONResponse({
                "success": False,
                "message": "User invalid. Face does not match the registered user.",
                "verified": False,
            })
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# -----------------------------------------------------------------------------
# Public APIs for frontend / DevOps (S3-backed, user_id in request)
# -----------------------------------------------------------------------------


def _parse_json_payload(body: bytes) -> tuple[str | None, bytes | None, str]:
    """From JSON body return (user_id, image_bytes, suffix)."""
    import json
    data = json.loads(body) if body else {}
    user_id = (data.get("user_id") or data.get("username") or "").strip() or None
    raw = data.get("image") or data.get("image_base64") or ""
    if raw.startswith("data:"):
        raw = raw.split(",", 1)[-1]
    image_data = base64.b64decode(raw) if raw else None
    suffix = "png" if "png" in (data.get("content_type") or "") else "jpg"
    return user_id, image_data, suffix


@app.post("/api/register")
async def api_register(request: Request):
    """
    Registration API: store a reference photo for a user in S3.
    Body (JSON): { "user_id": "alice", "image": "<base64>" }
    or form-data: user_id, image (file).
    Returns stored S3 key and success message.
    """
    content_type = request.headers.get("content-type", "")
    user_id = None
    image_data = None
    suffix = "jpg"

    if "application/json" in content_type:
        body = await request.body()
        user_id, image_data, suffix = _parse_json_payload(body)
    elif "multipart" in content_type or "form-urlencoded" in content_type:
        form = await request.form()
        user_id = (form.get("user_id") or form.get("username") or "").strip() or None
        if "image" in form:
            file = form["image"]
            if hasattr(file, "read"):
                image_data = await file.read()
            elif hasattr(file, "file"):
                image_data = await file.file.read()
            fn = getattr(file, "filename", "") or ""
            if fn.lower().endswith(".png"):
                suffix = "png"

    if not user_id:
        return JSONResponse(
            {"success": False, "message": "user_id (or username) is required"},
            status_code=400,
        )
    if not image_data:
        return JSONResponse(
            {"success": False, "message": "image (file or base64) is required"},
            status_code=400,
        )

    if S3_BUCKET == "YOUR_BUCKET_NAME_PLACEHOLDER":
        return JSONResponse(
            {
                "success": False,
                "message": "S3 is not configured. Set S3_BUCKET (and AWS credentials) in environment.",
            },
            status_code=503,
        )

    try:
        key = upload_reference_image(user_id, image_data, file_extension=suffix)
        
        # Precompute and cache embeddings during registration for faster first verification
        try:
            from pathlib import Path
            from face_utils import get_ref_embeddings
            
            tmp_refs_dir = download_user_refs_to_temp_dir(user_id)
            # This will compute embeddings and save to .face_embeddings.pkl
            get_ref_embeddings(Path(tmp_refs_dir), use_disk_cache=True)
            # Upload cache back to S3
            cache_file = Path(tmp_refs_dir) / ".face_embeddings.pkl"
            upload_embeddings_cache(user_id, cache_file)
            # Cleanup
            import shutil
            shutil.rmtree(tmp_refs_dir)
        except Exception as e:
            # Non-critical: if precomputation fails, embeddings will be computed on first verify
            print(f"Warning: Could not precompute embeddings for {user_id}: {e}")
        
        return JSONResponse({
            "success": True,
            "message": "Reference photo stored successfully.",
            "user_id": user_id,
            "stored_key": key,
        })
    except Exception as e:
        return JSONResponse(
            {"success": False, "message": f"Upload failed: {e}"},
            status_code=500,
        )


@app.post("/api/verify")
async def api_verify(request: Request):
    """
    Verification API: compare submitted face image against user's reference photos in S3.
    Body (JSON): { "user_id": "alice", "image": "<base64>" }
    or form-data: user_id, image (file).
    Returns verified (bool) and message.
    """
    content_type = request.headers.get("content-type", "")
    user_id = None
    image_data = None
    suffix = "jpg"

    if "application/json" in content_type:
        body = await request.body()
        user_id, image_data, suffix = _parse_json_payload(body)
    elif "multipart" in content_type or "form-urlencoded" in content_type:
        form = await request.form()
        user_id = (form.get("user_id") or form.get("username") or "").strip() or None
        if "image" in form:
            file = form["image"]
            if hasattr(file, "read"):
                image_data = await file.read()
            elif hasattr(file, "file"):
                image_data = await file.file.read()
            fn = getattr(file, "filename", "") or ""
            if fn.lower().endswith(".png"):
                suffix = "png"

    if not user_id:
        return JSONResponse(
            {"success": False, "verified": False, "message": "user_id (or username) is required"},
            status_code=400,
        )
    if not image_data:
        return JSONResponse(
            {"success": False, "verified": False, "message": "image (file or base64) is required"},
            status_code=400,
        )

    if S3_BUCKET == "YOUR_BUCKET_NAME_PLACEHOLDER":
        return JSONResponse(
            {
                "success": False,
                "verified": False,
                "message": "S3 is not configured. Set S3_BUCKET (and AWS credentials) in environment.",
            },
            status_code=503,
        )

    tmp_live = None
    tmp_refs_dir = None
    try:
        tmp_live = tempfile.NamedTemporaryFile(delete=False, suffix=f".{suffix}")
        tmp_live.write(image_data)
        tmp_live.close()
        tmp_refs_dir = download_user_refs_to_temp_dir(user_id)
        verified, detail = verify_image_file(
            tmp_live.name,
            tmp_refs_dir,
            use_embedding_cache=True,  # ENABLED: Cache embeddings locally
        )
        # Upload embeddings cache back to S3 for persistence
        try:
            cache_file = Path(tmp_refs_dir) / ".face_embeddings.pkl"
            upload_embeddings_cache(user_id, cache_file)
        except Exception:
            pass  # Non-critical if cache upload fails
        
        if verified:
            return JSONResponse({
                "success": True,
                "verified": True,
                "message": f"User verified successfully.",
            })
        else:
            return JSONResponse({
                "success": False,
                "verified": False,
                "message": "User invalid. Face does not match the registered user.",
            })
    except FileNotFoundError as e:
        return JSONResponse(
            {"success": False, "verified": False, "message": str(e) or "No reference photos found for this user. Register first."},
            status_code=404,
        )
    except Exception as e:
        return JSONResponse(
            {"success": False, "verified": False, "message": f"Verification failed: {e}"},
            status_code=500,
        )
    finally:
        if tmp_live and os.path.exists(tmp_live.name):
            try:
                os.unlink(tmp_live.name)
            except Exception:
                pass
        if tmp_refs_dir and os.path.exists(tmp_refs_dir):
            try:
                shutil.rmtree(tmp_refs_dir)
            except Exception:
                pass


@app.get("/api-test", response_class=HTMLResponse)
async def api_test_page(request: Request):
    """Simple test UI to mimic register and verify flows against /api/register and /api/verify."""
    return templates.TemplateResponse("api_test.html", {"request": request})


if __name__ == "__main__":
    import uvicorn
    ensure_user_folders()
    uvicorn.run(app, host="127.0.0.1", port=5000, reload=True)
