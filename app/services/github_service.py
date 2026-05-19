import re
import base64
from typing import Optional

import requests

from app.config import settings


# ─────────────────────────────────────────
# YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────

def _parse_repo_url(url: str) -> tuple[str, str]:
    """
    GitHub URL'inden owner ve repo adını çıkarır.

    Desteklenen formatlar:
    - https://github.com/owner/repo
    - https://github.com/owner/repo.git
    - https://github.com/owner/repo/tree/main
    """
    pattern = r"github\.com/([^/]+)/([^/\s]+?)(?:\.git)?(?:/.*)?$"
    match = re.search(pattern, url.strip())

    if not match:
        raise ValueError(f"Geçersiz GitHub URL'i: {url}")

    owner = match.group(1)
    repo  = match.group(2)
    return owner, repo


def _get_headers() -> dict:
    """
    GitHub API için header'ları döndürür.
    Token varsa Authorization ekler.
    """
    headers = {"Accept": "application/vnd.github+json"}

    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    return headers


def _get_default_branch(owner: str, repo: str, headers: dict) -> str:
    """
    Repo'nun default branch adını çeker (main, master vb.)
    """
    url      = f"https://api.github.com/repos/{owner}/{repo}"
    response = requests.get(url, headers=headers, timeout=15)

    if response.status_code == 404:
        raise ValueError(f"Repo bulunamadı veya private: {owner}/{repo}")

    if response.status_code == 403:
        raise ValueError("GitHub API rate limit aşıldı. GITHUB_TOKEN ekleyiniz.")

    response.raise_for_status()
    return response.json().get("default_branch", "main")


def _get_file_tree(owner: str, repo: str, branch: str, headers: dict) -> list[dict]:
    """
    Repo'nun tüm dosya ağacını çeker (recursive).
    """
    url = (
        f"https://api.github.com/repos/{owner}/{repo}"
        f"/git/trees/{branch}?recursive=1"
    )
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    data = response.json()

    if data.get("truncated"):
        # 100.000+ dosyalı repolar için GitHub tree'yi kesiyor
        # Bu proje için nadir ama loglayalım
        print(f"[WARN] {owner}/{repo} ağacı truncated — bazı dosyalar atlanabilir.")

    return data.get("tree", [])


def _fetch_file_content(owner: str, repo: str, path: str, headers: dict) -> Optional[str]:
    """
    Tek bir dosyanın içeriğini base64'ten decode ederek döndürür.
    """
    url      = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    response = requests.get(url, headers=headers, timeout=15)

    if response.status_code != 200:
        return None

    data = response.json()

    # Encoding her zaman base64 olmalı ama kontrol edelim
    if data.get("encoding") != "base64":
        return None

    try:
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return content
    except Exception:
        return None


# ─────────────────────────────────────────
# ANA FONKSİYON
# ─────────────────────────────────────────

def fetch_repo_files(
    github_url: str,
    max_files: int = 25,
    file_extensions: list[str] = None,
) -> dict:
    """
    GitHub repo URL'inden Python dosyalarını çeker.

    Döndürür:
    {
        "owner": str,
        "repo": str,
        "branch": str,
        "total_found": int,       # uzantıya uyan toplam dosya
        "fetched": int,           # gerçekten indirilen dosya
        "files": [
            {
                "path": str,
                "content": str,
                "size": int,      # karakter sayısı
            },
            ...
        ]
    }
    """
    if file_extensions is None:
        file_extensions = [".py"]

    headers         = _get_headers()
    owner, repo     = _parse_repo_url(github_url)
    branch          = _get_default_branch(owner, repo, headers)
    tree            = _get_file_tree(owner, repo, branch, headers)

    # Sadece istenen uzantılı ve blob (dosya) olan node'ları al
    candidates = [
        node for node in tree
        if node.get("type") == "blob"
        and any(node["path"].endswith(ext) for ext in file_extensions)
    ]

    total_found = len(candidates)

    # max_files limitini uygula — küçük dosyaları önce al (size'a göre sırala)
    candidates = sorted(candidates, key=lambda x: x.get("size", 0))
    candidates = candidates[:max_files]

    # Dosya içeriklerini indir
    files = []
    for node in candidates:
        content = _fetch_file_content(owner, repo, node["path"], headers)
        if content is not None:
            files.append({
                "path":    node["path"],
                "content": content,
                "size":    len(content),
            })

    return {
        "owner":       owner,
        "repo":        repo,
        "branch":      branch,
        "total_found": total_found,
        "fetched":     len(files),
        "files":       files,
    }