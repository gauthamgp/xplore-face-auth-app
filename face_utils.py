"""
Face verification utility: verify a captured image against reference images
in a user folder. Uses DeepFace (no dlib/CMake required).

Reference embeddings are precomputed and cached (in-memory, optional disk)
so we only compute the live image embedding at verify time.
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Tuple

import numpy as np

# Supported image extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# Detector backends to try in order. First ones handle side/angle/chin up-down better.
DETECTOR_BACKENDS = ("retinaface", "mtcnn", "opencv")

# Model: ArcFace is more robust to pose variation; fallback to Facenet.
VERIFICATION_MODEL = "ArcFace"

# Cosine distance threshold below which two faces are "same person" (model-dependent).
# DeepFace.verify() returns these; we use defaults so precomputed path matches verify() behavior.
DISTANCE_THRESHOLDS = {"ArcFace": 0.68, "Facenet": 0.40, "VGG-Face": 0.40}

# Cache filename inside each user folder (optional disk persistence)
EMBEDDINGS_CACHE_FILE = ".face_embeddings.pkl"


def get_user_folder(username: str, base_dir: str = "users") -> Path:
    """Return the path to the folder containing reference images for this user."""
    base = Path(base_dir)
    folder = base / username.strip().lower()
    return folder.resolve()


def _get_reference_image_paths(user_folder: Path):
    """Yield paths to image files in the user folder."""
    if not user_folder.exists() or not user_folder.is_dir():
        return
    for path in sorted(user_folder.iterdir()):
        if path.suffix.lower() in IMAGE_EXTENSIONS and path.name != EMBEDDINGS_CACHE_FILE:
            yield path


def _is_no_face_error(e: Exception) -> bool:
    err = str(e).lower()
    return "face could not be detected" in err or "no face" in err or ("detected" in err and "no " in err)


def _cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine distance between two vectors (0 = identical, 2 = opposite)."""
    a = np.asarray(a, dtype=np.float64).flatten()
    b = np.asarray(b, dtype=np.float64).flatten()
    n = np.linalg.norm(a) * np.linalg.norm(b)
    if n == 0:
        return 1.0
    return float(1.0 - np.dot(a, b) / n)


def _get_threshold(model_name: str) -> float:
    return DISTANCE_THRESHOLDS.get(model_name, DISTANCE_THRESHOLDS.get("Facenet", 0.4))


def _extract_embedding(
    image_path: str,
    model_name: str,
    detector_backend: str,
    align: bool = True,
    enforce_detection: bool = True,
):
    """Extract face embedding(s) from one image. Returns list of embedding vectors."""
    from deepface import DeepFace

    out = DeepFace.represent(
        img_path=image_path,
        model_name=model_name,
        detector_backend=detector_backend,
        align=align,
        enforce_detection=enforce_detection,
    )
    if not out:
        return []
    return [item["embedding"] for item in out if isinstance(item, dict) and "embedding" in item]


def _build_ref_embeddings(
    user_folder: Path,
    model_name: str,
    detector_backends: tuple[str, ...],
) -> list[tuple[np.ndarray, str]]:
    """Compute embeddings for all reference images. Returns list of (embedding, path)."""
    ref_paths = list(_get_reference_image_paths(user_folder))
    result: list[tuple[np.ndarray, str]] = []
    for path in ref_paths:
        for backend in detector_backends:
            try:
                embs = _extract_embedding(str(path), model_name, backend)
                for emb in embs:
                    result.append((np.asarray(emb), str(path)))
                break
            except Exception:
                continue
    return result


def _cache_key(user_folder: Path) -> Path:
    return user_folder.resolve()


# In-memory cache: key = (user_folder, model_name) -> { "embeddings": [...], "mtimes": {path: mtime} }
_embedding_cache: dict[tuple[Path, str], dict] = {}


def _folder_mtimes(user_folder: Path) -> dict[str, float]:
    """Return dict of path -> mtime for all reference image files."""
    mtimes = {}
    for path in _get_reference_image_paths(user_folder):
        try:
            mtimes[str(path)] = path.stat().st_mtime
        except OSError:
            pass
    return mtimes


