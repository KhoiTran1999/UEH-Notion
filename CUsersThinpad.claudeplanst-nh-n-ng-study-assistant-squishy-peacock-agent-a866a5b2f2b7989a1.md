# Plan to migrate Study Assistant to Telegram Web App

## 1. Architecture
- **Frontend Host**: Cloudflare Pages (Free, serverless, integrated with existing Cloudflare setup).
- **Tech Stack**: HTML + JavaScript (Vanilla or simple framework like Preact).
- **Backend API**: 
  - Keep the Cloudflare Worker (`cloudflare_worker.js`) to handle Telegram updates and serve as the API gateway.
  - The Python code (`src/jobs/study_assistant.py`) needs to be accessible via an API to fetch the candidates and generate the quiz on-demand.
  - Since GitHub Actions is asynchronous, we'll need to move the logic of `study_assistant.py` (fetching topics, generating quiz) to a serverless backend that can respond to API requests, or host it on a platform like Vercel, Render, or a cheap VPS using FastAPI. Given the current setup relies on Github Actions, this is a significant architecture shift.
  - **Proposed Backend Change**: We must move the Python logic (`study_assistant.py`) from a GitHub Action script to a web service. FastAPI on Render/Railway/Fly.io is ideal for this.

## 2. Changing the Initial `/study` Command
- Update `cloudflare_worker.js`: When the user sends `/study`, instead of triggering `triggerGitHub(env, "study-assistant", chatId)`, it will reply with an Inline Keyboard Button containing a Web App URL.
- Example:
  ```json
  {
    "inline_keyboard": [
      [{"text": "Mở Study Assistant", "web_app": {"url": "https://[YOUR_PAGES_APP].pages.dev"}}]
    ]
  }
  ```

## 3. Communication Strategy (Frontend <-> Backend)
- **Frontend (TWA)**:
  - Connects to the new Python API (FastAPI).
  - Endpoint 1: `GET /api/study/candidates` - Returns 5 topics.
  - Endpoint 2: `POST /api/study/quiz` - Accepts `topic_id`, returns quiz content.
  - Endpoint 3: `POST /api/study/status` - Accepts `topic_id` and status (`mastered`/`review`), updates Notion.
- **Python Backend (FastAPI)**:
  - Exposes the logic currently in `study_assistant.py` via HTTP endpoints.
  - Receives requests from the TWA frontend, executes Notion/Gemini calls, and returns JSON.

## 4. Required File Changes

### `cloudflare_worker.js`
- Modify the `/study` command handler.
- Remove the `triggerGitHub` call for `study-assistant`.
- Send a Telegram message with a `web_app` button pointing to the new frontend.

### `src/jobs/study_assistant.py`
- Refactor the procedural script into functions that can be called by an API framework (e.g., FastAPI).
- Separate the "fetch candidates", "generate quiz", and "update status" logic into distinct functions/endpoints.
- Remove the direct Telegram messaging (the frontend will display the data, not send messages to the chat, unless desired as a summary).

### `src/main.py` (or similar entry point)
- Set up FastAPI app to serve these new endpoints.

## 5. Next Steps
- Set up a FastAPI server (or similar) to host the Python logic.
- Create the Cloudflare Pages project for the HTML/JS frontend.
- Update the Cloudflare Worker to serve the Web App button.
