import shutil
import subprocess
import os

GITPATH="temp_git/PortableGit/cmd/git.exe"

def is_git_available():
    # 1. PATH上にgitがあるか確認
    if shutil.which("git") is None:
        return False

    # 2. 実際に実行できるか確認
    try:
        result = subprocess.run(
            ["git", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3
        )
        return result.returncode == 0
    except Exception:
        return False

def check_portable_git():  
    if os.path.exists(GITPATH):
        try:
            result = subprocess.run(
                [GITPATH, "--version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3
            )
            return result.returncode == 0
        except Exception:
            return False
    else:
        return False


def update_enacchi():
    if not os.path.exists(".git"):
        return False
    if is_git_available():
        result=subprocess.run(
            ["git", "pull"],
            cwd=".",  # リポジトリのあるフォルダ
            capture_output=True,
            text=True
        )
    elif check_portable_git():
        result=subprocess.run(
            [GITPATH, "pull"],
            cwd=".",  # リポジトリのあるフォルダ
            capture_output=True,
            text=True
        )
    else:
        return False
    if shutil.which("uv") is not None:
        subprocess.run(
            ["uv", "sync"],
            cwd=".",  # リポジトリのあるフォルダ
            capture_output=True,
            text=True
        )
    return result.returncode ==0