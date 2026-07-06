import os
import shutil


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACE_FIXTURE = os.path.join(ROOT_DIR, "tests", "fixtures", "lena.jpg")


def ensure_test_face(destination: str) -> bool:
    if os.path.exists(destination):
        return False

    if not os.path.exists(FACE_FIXTURE):
        raise FileNotFoundError(
            f"Missing face test fixture at {FACE_FIXTURE}. "
            "Restore tests/fixtures/lena.jpg before running validation."
        )

    os.makedirs(os.path.dirname(destination), exist_ok=True)
    shutil.copyfile(FACE_FIXTURE, destination)
    print(f"Copied face test fixture to {destination}")
    return True
