# AI Assistant

A personal AI Assistant project combining a Node backend, Python services, a Flutter mobile app, and a Next.js web frontend.

## Main Features

- Natural language interaction and audio processing (STT/TTS).
- Reminder and scheduling management backed by a MongoDB datastore.
- User authentication and email utilities (password reset, notifications).
- Image generation and image processing utilities.
- Cross-platform frontends: Flutter mobile/desktop and a Next.js web UI.

## Repository Structure

- `Backend/Node` — Express-based API server, controllers, models, routes and utilities.
- `Backend/Python` — Python services for ML, audio/image processing, and reminder logic.
- `frontend/flutter` — Flutter application (mobile + desktop targets).
- `next` — Next.js web frontend.

## Quick Start

Prerequisites

- Node.js (18+ recommended) and npm or pnpm
- Python 3.8+ and virtualenv (for Python services)
- Flutter SDK (for the Flutter app)
- MongoDB (local or cloud) and SMTP credentials for email features

Backend (Node)

1. Open a terminal and change to the Node backend:

```powershell
cd Backend/Node
```

2. Install dependencies:

```powershell
npm install
# or: pnpm install
```

3. Start the server:

```powershell
# Option A: run directly (recommended if there is no npm start script)
node src/server.js

# Option B: if a start script exists in package.json
npm run start
```

4. Environment variables

- Create a `.env` file (or set environment variables) for DB connection, JWT secret, SMTP creds, etc. Typical variables:

```
MONGODB_URI=mongodb://localhost:27017/ai_assistant
JWT_SECRET=your_jwt_secret
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=you@example.com
SMTP_PASS=yourpassword
```

Backend (Python)

1. Create and activate a virtual environment:

```powershell
cd Backend/Python
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies (if a `requirements.txt` exists) or install needed packages:

```powershell
pip install -r requirements.txt
# otherwise, install packages used in the project
```

3. Run the main service (example):

```powershell
python Main.py
```

Frontend (Flutter)

1. Open a terminal and change to the Flutter project:

```powershell
cd frontend/flutter
```

2. Get packages and run:

```powershell
flutter pub get
flutter run
# or run for a specific platform: flutter run -d windows
```

Frontend (Next.js)

1. Change to the Next project:

```powershell
cd next
```

2. Install and run:

```powershell
npm install
npm run dev
# or use pnpm: pnpm install && pnpm dev
```

## Usage

- Use the REST API routes exposed by the Node backend for authentication, reminders, and other features. See `Backend/Node/src/routes` for route files and `controllers` for logic.
- The Python services may provide helper CLI scripts or importable modules used by the backend — check `Backend/Python` for details.
- The Flutter and Next frontends consume the backend API endpoints. Update the API base URL in each frontend's configuration when running locally or deploying.

## Development Notes

- Database: the project uses MongoDB via `mongoose` (see `Backend/Node/src/config/db.js`). Ensure `MONGODB_URI` points to a running DB.
- Email: email utilities use `nodemailer`. Provide SMTP credentials in environment variables to enable email features.
- Authentication: JWT tokens are used for protected routes. Make sure `JWT_SECRET` is set.

## Testing & Linting

- There are no automated tests included by default. Add tests in `Backend/Node/test` or the respective frontend test folders and add scripts to `package.json`.

## Contributing

- Fork the repository, create a feature branch, and open a pull request with a clear description of changes.
- Add or update documentation and tests when adding features.

## License

This repository includes a `LICENSE` file in the root. Follow the terms in that file when contributing or reusing code.

---

If you'd like, I can:

- Add a `start` script to `Backend/Node/package.json` (e.g. `"start": "node src/server.js"`).
- Generate a `requirements.txt` for the Python service.
- Add environment variable templates or an example `.env.example` file.

Tell me which option you prefer and I'll implement it.