def _load_cached_embeddings(
    user_folder: Path,
    model_name: str,
    detector_backends: tuple[str, ...],
    use_disk_cache: bool = True,
) -> list[tuple[np.ndarray, str]] | None:
    """
    Return cached reference embeddings if cache is valid (same files, same mtimes).
    Otherwise return None (caller should rebuild).
    """
    key = (_cache_key(user_folder), model_name)
    current_mtimes = _folder_mtimes(user_folder)
    if not current_mtimes:
        return None

    # In-memory
    if key in _embedding_cache:
        entry = _embedding_cache[key]
        if entry.get("mtimes") == current_mtimes and entry.get("embeddings"):
            return entry["embeddings"]

    # Disk
    if use_disk_cache:
        cache_path = user_folder / EMBEDDINGS_CACHE_FILE
        if cache_path.exists():
            try:
                with open(cache_path, "rb") as f:
                    data = pickle.load(f)
                if data.get("model_name") == model_name and data.get("mtimes") == current_mtimes:
                    raw = data.get("embeddings", [])
                    if raw:
                        embs = [(np.asarray(e), p) for e, p in raw]
                        _embedding_cache[key] = {"embeddings": embs, "mtimes": current_mtimes}
                        return embs
            except Exception:
                pass
    return None


def _save_cached_embeddings(
    user_folder: Path,
    model_name: str,
    embeddings: list[tuple[np.ndarray, str]],
    use_disk_cache: bool = True,
) -> None:
    """Store embeddings in memory and optionally on disk."""
    current_mtimes = _folder_mtimes(user_folder)
    key = (_cache_key(user_folder), model_name)
    _embedding_cache[key] = {"embeddings": embeddings, "mtimes": current_mtimes}

    if use_disk_cache and embeddings:
        cache_path = user_folder / EMBEDDINGS_CACHE_FILE
        try:
            with open(cache_path, "wb") as f:
                pickle.dump(
                    {
                        "model_name": model_name,
                        "mtimes": current_mtimes,
                        "embeddings": [(np.asarray(e).tolist(), p) for e, p in embeddings],
                    },
                    f,
                )
        except Exception:
            pass


def get_ref_embeddings(
    user_folder: Path,
    model_name: str | None = None,
    detector_backends: tuple[str, ...] = DETECTOR_BACKENDS,
    use_disk_cache: bool = True,
) -> list[tuple[np.ndarray, str]]:
    """
    Return list of (embedding, path) for all reference faces in user_folder.
    Uses in-memory and optional disk cache; recomputes only when folder contents change.
    """
    model = model_name or VERIFICATION_MODEL
    cached = _load_cached_embeddings(user_folder, model, detector_backends, use_disk_cache)
    if cached is not None:
        return [(np.asarray(e), p) for e, p in cached]
    embeddings = _build_ref_embeddings(user_folder, model, detector_backends)
    _save_cached_embeddings(user_folder, model, embeddings, use_disk_cache)
    return embeddings


def verify_image_file(
    image_path: str,
    user_folder: Path,
    model_name: str | None = None,
    detector_backends: tuple[str, ...] = DETECTOR_BACKENDS,
    enforce_detection: bool = True,
    align: bool = True,
    use_embedding_cache: bool = True,
) -> Tuple[bool, str]:
    """
    Verify that the face in image_path matches at least one reference face
    in user_folder. Reference embeddings are precomputed and cached when possible;
    only the live image embedding is computed on each call.
    Returns (verified, message).
    """
    from deepface import DeepFace

    if not Path(image_path).exists():
        return False, "Image file not found."

    ref_paths = list(_get_reference_image_paths(user_folder))
    if not ref_paths:
        return False, "No reference face images found for this user. Add photos to the user folder."

    no_face_message = (
        "No face detected in the captured image. "
        "Try facing the camera more directly, or ensure good lighting."
    )
    model = model_name or VERIFICATION_MODEL
    threshold = _get_threshold(model)

    # 1. Get precomputed reference embeddings (or build cache on first use)
    if use_embedding_cache:
        ref_embeddings = get_ref_embeddings(user_folder, model, detector_backends)
    else:
        ref_embeddings = _build_ref_embeddings(user_folder, model, detector_backends)

    if not ref_embeddings:
        return False, "No reference face images found for this user. Add photos to the user folder."

    # 2. Extract embedding for the live image (once per request)
    live_embedding = None
    for backend in detector_backends:
        try:
            embs = _extract_embedding(image_path, model, backend, align, enforce_detection)
            if embs:
                live_embedding = np.asarray(embs[0])
                break
        except Exception as e:
            if _is_no_face_error(e):
                return False, no_face_message
            continue

    if live_embedding is None:
        return False, no_face_message

    # 3. Compare to each reference embedding (fast: just vector distance)
    for ref_emb, _ in ref_embeddings:
        dist = _cosine_distance(live_embedding, ref_emb)
        if dist <= threshold:
            return True, f"Face verified (distance: {dist:.3f})"

    return False, "Face does not match the registered user."
