# Django Chat API

A backend for a one-to-one real-time chat application. It combines a Django REST API for registration, login, user discovery, message history, and profile data with Django Channels WebSockets for live chat delivery and online-presence updates.

The application uses cookie-based JSON Web Tokens (JWTs): the browser receives secure, HTTP-only access and refresh cookies after signing in, uses the access cookie for protected REST endpoints, and the same cookie is validated when a WebSocket connection is opened.

## What this project provides

- User registration, login, logout, token refresh, and profile endpoints.
- Authenticated list of users available to chat with.
- Persistent one-to-one messages stored in SQLite.
- Conversation-history endpoint for any other user.
- Live WebSocket message broadcasts through a Redis/Valkey channel layer.
- WebSocket-based presence list, maintained with a short client heartbeat.
- Django admin for inspecting users and data (after an admin user is created).

## Technology

| Area | Package / service | Purpose |
| --- | --- | --- |
| HTTP framework | Django 4.2 | Project configuration, ORM, admin, and routing |
| REST API | Django REST Framework | Serializers, views, authentication, and JSON responses |
| Authentication | Simple JWT | Signed access and refresh tokens, including refresh-token blacklisting |
| Real-time transport | Django Channels + Daphne | ASGI WebSocket server and consumers |
| Realtime broker | Redis or Valkey | Shared Channels layer used to broadcast chat and presence events |
| Cross-origin support | django-cors-headers | CORS response headers for a separate frontend |
| Database | SQLite | Development database; configured in `django_chat/settings.py` |

## Architecture at a glance

```text
Browser / frontend
  |
  | HTTPS REST requests + HTTP-only JWT cookies
  v
Django REST API
  |-- /api/register/, /api/login/, /api/refresh/, /api/logout/
  |-- /api/profile/, /api/people/, /api/messages/<user_id>
  |
  | WebSocket upgrade (cookie is checked by JwtCookieAuthMiddleware)
  v
Django Channels consumers
  |-- /ws/chat/<room_name>/      live chat events
  |-- /ws/presence/              online-user events
  |                |
  |                v
  |          Redis / Valkey channel layer
  |
  v
SQLite database
  |-- Django User records
  `-- Message records
```

### Request and message lifecycle

1. A user registers or logs in through the REST API. The server sets `access` and `refresh` JWT cookies.
2. The frontend calls protected REST endpoints. `CookieJWTAuthentication` reads and validates the `access` cookie.
3. When the frontend opens a WebSocket, `JwtCookieAuthMiddleware` reads the same `access` cookie and attaches the authenticated user to `scope["user"]`.
4. A chat client sends JSON containing a message and a recipient ID. `ChatConsumer` saves a `Message` row, then broadcasts the resulting event to the chosen chat group.
5. Clients connected to that same chat group receive the event immediately. REST remains the source for loading earlier message history.
6. A presence client sends a `ping` every few seconds. `PresenceConsumer` records the last-seen time in the cache and broadcasts the users active in the last 10 seconds.

## Repository layout

```text
django_chat/
├── manage.py                   # Django command-line entry point
├── requirements.txt            # Python dependencies
├── django_chat/                # Project configuration
│   ├── settings.py              # Installed apps, JWT, database, Redis/Valkey layer
│   ├── urls.py                  # Top-level REST URL includes
│   └── asgi.py                  # HTTP + WebSocket ASGI routing
├── authentication/             # Account and cookie-JWT features
│   ├── views.py                 # Register, login, logout, refresh, profile
│   ├── serializers.py           # Input validation and user serialization
│   ├── authentication.py        # REST authentication from the access cookie
│   ├── utils.py                 # Token creation and cookie helpers
│   └── urls.py                  # Authentication endpoint routes
└── chat/                       # Chat data and real-time features
    ├── models.py                # Message model
    ├── views.py                 # People list and message-history API
    ├── serializers.py           # User and message API representation
    ├── consumers.py             # Chat and presence WebSocket consumers
    ├── middleware.py            # WebSocket JWT-cookie authentication
    ├── routing.py               # WebSocket URL patterns
    └── migrations/              # Database schema history
