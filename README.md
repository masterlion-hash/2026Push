# AutoPost AI — TikTok Content Posting Pipeline

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9+-green.svg)](https://python.org)
[![TikTok API](https://img.shields.io/badge/TikTok-Content_Posting_API-ff0050.svg)](https://developers.tiktok.com/)

Full-stack Flask application for OAuth 2.0 authorization and direct video publishing
to TikTok via the Content Posting API (`video.publish` scope).

---

## Project Structure

```
2026Push/
├── app.py              # Flask app — OAuth, upload, status endpoints
├── tos.html            # Terms of Service (hosted via GitHub Pages)
├── privacy.html        # Privacy Policy (hosted via GitHub Pages)
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
├── DEMO_SCRIPT.txt     # Step-by-step demo recording guide
├── LICENSE             # Apache 2.0
└── README.md           # This file
```

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env and add your TIKTOK_CLIENT_SECRET and FLASK_SECRET_KEY
```

### 3. Run locally
```bash
python app.py
# Open http://localhost:5000
```

### 4. Ensure TikTok redirect URI matches
In TikTok Developer Console → your app → Login Kit → Redirect URIs:
```
http://localhost:5000/callback
```

---

## Hosting the ToS & Privacy Policy (Required for App Review)

TikTok requires public URLs for both documents. This repo uses **GitHub Pages**:

### GitHub Pages (this repo)
1. Go to **Settings → Pages → Deploy from branch** (`main`, root `/`)
2. Your URLs will be:
   - `https://masterlion-harsh.github.io/2026Push/tos.html`
   - `https://masterlion-harsh.github.io/2026Push/privacy.html`
3. Paste these URLs into TikTok Developer Console

---

## TikTok App Review — What to Fill

| Field | Value |
|-------|-------|
| App Name | AutoPost AI |
| Category | Tools & Utilities |
| ToS URL | `https://masterlion-harsh.github.io/2026Push/tos.html` |
| Privacy URL | `https://masterlion-harsh.github.io/2026Push/privacy.html` |
| Platform | Web |
| Scope | `video.publish`, `user.info.basic` |

**Explanation text (copy into the review form):**
```
AutoPost AI integrates the Content Posting API (video.publish scope) to allow
authorized users to upload and publish original faceless educational videos (60s+)
generated via AI tools.

Flow:
1. User authorizes via OAuth 2.0 (user.info.basic + video.publish scopes)
2. App calls /creator_info to verify allowed privacy/interaction settings
3. App calls /v2/post/publish/video/init/ to initialize file upload
4. Video file is uploaded to the provided upload_url in chunks
5. App polls /v2/post/publish/status/fetch/ to confirm publication

Used in sandbox for testing. No auto-posting without explicit user action.
Content is original and educational (tech/finance niches). No commercial
resale of API access. Personal developer tool for content automation.
```

---

## API Endpoints

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Dashboard |
| `/login` | GET | Redirect to TikTok OAuth |
| `/callback` | GET | Handle OAuth return + exchange code for token |
| `/logout` | GET | Clear session |
| `/creator-info` | GET | Fetch creator settings from TikTok |
| `/upload` | GET/POST | Upload form + publish video |
| `/status` | GET | Check publish status by publish_id |
| `/health` | GET | Health check JSON |
| `/tos` | GET | Terms of Service page |
| `/privacy` | GET | Privacy Policy page |

---

## Sandbox Testing

1. In TikTok Developer Console → toggle your app to **Sandbox Mode**
2. Add test users (your personal TikTok account) under Sandbox → Manage Users
3. Run the full OAuth + upload flow — videos post to sandbox, not live TikTok
4. Record this flow for your demo video (see `DEMO_SCRIPT.txt`)

---

## Security Notes

- Never commit `.env` to git (it's in `.gitignore` template)
- Access tokens are held in server-side session only, never logged or stored to DB
- Client Secret must stay server-side — never expose in frontend code
- Revoke access: TikTok → Settings → Privacy → Apps and Websites → AutoPost AI → Remove
