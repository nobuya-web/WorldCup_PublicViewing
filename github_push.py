#!/usr/bin/env python3
"""
github_push.py
W杯観戦ガイドの index.html / new_venues.js を GitHub Pages に自動プッシュするスクリプト。
毎朝7時のスケジュールタスクから呼び出されます。

【初回セットアップ】
1. GitHub の Settings > Developer settings > Personal access tokens で
   "Contents" 書き込み権限付きのトークンを発行する
2. 同フォルダの github_config.json を開き "token" にそのトークンを貼り付ける
3. このスクリプトを一度手動実行してテストする:
     python github_push.py
"""

import json, base64, sys
from pathlib import Path
import urllib.request, urllib.error

# ── パス設定 ───────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "github_config.json"
FILES_TO_PUSH = ["index.html", "new_venues.js"]

# ── 設定読み込み ───────────────────────────────────────────────
def load_config():
    if not CONFIG_FILE.exists():
        print("❌ github_config.json が見つかりません")
        sys.exit(1)
    cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    if cfg.get("token", "").startswith("YOUR_"):
        print("❌ github_config.json の token を設定してください")
        sys.exit(1)
    return cfg

# ── GitHub API ─────────────────────────────────────────────────
def api_request(method, url, token, data=None):
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json"
    }
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code

def get_file_sha(token, owner, repo, path, branch):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
    data, status = api_request("GET", url, token)
    return data.get("sha") if status == 200 else None

def push_file(token, owner, repo, branch, filepath, github_path):
    content = Path(filepath).read_bytes()
    encoded = base64.b64encode(content).decode("utf-8")
    sha = get_file_sha(token, owner, repo, github_path, branch)

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{github_path}"
    payload = {
        "message": f"Update {github_path} (自動更新)",
        "content": encoded,
        "branch": branch
    }
    if sha:
        payload["sha"] = sha

    _, status = api_request("PUT", url, token, payload)
    return status in (200, 201)

# ── メイン ─────────────────────────────────────────────────────
def main():
    cfg = load_config()
    token  = cfg["token"]
    owner  = cfg["owner"]
    repo   = cfg["repo"]
    branch = cfg["branch"]

    print(f"📤 GitHubへプッシュ: {owner}/{repo} (branch: {branch})")

    ok_count = 0
    for filename in FILES_TO_PUSH:
        filepath = BASE_DIR / filename
        if not filepath.exists():
            print(f"  ⚠️  スキップ（ファイルなし）: {filename}")
            continue
        success = push_file(token, owner, repo, branch, filepath, filename)
        if success:
            print(f"  ✅ {filename}")
            ok_count += 1
        else:
            print(f"  ❌ {filename} のプッシュに失敗しました")

    print(f"\n完了: {ok_count}/{len(FILES_TO_PUSH)} ファイルをプッシュしました")
    if ok_count == len(FILES_TO_PUSH):
        print(f"🌐 サイト: https://{owner}.github.io/{repo}/")

if __name__ == "__main__":
    main()