```

## Prerequisites

- Python 3.10 or later.
- Redis or Valkey running locally for development, or a hosted Redis-compatible URL for deployment.
- `pip` and a virtual environment tool such as Python's built-in `venv`.

> The application is configured to use SQLite, so no separate SQL database is required for local development.

## Run locally

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install packages and apply database migrations:

```powershell
pip install -r requirements.txt
python manage.py migrate
```

Start Redis or Valkey on the default local port (`6379`), then start the ASGI development server:

```powershell
daphne -p 8000 django_chat.asgi:application
```

Alternatively, `python manage.py runserver` is convenient during development, although Daphne most closely matches the configured ASGI deployment.

The server will be available at `http://127.0.0.1:8000`.

### Local-development configuration note

`DEBUG` is currently set to `False`. With that setting, the Channels layer requires the `VALKEY_URL` environment variable. To run the provided local Redis configuration, set `DEBUG = True` temporarily in `django_chat/settings.py`; it then connects to `127.0.0.1:6379`.

For cookie-based authentication in a plain HTTP local environment, the cookies are currently marked `secure=True`, so most browsers will not store them over `http://localhost`. Use HTTPS locally or temporarily use development-only cookie settings. Never deploy production cookies without `secure=True`.

## Environment variables

Create a `.env` file in the repository root for deployment configuration:

```dotenv
VALKEY_URL=redis://:password@host:6379/0
```

`VALKEY_URL` is read when `DEBUG = False` and is passed to `channels_redis`. Do not commit credentials or a production Django secret key.

## REST API reference

All REST paths below have the `/api/` prefix. Login and registration are public. The remaining protected endpoints require a valid `access` cookie.

| Method | Endpoint | Authentication | Description |
| --- | --- | --- | --- |
| `POST` | `/api/register/` | No | Create a user and set access/refresh cookies |
| `POST` | `/api/login/` | No | Validate credentials and set access/refresh cookies |
| `POST` | `/api/logout/` | Yes | Blacklist the refresh token and expire both cookies |
| `POST` | `/api/refresh/` | No refresh cookie required in request | Issue a new access cookie from the refresh cookie |
| `GET` | `/api/profile/` | Yes | Return the currently authenticated user |
| `GET` | `/api/people/` | Yes | Return all Django users (`id`, `username`) |
| `GET` | `/api/messages/<id>` | Yes | Return the complete conversation with user `<id>` |

### Register

`POST /api/register/`

```json
{
  "username": "ada",
  "email": "ada@example.com",
  "password": "a-strong-password"
}
```

On success, the response status is `201 Created` and has this body:

```json
{
  "message": "User registered successfully",
  "id": 1
}
```

The server also sets HTTP-only `access` and `refresh` cookies. The password must be at least eight characters long.

### Login

`POST /api/login/`

```json
{
  "username": "ada",
  "password": "a-strong-password"
}
```

Successful login returns the user ID and sets new JWT cookies. Invalid credentials produce a serializer validation error.

### Profile

`GET /api/profile/`

```json
{
  "user": {
    "id": 1,
    "username": "ada"
  }
}
```

### People and message history

`GET /api/people/` returns an array of users:

```json
[
  {"id": 1, "username": "ada"},
  {"id": 2, "username": "grace"}
]
```

`GET /api/messages/2` returns messages where the current user and user 2 are either sender or recipient, ordered oldest first. Asking for your own ID returns an empty list. The `MessageSerializer` currently exposes every model field, including `sender`, `recipient`, message text, file field value, read status, and timestamps.

## WebSocket reference

WebSocket connections rely on the `access` cookie sent during the handshake. An unauthenticated connection is closed immediately.

### Chat socket

```text
ws://<host>/ws/chat/<room_name>/
```

`room_name` is an application-defined string. Every client in the same room receives every event sent to that room. A frontend should derive it deterministically from the two participant IDs (for example, `chat_1_2` after sorting the IDs) so that both users join the same room.

Send a message:

```json
{
  "message": "Hello, Grace!",
  "recipient": 2
}
```

The consumer persists the message and broadcasts an event shaped like:

```json
{
  "type": "chat_message",
  "id": 42,
  "sender": 1,
  "recipient": 2,
  "message": "Hello, Grace!",
  "file": null,
  "created_at": "2026-08-31T12:34:56.000000+00:00"
}
```

### Presence socket

```text
ws://<host>/ws/presence/
```

After connecting, send this periodically—more frequently than every 10 seconds—to remain online:

```json
{"type": "ping"}
```

Every client connected to the presence group receives an update like:

```json
{
  "online": [
    {"userId": "1", "username": "ada"},
    {"userId": "2", "username": "grace"}
  ]
}
```

## Data model

