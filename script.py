#!/usr/bin/env python3
"""
Termux Git Server for AutoGit (Android).

Run this script inside Termux so AutoGit can manage local git repositories
via HTTP on localhost. The script creates ~/Repositories and serves git
operations (list, init, clone, run).

Usage in Termux:
  pkg install python git
  cd ~
  python3 path/to/termux_git_server.py

Or run in background:
  nohup python3 termux_git_server.py > /dev/null 2>&1 &
"""

import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

HOST = "127.0.0.1"
PORT = 8765
REPOS_DIR = os.path.expanduser("~/Repositories")


def ensure_repos_dir():
    os.makedirs(REPOS_DIR, exist_ok=True)


def is_git_dir(path):
    return os.path.isdir(os.path.join(path, ".git"))


def get_repos():
    ensure_repos_dir()
    result = []
    for name in sorted(os.listdir(REPOS_DIR)):
        if name.startswith("."):
            continue
        full = os.path.join(REPOS_DIR, name)
        if not os.path.isdir(full) or not is_git_dir(full):
            continue
        current_branch = None
        is_clean = None
        try:
            r = subprocess.run(
                ["git", "-C", full, "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if r.returncode == 0:
                current_branch = (r.stdout or "").strip() or None
            r2 = subprocess.run(
                ["git", "-C", full, "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            is_clean = r2.returncode == 0 and (r2.stdout or "").strip() == ""
        except Exception:
            pass
        result.append({
            "name": name,
            "path": full,
            "currentBranch": current_branch,
            "isClean": is_clean,
        })
    return result


def init_repo(name):
    if not name or "/" in name or "\\" in name or name.startswith("."):
        raise ValueError("Invalid repo name")
    ensure_repos_dir()
    full = os.path.join(REPOS_DIR, name)
    if os.path.exists(full):
        raise FileExistsError(f"A directory named \"{name}\" already exists")
    subprocess.run(["git", "init", full], check=True, capture_output=True, timeout=10)
    return {"name": name, "path": full}


def clone_repo(url, name=None):
    if not url:
        raise ValueError("Clone URL required")
    ensure_repos_dir()
    if name is None:
        name = url.rstrip("/").split("/")[-1].removesuffix(".git") or "repo"
    if "/" in name or "\\" in name or name.startswith("."):
        raise ValueError("Invalid repo name")
    full = os.path.join(REPOS_DIR, name)
    if os.path.exists(full):
        raise FileExistsError(f"A directory named \"{name}\" already exists")
    subprocess.run(
        ["git", "clone", url, full],
        check=True,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return {"name": name, "path": full}


def run_git(repo_name, args):
    if not args:
        return ""
    full = os.path.join(REPOS_DIR, repo_name)
    if not is_git_dir(full):
        raise FileNotFoundError(f"Not a git repository: {repo_name}")
    r = subprocess.run(
        ["git", "-C", full] + args,
        capture_output=True,
        text=True,
        timeout=60,
    )
    out = (r.stdout or "").strip()
    err = (r.stderr or "").strip()
    if r.returncode != 0 and err:
        raise RuntimeError(err)
    return out if out else err


class Handler(BaseHTTPRequestHandler):
    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _error(self, message, status=400):
        self._json({"error": message}, status=status)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return None
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        if urlparse(self.path).path == "/repos":
            try:
                self._json(get_repos())
            except Exception as e:
                self._error(str(e), 500)
        elif urlparse(self.path).path == "/health":
            self._json({"ok": True, "reposDir": REPOS_DIR})
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_json() or {}

        if path == "/init":
            name = body.get("name")
            if not name:
                self._error("Missing 'name'")
                return
            try:
                self._json(init_repo(name), 201)
            except FileExistsError as e:
                self._error(str(e), 409)
            except ValueError as e:
                self._error(str(e), 400)
            except Exception as e:
                self._error(str(e), 500)

        elif path == "/clone":
            url = body.get("url")
            if not url:
                self._error("Missing 'url'")
                return
            try:
                self._json(clone_repo(url, body.get("name")), 201)
            except FileExistsError as e:
                self._error(str(e), 409)
            except ValueError as e:
                self._error(str(e), 400)
            except subprocess.CalledProcessError as e:
                self._error((e.stderr or e.stdout or str(e)).strip(), 400)
            except Exception as e:
                self._error(str(e), 500)

        elif path == "/run":
            repo = body.get("repo")
            args = body.get("args")
            if not repo or not isinstance(args, list):
                self._error("Missing 'repo' or 'args' (list)")
                return
            try:
                self._json({"output": run_git(repo, args)})
            except FileNotFoundError as e:
                self._error(str(e), 404)
            except RuntimeError as e:
                self._error(str(e), 400)
            except Exception as e:
                self._error(str(e), 500)

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        print(format % args, file=sys.stderr)


def main():
    ensure_repos_dir()
    print(f"Repositories directory: {REPOS_DIR}", file=sys.stderr)
    print(f"Serving at http://{HOST}:{PORT}", file=sys.stderr)
    server = HTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
