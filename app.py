"""
AutoPost AI — TikTok Content Posting Pipeline
Flask app for OAuth 2.0 + video.publish (direct post) via TikTok Content Posting API

Setup:
    pip install flask requests python-dotenv

Run:
    python app.py

Environment variables (.env):
    TIKTOK_CLIENT_KEY=your_client_key
    TIKTOK_CLIENT_SECRET=your_client_secret
    FLASK_SECRET_KEY=any_random_string
    REDIRECT_URI=http://localhost:5000/callback
"""

import os
import json
import time
import hashlib
import secrets
import requests
from flask import (
    Flask, session, redirect, request,
    url_for, jsonify, render_template_string, send_from_directory
)
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))

# ── Config ────────────────────────────────────────────────────────────────────
CLIENT_KEY    = os.getenv("TIKTOK_CLIENT_KEY",    "")
CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")
REDIRECT_URI  = os.getenv("REDIRECT_URI",          "http://localhost:5000/callback")

TIKTOK_AUTH_URL    = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN_URL   = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_USERINFO_URL = "https://open.tiktokapis.com/v2/user/info/"

# Content Posting API endpoints
TIKTOK_CREATOR_INFO = "https://open.tiktokapis.com/v2/post/publish/creator_info/query/"
TIKTOK_INIT_UPLOAD  = "https://open.tiktokapis.com/v2/post/publish/video/init/"
TIKTOK_CHECK_STATUS = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"

SCOPES = "user.info.basic,video.publish"

