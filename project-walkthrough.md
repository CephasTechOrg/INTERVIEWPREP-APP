PROJECT WALKTHROUGH (BOTTOM TO TOP)
This is a plain-English map of how the project is built, how it works, and where to edit it.

----------------------------------------------------------------------
1) DATA AND DATABASE (THE BOTTOM LAYER)
----------------------------------------------------------------------
Data folders:
- Questions live in data/questions (JSON files by track/company/difficulty).
- Rubrics live in data/rubrics (JSON files used for scoring).
- See data/README.md for the question file format.

Database config and connection:
- Settings are loaded from backend/.env by backend/app/core/config.py.
  The most important values are DATABASE_URL and SECRET_KEY.
- The SQLAlchemy engine is created in backend/app/db/session.py.
- The ORM base class is in backend/app/db/base.py.

Tables and models (what lives in the database):
- Users: backend/app/models/user.py
- Pending signups (pre-verification accounts): backend/app/models/pending_signup.py
- Interview sessions: backend/app/models/interview_session.py
- Messages: backend/app/models/message.py
- Questions: backend/app/models/question.py
- Evaluations: backend/app/models/evaluation.py
- Session-question link table: backend/app/models/session_question.py
- Per-user question history: backend/app/models/user_question_seen.py

How tables are created:
- On server startup, backend/app/main.py calls Base.metadata.create_all.
- The same file runs small SQL "upgrade" statements to add missing columns.
- It also creates the pending_signups table via the model import.

How questions get into the DB:
- backend/app/db/init_db.py loads all JSON files in data/questions.
- This seeding runs at startup in backend/app/main.py.
- It skips bad files and avoids duplicates.

----------------------------------------------------------------------
2) CRUD LAYER (SIMPLE DATABASE OPERATIONS)
----------------------------------------------------------------------
CRUD files are small helpers that read/write the database:
- backend/app/crud/user.py
- backend/app/crud/pending_signup.py
- backend/app/crud/session.py
- backend/app/crud/message.py
- backend/app/crud/question.py
- backend/app/crud/evaluation.py
- backend/app/crud/session_question.py
- backend/app/crud/user_question_seen.py

If you need to change how data is stored or fetched, start here.

----------------------------------------------------------------------
3) SERVICE LAYER (THE APP LOGIC)
----------------------------------------------------------------------
These files implement the "brain" of the app:
- Interview flow and question logic: backend/app/services/interview_engine.py
- Warmup flow: backend/app/services/interview_warmup.py
- LLM client (DeepSeek): backend/app/services/llm_client.py
- Scoring and final results: backend/app/services/scoring_engine.py
- Rubric loading: backend/app/services/rubric_loader.py
- Text-to-speech backend: backend/app/services/tts/tts_service.py
- ElevenLabs adapter: backend/app/services/tts/elevenlabs_tts.py
- Prompt templates: backend/app/services/prompt_templates.py

If you want to change how the interview is conducted or scored, edit the service layer.

----------------------------------------------------------------------
4) API LAYER (HOW THE FRONTEND TALKS TO THE BACKEND)
----------------------------------------------------------------------
The FastAPI app and routing:
- Main app: backend/app/main.py
- API router: backend/app/api/v1/router.py (prefix: /api/v1)

Auth and security:
- JWT creation and password hashing: backend/app/core/security.py
- Auth dependency (JWT verification): backend/app/api/deps.py
- Rate limiting (simple in-memory): backend/app/api/rate_limit.py

Main API endpoints and where they live:
- Auth:
  - POST /api/v1/auth/signup -> backend/app/api/v1/auth.py
  - POST /api/v1/auth/verify -> backend/app/api/v1/auth.py
  - POST /api/v1/auth/login -> backend/app/api/v1/auth.py
  - POST /api/v1/auth/resend-verification -> backend/app/api/v1/auth.py
  - POST /api/v1/auth/request-password-reset -> backend/app/api/v1/auth.py
  - POST /api/v1/auth/reset-password -> backend/app/api/v1/auth.py
- Sessions:
  - POST /api/v1/sessions (create session)
  - POST /api/v1/sessions/{id}/start
  - POST /api/v1/sessions/{id}/message
  - POST /api/v1/sessions/{id}/finalize
  - GET /api/v1/sessions (list)
  - GET /api/v1/sessions/{id}/messages
  - DELETE /api/v1/sessions/{id}
  All in backend/app/api/v1/sessions.py
- Questions:
  - GET /api/v1/questions
  - GET /api/v1/questions/coverage
  - GET /api/v1/questions/{id}
  All in backend/app/api/v1/questions.py
- Analytics (results):
  - GET /api/v1/analytics/sessions/{id}/results
  In backend/app/api/v1/analytics.py
- Voice (TTS):
  - POST /api/v1/tts
  In backend/app/api/v1/voice.py
- AI status (health):
  - GET /api/v1/ai/status
  In backend/app/api/v1/ai.py

----------------------------------------------------------------------
5) EMAIL VERIFICATION AND SIGNUP (NEW FLOW)
----------------------------------------------------------------------
Goal: A real account is NOT created until a 6-digit code is verified.

Signup flow (no account yet):
1) Frontend sends POST /api/v1/auth/signup with email + password.
2) Backend stores a pending signup record in pending_signups.
   - Code generation: backend/app/crud/pending_signup.py
   - Code is 6 digits, expires in 30 minutes.
3) Email is sent (or printed to console in dev):
   - backend/app/core/email.py
4) Frontend shows the Verify view.