### `Message`

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | Big integer, primary key | Unique message identifier |
| `sender` | Foreign key to `User` | User who wrote the message |
| `recipient` | Foreign key to `User` | User the message is addressed to |
| `message` | Text | Message content; it may be blank |
| `file` | File field | Optional attachment path |
| `is_read` | Boolean | Read-state flag; defaults to `false` |
| `created_at` | Date/time | Set automatically when created |
| `updated_at` | Date/time | Updated automatically whenever saved |

Deleting a user deletes their sent and received messages because both foreign keys use `CASCADE`. The composite database index on `(sender, recipient, created_at)` supports common ordered conversation queries.

## Authentication design

The project deliberately keeps JWTs out of JavaScript-readable storage:

- `RegisterAPIView` and `LoginAPIView` create an access token (60 minutes) and refresh token (1 day).
- `set_auth_cookies` stores them as HTTP-only cookies with `Secure` and `SameSite=None` attributes.
- REST endpoints use `CookieJWTAuthentication`, a subclass of Simple JWT's authentication class that reads the `access` cookie instead of an `Authorization` header.
- WebSocket handshakes use `JwtCookieAuthMiddleware`, which validates the same cookie and sets the Channels user.
- Logging out blacklists the refresh token when possible and expires both cookies.

Because `SameSite=None` permits cross-site cookies, production must use HTTPS and a restricted list of trusted frontend origins. See the security notes below.

## Important current limitations and recommended next steps

This repository is a useful working foundation, but these items should be addressed before treating it as a production-ready chat service:

1. **Secrets are in source code.** `SECRET_KEY` is hard-coded in `settings.py`. Load it from an environment variable and rotate the exposed key.
2. **CORS is permissive.** `CORS_ORIGIN_ALLOW_ALL = True` together with credentialed cookies is not an appropriate production policy. Set explicit allowed origins and configure CSRF trusted origins for the frontend.
3. **Room authorization is not enforced.** Any authenticated user who knows a room name can join it, and `ChatConsumer` does not verify that the room corresponds to the sender and recipient. Derive room names safely and add server-side participant validation.
4. **Message recipient errors are not handled.** A nonexistent or missing `recipient` can raise an exception in the consumer. Validate inbound WebSocket data and return structured errors instead.
5. **File attachments are incomplete.** A WebSocket JSON payload cannot upload a browser file directly; the consumer currently receives only a value and the project has no `MEDIA_ROOT`/`MEDIA_URL` configuration. Add a dedicated authenticated upload endpoint and object storage before exposing attachments.
6. **Read receipts are not implemented.** The `is_read` field exists, but no endpoint or WebSocket event updates it.
7. **Presence is simple and process-sensitive.** Presence is stored as one cache dictionary, with a 10-second heartbeat timeout. Improve it for multiple tabs, atomic updates, cleanup, and connection tracking as traffic grows.
8. **Tests have not been written yet.** Both app test modules only contain Django's starter placeholder. Add tests for authentication, authorization, cookie behavior, WebSocket events, and invalid inputs.
9. **The dependencies and comments disagree about Django version.** `requirements.txt` pins Django 4.2.27 while settings comments mention Django 6.0. Keep the documentation and dependency target aligned.

## Production checklist

- Set `DEBUG=False`.
- Supply a strong `SECRET_KEY` through the deployment environment.
- Set a real `VALKEY_URL` and verify the service can connect to it.
- Replace SQLite with a managed database such as PostgreSQL for concurrent production traffic.
- Restrict `ALLOWED_HOSTS`, CORS origins, and CSRF trusted origins to known domains.
- Keep cookie `Secure` enabled and serve only through HTTPS.
- Configure static-file collection and a media storage solution if attachments are supported.
- Run Daphne (or another ASGI server) behind a reverse proxy that supports WebSocket upgrades.
- Create and run an automated test suite in CI.

## Useful Django commands

```powershell
# Create an administrator account
python manage.py createsuperuser

# Create migrations after changing models
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Open the Django shell
python manage.py shell

# Run the test suite
python manage.py test
```

Visit `/admin/` after creating a superuser to sign in to Django's administration site.

## Contributing

1. Create a focused branch from the current main branch.
2. Make the smallest cohesive change needed for the feature or fix.
3. Add or update tests for the behavior.
4. Run `python manage.py test` and any relevant manual WebSocket checks.
5. Update this README whenever routes, configuration, or client-facing event formats change.

## License

No license file is currently included. Add a `LICENSE` file before publishing or accepting external contributions so users know how the code may be used.
