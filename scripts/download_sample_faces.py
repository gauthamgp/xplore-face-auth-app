"""
Download sample face images into users/alice, users/bob, users/charlie
so you can test verification without adding your own photos first.
Uses example images from the face_recognition project (CC/public domain style use for demo).
"""
import urllib.request
from pathlib import Path

# Base directory: project root (parent of scripts/)
BASE = Path(__file__).resolve().parent.parent
USERS_BASE = BASE / "users"

# Sample images (face_recognition examples - one face per image for clear mapping)
SAMPLES = [
    ("alice", "https://raw.githubusercontent.com/ageitgey/face_recognition/master/examples/obama.jpg"),
    ("bob", "https://raw.githubusercontent.com/ageitgey/face_recognition/master/examples/biden.jpg"),
    ("charlie", "https://raw.githubusercontent.com/ageitgey/face_recognition/master/examples/obama2.jpg"),
]


def main():
    for username, url in SAMPLES:
        folder = USERS_BASE / username
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "ref1.jpg"
        try:
            urllib.request.urlretrieve(url, path)
            print(f"Downloaded {path}")
        except Exception as e:
            print(f"Could not download {url}: {e}")
    print("Done. Add more photos to each user folder for stronger verification.")


if __name__ == "__main__":
    main()