Verify flow (account is created here):
1) Frontend sends POST /api/v1/auth/verify with email + 6-digit code.
2) Backend checks pending_signups.
3) If the code matches, a real User is created:
   - backend/app/crud/user.py (create_user_from_hash)
4) Backend returns a JWT token.
5) Frontend stores the token and redirects to the interview page.

Login flow:
1) POST /api/v1/auth/login with email + password.
2) If user is verified, a JWT token is returned.
3) If the user is not verified (or still pending), login is blocked.

Resend flow:
- POST /api/v1/auth/resend-verification
- If pending, it sends a new 6-digit code.
- If an unverified user already exists, it sends a 6-digit code as well.

----------------------------------------------------------------------
6) FRONTEND STRUCTURE (WHAT YOU EDIT)
----------------------------------------------------------------------
HTML pages:
- Login/verification: frontend/login.html
- Main dashboard: frontend/dashboard.html
- Live interview: frontend/interview.html
- Results page: frontend/results.html
- Settings page: frontend/settings.html
- Landing page: frontend/index.html

CSS:
- Primary styles: frontend/assets/css/pro.css
- Responsive styles: frontend/assets/css/responsive.css
- Performance page styles: frontend/assets/css/performance.css

JavaScript (how the UI works):
- frontend/assets/js/api.js
  - API_BASE and fetch helper
  - Token storage
  - Auto-redirect on 401/403
- frontend/assets/js/auth.js
  - Signup, verify, login, resend, reset
  - 6-digit code input behavior (paste and auto-advance)
- frontend/assets/js/interview.js
  - Main UI logic for dashboard, interview, history, performance
  - Session creation, start, sending messages, finalize
  - Navigation between dashboard sections
  - Text-to-speech playback
- frontend/assets/js/voice.js
  - Speech recognition (mic input) and browser TTS
- frontend/assets/js/charts.js
  - Charts for performance and results

Which scripts are loaded where:
- login.html -> api.js, auth.js
- dashboard.html -> api.js, charts.js, voice.js, interview.js
- interview.html -> api.js, charts.js, voice.js, interview.js
- results.html -> api.js, charts.js, auth.js
- settings.html -> api.js, charts.js, voice.js, interview.js

----------------------------------------------------------------------
7) HOW PAGES ARE LINKED TOGETHER
----------------------------------------------------------------------
The UI uses static pages plus light client-side navigation:
- The sidebar uses data-page attributes on links.
- interview.js has navigateTo() which shows the correct section inside dashboard.html.
- Some pages are separate HTML files (interview.html, results.html, settings.html).
  These are opened by goToPage() and goToInterviewPage().
- When starting a session, interview.js adds ?session_id=ID to the interview URL.
- The interview page reads session_id and resumes that session.
- The current session id is also stored in localStorage.

Key linking helpers:
- goToInterviewPage() in frontend/assets/js/interview.js
- navigateTo() in frontend/assets/js/interview.js
- session_id in URL and localStorage

----------------------------------------------------------------------
8) STEP-BY-STEP: SIGNUP TO START INTERVIEW
----------------------------------------------------------------------
Signup and verify:
1) User opens frontend/login.html.
2) Clicks "Create Account", enters info, submits.
3) Frontend calls POST /api/v1/auth/signup.
4) Backend stores a pending signup and sends a 6-digit code.
5) User enters code in the 6-box input and clicks Verify.
6) Frontend calls POST /api/v1/auth/verify (email + code).
7) Backend creates the User and returns a JWT token.
8) Frontend saves the token and redirects to interview.html.

Start interview:
1) From dashboard, user clicks "Start Interview Session".
2) Frontend calls POST /api/v1/sessions to create a session.
3) Frontend calls POST /api/v1/sessions/{id}/start.
4) Backend InterviewEngine selects the first question and returns a message.
5) Frontend displays the message and enables the chat box.

Chat and finalize:
1) User sends a message -> POST /api/v1/sessions/{id}/message.
2) Backend processes it and returns the next interviewer reply.
3) When finished, user clicks Finalize -> POST /api/v1/sessions/{id}/finalize.
4) ScoringEngine produces results, saved to DB.
5) Frontend loads results from GET /api/v1/analytics/sessions/{id}/results.

----------------------------------------------------------------------
9) WHERE TO EDIT COMMON THINGS
----------------------------------------------------------------------
Change API base URL:
- frontend/assets/js/api.js (API_BASE)

Change signup/verify UI:
- frontend/login.html
- frontend/assets/js/auth.js

Change interview flow or LLM prompts:
- backend/app/services/interview_engine.py
- backend/app/services/prompt_templates.py

Change question selection or rules:
- backend/app/services/interview_engine.py
- backend/app/crud/question.py

Change data files (questions or rubrics):
- data/questions
- data/rubrics
- backend/app/db/init_db.py (loader)

Change scoring logic:
- backend/app/services/scoring_engine.py
- backend/app/services/rubric_loader.py

Change TTS behavior:
- backend/app/services/tts/tts_service.py
- frontend/assets/js/interview.js
- frontend/assets/js/voice.js

----------------------------------------------------------------------
10) IMPORTANT NOTES FOR NON-CODERS
----------------------------------------------------------------------
- Think of the backend as the "brain" and the frontend as the "face".
- The frontend only talks to the backend through the API endpoints listed above.
- The database is where all accounts, sessions, and messages are stored.
- Email verification happens before a real account is created.
- If SMTP is not configured, the verification code prints in the backend console.

If you want me to expand any specific part, tell me the section name and I will add more detail.