# ── HTML Templates ─────────────────────────────────────────────────────────────
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>AutoPost AI</title>
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Mono:wght@300;400&display=swap" rel="stylesheet"/>
  <style>
    :root {
      --bg:#0a0a0a; --surface:#111; --accent:#f5a623;
      --accent2:#ff6b35; --text:#e8e8e0; --muted:#555; --border:#1e1e1e;
      --green:#4ade80; --red:#f87171;
    }
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
    body{background:var(--bg);color:var(--text);font-family:'DM Mono',monospace;font-size:13px;min-height:100vh;display:flex;flex-direction:column;}
    .noise{position:fixed;inset:0;z-index:0;pointer-events:none;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.05'/%3E%3C/svg%3E");opacity:0.35;}
    nav{position:sticky;top:0;z-index:20;background:rgba(10,10,10,0.95);backdrop-filter:blur(16px);border-bottom:1px solid var(--border);padding:1rem 2rem;display:flex;align-items:center;gap:1rem;}
    .logo{font-family:'Syne',sans-serif;font-weight:800;font-size:1rem;color:var(--accent);letter-spacing:-0.02em;}
    .logo span{color:var(--accent2);}
    .nav-links{margin-left:auto;display:flex;gap:1.5rem;font-size:11px;color:var(--muted);}
    .nav-links a{color:var(--muted);text-decoration:none;transition:color .2s;}
    .nav-links a:hover{color:var(--text);}
    .status-dot{width:7px;height:7px;border-radius:50%;background:{% if authed %}var(--green){% else %}var(--red){% endif %};display:inline-block;margin-right:5px;box-shadow:0 0 6px {% if authed %}var(--green){% else %}var(--red){% endif %};}
    main{position:relative;z-index:1;flex:1;max-width:900px;margin:0 auto;width:100%;padding:3rem 2rem;}
    .grid{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;margin-top:2rem;}
    .card{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:1.5rem;transition:border-color .2s;}
    .card:hover{border-color:#333;}
    .card-label{font-size:9px;letter-spacing:0.2em;text-transform:uppercase;color:var(--accent);margin-bottom:0.6rem;}
    .card h2{font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;margin-bottom:0.8rem;color:var(--text);}
    .card p{color:var(--muted);font-size:12px;line-height:1.7;margin-bottom:1rem;}
    .btn{display:inline-flex;align-items:center;gap:0.5rem;padding:0.65rem 1.3rem;font-family:'DM Mono',monospace;font-size:12px;border:none;border-radius:4px;cursor:pointer;text-decoration:none;transition:all .2s;letter-spacing:0.03em;}
    .btn-primary{background:var(--accent);color:#000;font-weight:bold;}
    .btn-primary:hover{background:#e09520;transform:translateY(-1px);}
    .btn-outline{background:transparent;color:var(--text);border:1px solid var(--border);}
    .btn-outline:hover{border-color:var(--accent);color:var(--accent);}
    .btn-danger{background:transparent;color:var(--red);border:1px solid var(--red);}
    .btn-danger:hover{background:var(--red);color:#000;}
    .hero{margin-bottom:2.5rem;}
    .hero-eyebrow{font-size:10px;letter-spacing:0.2em;text-transform:uppercase;color:var(--accent);margin-bottom:0.8rem;}
    .hero h1{font-family:'Syne',sans-serif;font-size:clamp(1.8rem,4vw,2.8rem);font-weight:800;letter-spacing:-0.03em;line-height:1.1;margin-bottom:0.8rem;}
    .hero h1 span{color:var(--accent);}
    .hero p{color:var(--muted);max-width:500px;font-size:12px;line-height:1.8;}
    .auth-banner{background:rgba(245,166,35,0.07);border:1px solid rgba(245,166,35,0.25);border-radius:6px;padding:1rem 1.2rem;margin-bottom:2rem;display:flex;align-items:center;justify-content:space-between;gap:1rem;}
    .auth-info{display:flex;align-items:center;gap:0.8rem;font-size:12px;}
    .tag{font-size:9px;padding:2px 7px;border:1px solid var(--border);color:var(--muted);border-radius:2px;text-transform:uppercase;letter-spacing:0.1em;}
    .pipeline-steps{display:flex;flex-direction:column;gap:0.5rem;margin-top:1rem;}
    .step{display:flex;align-items:center;gap:0.8rem;padding:0.6rem 0.8rem;border:1px solid var(--border);border-radius:4px;font-size:12px;color:var(--muted);}
    .step-num{font-family:'Syne',sans-serif;font-weight:800;color:var(--accent);font-size:0.9rem;min-width:1.5rem;}
    @media(max-width:600px){.grid{grid-template-columns:1fr;}}
  </style>
</head>
<body>
  <div class="noise"></div>
  <nav>
    <span class="logo">Auto<span>Post</span> AI</span>
    <span class="tag">v1.0</span>
    <div class="nav-links">
      <a href="/tos">Terms</a>
      <a href="/privacy">Privacy</a>
      {% if authed %}<a href="/logout">Logout</a>{% endif %}
    </div>
  </nav>
  <main>
    <div class="hero">
      <p class="hero-eyebrow">TikTok Content Posting Pipeline</p>
      <h1>Algorithmic <span>video publishing</span><br/>on autopilot.</h1>
      <p>Connect your TikTok account, generate AI-powered faceless videos, and publish directly — all from a single workflow.</p>
    </div>

    {% if authed %}
    <div class="auth-banner">
      <div class="auth-info">
        <span class="status-dot"></span>
        <strong>Connected:</strong> {{ username or open_id[:16] + '...' }}
        <span class="tag">{{ scopes }}</span>
      </div>
      <a href="/logout" class="btn btn-danger">Disconnect</a>
    </div>
    {% else %}
    <div class="auth-banner">
      <div class="auth-info">
        <span class="status-dot"></span>
        TikTok account not connected
      </div>
      <a href="/login" class="btn btn-primary">▸ Connect TikTok</a>
    </div>
    {% endif %}

    <div class="grid">
      <div class="card">
        <p class="card-label">Step 01</p>
        <h2>Authorization</h2>
        <p>Connect your TikTok account securely via OAuth 2.0. Your credentials are never stored — only a session token is held in memory.</p>
        {% if not authed %}
        <a href="/login" class="btn btn-primary">Connect Account →</a>
        {% else %}
        <span class="btn btn-outline" style="cursor:default;">✓ Authorized</span>
        {% endif %}
      </div>

      <div class="card">
        <p class="card-label">Step 02</p>
        <h2>Creator Info</h2>
        <p>Fetch your TikTok creator settings to verify privacy defaults, duet settings, and comment configuration before uploading.</p>
        {% if authed %}
        <a href="/creator-info" class="btn btn-outline">Fetch Creator Info →</a>
        {% else %}
        <span class="btn btn-outline" style="opacity:.4;cursor:not-allowed;">Requires Auth</span>
        {% endif %}
      </div>

      <div class="card">
        <p class="card-label">Step 03</p>
        <h2>Upload & Publish</h2>
        <p>Initialize a video upload to TikTok's Content API, transfer the file, and trigger a direct post with title and privacy settings.</p>
        {% if authed %}
        <a href="/upload" class="btn btn-primary">Upload Video →</a>
        {% else %}
        <span class="btn btn-outline" style="opacity:.4;cursor:not-allowed;">Requires Auth</span>
        {% endif %}
      </div>

      <div class="card">
        <p class="card-label">Step 04</p>
        <h2>Post Status</h2>
        <p>Poll the TikTok API to check the processing and publication status of your uploaded video after submission.</p>
        {% if authed %}
        <a href="/status" class="btn btn-outline">Check Status →</a>
        {% else %}
        <span class="btn btn-outline" style="opacity:.4;cursor:not-allowed;">Requires Auth</span>
        {% endif %}
      </div>
    </div>

    <div class="card" style="margin-top:1.5rem;">
      <p class="card-label">Pipeline Flow</p>
      <h2>How it works</h2>
      <div class="pipeline-steps">
        <div class="step"><span class="step-num">1</span> User clicks "Connect TikTok" → redirected to TikTok OAuth</div>
        <div class="step"><span class="step-num">2</span> TikTok returns auth code → App exchanges for access_token</div>
        <div class="step"><span class="step-num">3</span> App calls /creator_info to get allowed privacy/comment settings</div>
        <div class="step"><span class="step-num">4</span> App calls /video/init → gets upload_url + publish_id</div>
        <div class="step"><span class="step-num">5</span> App PUTs video file to upload_url (chunked for large files)</div>
        <div class="step"><span class="step-num">6</span> App calls /status/fetch with publish_id to confirm live post</div>
      </div>
    </div>
  </main>
</body>
</html>
"""

UPLOAD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Upload Video — AutoPost AI</title>
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Mono:wght@300;400&display=swap" rel="stylesheet"/>
  <style>
    :root{--bg:#0a0a0a;--surface:#111;--accent:#f5a623;--accent2:#ff6b35;--text:#e8e8e0;--muted:#555;--border:#1e1e1e;}
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
    body{background:var(--bg);color:var(--text);font-family:'DM Mono',monospace;font-size:13px;min-height:100vh;}
    nav{background:rgba(10,10,10,0.95);border-bottom:1px solid var(--border);padding:1rem 2rem;display:flex;align-items:center;gap:1rem;}
    .logo{font-family:'Syne',sans-serif;font-weight:800;font-size:1rem;color:var(--accent);}
    .logo span{color:var(--accent2);}
    a.back{margin-left:auto;color:var(--muted);text-decoration:none;font-size:11px;}
    a.back:hover{color:var(--text);}
    main{max-width:600px;margin:3rem auto;padding:0 2rem;}
    h1{font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:800;letter-spacing:-0.03em;margin-bottom:0.5rem;}
    .sub{color:var(--muted);font-size:12px;margin-bottom:2rem;}
    .form-group{margin-bottom:1.2rem;}
    label{display:block;font-size:10px;letter-spacing:0.15em;text-transform:uppercase;color:var(--accent);margin-bottom:0.4rem;}
    input[type=text],input[type=file],select,textarea{
      width:100%;background:var(--surface);border:1px solid var(--border);
      color:var(--text);padding:0.65rem 0.9rem;font-family:'DM Mono',monospace;
      font-size:12px;border-radius:4px;outline:none;transition:border-color .2s;
    }
    input:focus,select:focus,textarea:focus{border-color:var(--accent);}
    textarea{resize:vertical;min-height:80px;}
    .btn{display:inline-flex;align-items:center;gap:0.5rem;padding:0.7rem 1.5rem;font-family:'DM Mono',monospace;font-size:12px;border:none;border-radius:4px;cursor:pointer;letter-spacing:0.03em;font-weight:bold;background:var(--accent);color:#000;width:100%;justify-content:center;transition:all .2s;}
    .btn:hover{background:#e09520;}
    .note{background:rgba(245,166,35,0.07);border:1px solid rgba(245,166,35,0.2);border-radius:4px;padding:0.8rem 1rem;font-size:11px;color:#aaa;margin-top:0.5rem;}
    {% if result %}
    .result{background:#111;border:1px solid var(--border);border-radius:6px;padding:1.2rem;margin-top:2rem;font-size:12px;white-space:pre-wrap;word-break:break-all;color:#aaa;}
    .result strong{color:var(--accent);}
    {% endif %}
  </style>
</head>
<body>
  <nav>
    <span class="logo">Auto<span>Post</span> AI</span>
    <a class="back" href="/">← Back to Dashboard</a>
  </nav>
  <main>
    <h1>Upload Video</h1>
    <p class="sub">Direct post to TikTok via Content Posting API (video.publish)</p>

    <form method="POST" enctype="multipart/form-data">
      <div class="form-group">
        <label>Video File (MP4)</label>
        <input type="file" name="video" accept="video/mp4,video/mov" required/>
        <div class="note">Max 4GB. Min 3 seconds, max 10 minutes. 720p+ recommended.</div>
      </div>
      <div class="form-group">
        <label>Post Title / Caption</label>
        <textarea name="title" placeholder="Your AI-generated caption with #hashtags..."></textarea>
      </div>
      <div class="form-group">
        <label>Privacy Level</label>
        <select name="privacy_level">
          <option value="SELF_ONLY">Private (Self Only) — recommended for testing</option>
          <option value="FOLLOWER_OF_CREATOR">Followers Only</option>
          <option value="MUTUAL_FOLLOW_FRIENDS">Friends</option>
          <option value="PUBLIC_TO_EVERYONE">Public</option>
        </select>
      </div>
      <div class="form-group">
        <label>Disable Comments?</label>
        <select name="disable_comment">
          <option value="false">No — allow comments</option>
          <option value="true">Yes — disable comments</option>
        </select>
      </div>
      <div class="form-group">
        <label>Disable Duet?</label>
        <select name="disable_duet">
          <option value="false">No</option>
          <option value="true">Yes</option>
        </select>
      </div>
      <div class="form-group">
        <label>Disable Stitch?</label>
        <select name="disable_stitch">
          <option value="false">No</option>
          <option value="true">Yes</option>
        </select>
      </div>
      <button type="submit" class="btn">▸ Upload & Publish to TikTok</button>
    </form>

    {% if result %}
    <div class="result"><strong>API Response:</strong>\n{{ result }}</div>
    {% endif %}
  </main>
</body>
</html>
"""

RESULT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>Result — AutoPost AI</title>
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Mono:wght@300;400&display=swap" rel="stylesheet"/>
  <style>
    :root{--bg:#0a0a0a;--accent:#f5a623;--accent2:#ff6b35;--text:#e8e8e0;--muted:#555;--border:#1e1e1e;}
    *{box-sizing:border-box;margin:0;padding:0;}
    body{background:var(--bg);color:var(--text);font-family:'DM Mono',monospace;font-size:13px;min-height:100vh;}
    nav{background:rgba(10,10,10,.95);border-bottom:1px solid var(--border);padding:1rem 2rem;display:flex;align-items:center;}
    .logo{font-family:'Syne',sans-serif;font-weight:800;font-size:1rem;color:var(--accent);}
    .logo span{color:var(--accent2);}
    a.back{margin-left:auto;color:var(--muted);text-decoration:none;font-size:11px;}
    main{max-width:700px;margin:3rem auto;padding:0 2rem;}
    h1{font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:800;letter-spacing:-0.03em;margin-bottom:1.5rem;}
    pre{background:#111;border:1px solid var(--border);border-radius:6px;padding:1.5rem;white-space:pre-wrap;word-break:break-all;color:#aaa;font-size:12px;line-height:1.8;}
    .btn{display:inline-block;margin-top:1.5rem;padding:0.65rem 1.3rem;background:var(--accent);color:#000;font-family:'DM Mono',monospace;font-size:12px;font-weight:bold;border-radius:4px;text-decoration:none;}
  </style>
</head>
<body>
  <nav><span class="logo">Auto<span>Post</span> AI</span><a class="back" href="/">← Dashboard</a></nav>
  <main>
    <h1>{{ title }}</h1>
    <pre>{{ content }}</pre>
    <a href="/" class="btn">← Back to Dashboard</a>
  </main>
</body>
</html>
"""

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    authed = "access_token" in session
    return render_template_string(
        INDEX_HTML,
        authed=authed,
        open_id=session.get("open_id", ""),
        username=session.get("display_name", ""),
        scopes=session.get("scope", SCOPES),
    )

@app.route("/tos")
def tos():
    return send_from_directory(".", "tos.html")

@app.route("/privacy")
def privacy():
    return send_from_directory(".", "privacy.html")


# ── OAuth ──────────────────────────────────────────────────────────────────────

@app.route("/login")
def login():
    """Redirect user to TikTok OAuth authorization page."""
    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state

    params = {
        "client_key":     CLIENT_KEY,
        "response_type":  "code",
        "scope":          SCOPES,
        "redirect_uri":   REDIRECT_URI,
        "state":          state,
    }
    url = TIKTOK_AUTH_URL + "?" + "&".join(f"{k}={v}" for k, v in params.items())
    return redirect(url)


@app.route("/callback")
def callback():
    """Handle TikTok OAuth callback, exchange code for access_token."""
    error = request.args.get("error")
    if error:
        return render_template_string(RESULT_HTML,
            title="Authorization Failed",
            content=f"Error: {error}\nDescription: {request.args.get('error_description','')}"
        )

    code  = request.args.get("code")
    state = request.args.get("state")

    if state != session.pop("oauth_state", None):
        return render_template_string(RESULT_HTML,
            title="Security Error",
            content="State mismatch — possible CSRF attack. Please try again."
        )

    # Exchange code for token
    token_resp = requests.post(TIKTOK_TOKEN_URL, data={
        "client_key":     CLIENT_KEY,
        "client_secret":  CLIENT_SECRET,
        "code":           code,
        "grant_type":     "authorization_code",
        "redirect_uri":   REDIRECT_URI,
    }, headers={"Content-Type": "application/x-www-form-urlencoded"})

    data = token_resp.json()
    print("[TOKEN RESPONSE]", json.dumps(data, indent=2))

    if "access_token" not in data:
        return render_template_string(RESULT_HTML,
            title="Token Exchange Failed",
            content=json.dumps(data, indent=2)
        )

    session["access_token"] = data["access_token"]
    session["open_id"]       = data.get("open_id", "")
    session["scope"]         = data.get("scope", "")
    session["expires_in"]    = data.get("expires_in", 0)
    session["token_time"]    = time.time()

    # Fetch basic user info
    userinfo_resp = requests.get(
        TIKTOK_USERINFO_URL,
        params={"fields": "open_id,display_name,avatar_url"},
        headers={"Authorization": f"Bearer {data['access_token']}"}
    )
    userdata = userinfo_resp.json()
    print("[USER INFO]", json.dumps(userdata, indent=2))
    if "data" in userdata and "user" in userdata["data"]:
        session["display_name"] = userdata["data"]["user"].get("display_name", "")

    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ── Creator Info ───────────────────────────────────────────────────────────────

@app.route("/creator-info")
def creator_info():
    if "access_token" not in session:
        return redirect(url_for("login"))

    resp = requests.post(
        TIKTOK_CREATOR_INFO,
        headers={
            "Authorization": f"Bearer {session['access_token']}",
            "Content-Type":  "application/json; charset=UTF-8",
        },
        json={}
    )
    return render_template_string(RESULT_HTML,
        title="Creator Info",
        content=json.dumps(resp.json(), indent=2)
    )


# ── Upload & Direct Post ───────────────────────────────────────────────────────

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if "access_token" not in session:
        return redirect(url_for("login"))

    result = None

    if request.method == "POST":
        video_file     = request.files.get("video")
        title          = request.form.get("title", "")[:150]
        privacy_level  = request.form.get("privacy_level", "SELF_ONLY")
        disable_comment = request.form.get("disable_comment") == "true"
        disable_duet    = request.form.get("disable_duet")    == "true"
        disable_stitch  = request.form.get("disable_stitch")  == "true"

        if not video_file:
            result = "Error: No video file provided."
        else:
            video_bytes   = video_file.read()
            video_size    = len(video_bytes)
            chunk_size    = 64 * 1024 * 1024  # 64MB chunks
            total_chunks  = max(1, (video_size + chunk_size - 1) // chunk_size)

            # Step 1 — Initialize upload
            init_payload = {
                "post_info": {
                    "title":           title,
                    "privacy_level":   privacy_level,
                    "disable_comment": disable_comment,
                    "disable_duet":    disable_duet,
                    "disable_stitch":  disable_stitch,
                },
                "source_info": {
                    "source":       "FILE_UPLOAD",
                    "video_size":   video_size,
                    "chunk_size":   min(chunk_size, video_size),
                    "total_chunk_count": total_chunks,
                }
            }

            print("[INIT PAYLOAD]", json.dumps(init_payload, indent=2))

            init_resp = requests.post(
                TIKTOK_INIT_UPLOAD,
                headers={
                    "Authorization": f"Bearer {session['access_token']}",
                    "Content-Type":  "application/json; charset=UTF-8",
                },
                json=init_payload
            )

            init_data = init_resp.json()
            print("[INIT RESPONSE]", json.dumps(init_data, indent=2))

            if init_data.get("error", {}).get("code") != "ok":
                result = f"Init failed:\n{json.dumps(init_data, indent=2)}"
            else:
                publish_id = init_data["data"]["publish_id"]
                upload_url = init_data["data"]["upload_url"]

                # Step 2 — Upload video in chunks
                upload_success = True
                for chunk_index in range(total_chunks):
                    start = chunk_index * chunk_size
                    end   = min(start + chunk_size, video_size)
                    chunk = video_bytes[start:end]

                    content_range = f"bytes {start}-{end-1}/{video_size}"
                    upload_resp = requests.put(
                        upload_url,
                        data=chunk,
                        headers={
                            "Content-Type":   "video/mp4",
                            "Content-Length": str(len(chunk)),
                            "Content-Range":  content_range,
                        }
                    )
                    print(f"[CHUNK {chunk_index+1}/{total_chunks}] status={upload_resp.status_code}")
                    if upload_resp.status_code not in (200, 206):
                        upload_success = False
                        result = f"Upload failed at chunk {chunk_index+1}:\n{upload_resp.text}"
                        break

                if upload_success:
                    # Step 3 — Store publish_id for status check
                    session["publish_id"] = publish_id
                    result = (
                        f"✓ Upload initiated successfully!\n\n"
                        f"publish_id: {publish_id}\n\n"
                        f"TikTok is now processing your video.\n"
                        f"Go to /status to check when it goes live."
                    )

    return render_template_string(UPLOAD_HTML, result=result)


# ── Status Check ───────────────────────────────────────────────────────────────

@app.route("/status", methods=["GET", "POST"])
def status():
    if "access_token" not in session:
        return redirect(url_for("login"))

    publish_id = request.args.get("publish_id") or session.get("publish_id", "")

    if publish_id:
        resp = requests.post(
            TIKTOK_CHECK_STATUS,
            headers={
                "Authorization": f"Bearer {session['access_token']}",
                "Content-Type":  "application/json; charset=UTF-8",
            },
            json={"publish_id": publish_id}
        )
        status_data = resp.json()
        print("[STATUS]", json.dumps(status_data, indent=2))

        content = (
            f"Checked publish_id: {publish_id}\n\n"
            + json.dumps(status_data, indent=2)
        )
    else:
        content = "No publish_id found. Upload a video first, or pass ?publish_id=XXX in the URL."

    return render_template_string(RESULT_HTML,
        title="Post Status",
        content=content
    )


# ── Health Check ───────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "ok", "authed": "access_token" in session})


if __name__ == "__main__":
    print("=" * 60)
    print("  AutoPost AI — TikTok Content Posting Pipeline")
    print("=" * 60)
    print(f"  Client Key : {CLIENT_KEY}")
    print(f"  Redirect   : {REDIRECT_URI}")
    print(f"  Scopes     : {SCOPES}")
    print("=" * 60)
    print("  Open: http://localhost:5000")
    print("=" * 60)
    app.run(debug=True, port=5000)
