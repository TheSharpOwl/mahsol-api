# Mobile API Guide

Small reference for the mobile app team working with the Farming Assistant backend.

## Base URL

- Local: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`
- Health check: `GET /healthz`

Example health response:

```json
{
  "status": "ok",
  "service": "Farming Assistant API"
}
```

## Auth

Most endpoints require a Bearer token:

```http
Authorization: Bearer <access_token>
```

The token is returned by signup and login.

## Main App Flow

1. Sign up or log in.
2. Save the returned `access_token`.
3. Create or update the user's land info.
4. Read assistant insights or reports.
5. Use chat either with HTTP or WebSocket.

## Authentication Endpoints

### `POST /auth/signup`

Creates a new user and returns an access token.

Request:

```json
{
  "name": "Ziad",
  "email": "ziad@example.com",
  "password": "secret123",
  "role": "farmer"
}
```

Notes:

- Allowed roles for signup: `farmer`, `expert`
- `admin` cannot self-register
- Returns `409` if email already exists

Response:

```json
{
  "access_token": "jwt-token",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "name": "Ziad",
    "email": "ziad@example.com",
    "role": "farmer",
    "created_at": "2026-04-18T12:00:00Z"
  }
}
```

### `POST /auth/login`

Logs the user in and returns the same token shape as signup.

Request:

```json
{
  "email": "ziad@example.com",
  "password": "secret123"
}
```

Returns `401` for invalid credentials.

## Land Info

### `POST /land-info`

Creates land info the first time, then updates the same record on later calls.

Auth required: yes

Request:

```json
{
  "latitude": 33.5138,
  "longitude": 36.2765,
  "soil_type": "clay",
  "crop_type": "wheat",
  "additional_notes": "north field"
}
```

Response:

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "latitude": 33.5138,
  "longitude": 36.2765,
  "soil_type": "clay",
  "crop_type": "wheat",
  "additional_notes": "north field",
  "created_at": "2026-04-18T12:00:00Z",
  "updated_at": "2026-04-18T12:00:00Z",
  "weather": {
    "temperature": 25.0,
    "description": "partly cloudy"
  }
}
```

### `GET /land-info/me`

Returns the current user's saved land info with weather attached.

Auth required: yes

Returns `404` if land info has not been saved yet.

## Reports and Insights

### `GET /reports`

Returns all saved reports for the current user, newest first.

Auth required: yes

Response item shape:

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "weather_data": {},
  "warning": "Possible irrigation issue",
  "report_text": "Today's farming advice...",
  "created_at": "2026-04-18T06:00:00Z"
}
```

### `GET /reports/latest`

Returns the newest report only.

Auth required: yes

Returns `404` if no reports exist yet.

### `GET /reports/assistant/insights`

Returns an on-demand AI summary using the latest land info and live weather.

Auth required: yes

Response:

```json
{
  "land": {
    "soil_type": "clay",
    "crop_type": "wheat"
  },
  "weather": {},
  "advice": "AI-generated advice text"
}
```

Returns `404` if the user has no land info yet.

## Conversations

### `POST /conversations`

Creates an empty conversation.

Auth required: yes

Request body:

```json
{}
```

Response:

```json
{
  "id": "conversation-uuid",
  "user_id": "user-uuid",
  "created_at": "2026-04-18T12:00:00Z"
}
```

### `GET /conversations`

Returns all conversations for the current user with their messages included.

Auth required: yes

Each message looks like:

```json
{
  "id": "message-uuid",
  "conversation_id": "conversation-uuid",
  "sender_type": "user",
  "message_type": "text",
  "content": "How are my crops doing?",
  "created_at": "2026-04-18T12:05:00Z"
}
```

Enums:

- `sender_type`: `user` or `ai`
- `message_type`: `text` or `image`

## Chat via HTTP

### `POST /chat/{conversation_id}`

Sends one message and gets both the saved user message and AI reply.

Auth required: yes

Use `conversation_id = new` to create a new conversation automatically.

Request:

```json
{
  "content": "My tomato leaves have yellow spots",
  "message_type": "text",
  "file_id": null
}
```

Response:

```json
{
  "user_message": {
    "id": "uuid",
    "conversation_id": "uuid",
    "sender_type": "user",
    "message_type": "text",
    "content": "My tomato leaves have yellow spots",
    "created_at": "2026-04-18T12:10:00Z"
  },
  "ai_message": {
    "id": "uuid",
    "conversation_id": "uuid",
    "sender_type": "ai",
    "message_type": "text",
    "content": "This may indicate...",
    "created_at": "2026-04-18T12:10:01Z"
  }
}
```

Common errors:

- `400` if `content` is empty
- `404` if the conversation does not belong to the current user

## Chat via WebSocket

### `GET ws://<host>/ws/chat/{conversation_id}?token=<access_token>`

Use this for real-time chat.

Notes:

- Use `conversation_id = new` to create a new conversation on connect
- JWT token is passed in the query string, not in headers
- The server first sends a `connected` event with the actual `conversation_id`

Initial server event:

```json
{
  "type": "connected",
  "conversation_id": "conversation-uuid"
}
```

Client message format:

```json
{
  "content": "Is the weather good for irrigation today?",
  "message_type": "text"
}
```

Server event types:

- `connected`
- `message`
- `typing`
- `error`

Example message event:

```json
{
  "type": "message",
  "data": {
    "id": "uuid",
    "conversation_id": "uuid",
    "sender_type": "ai",
    "message_type": "text",
    "content": "Based on the current weather...",
    "created_at": "2026-04-18T12:15:00Z"
  }
}
```

Example typing event:

```json
{
  "type": "typing",
  "data": {
    "is_typing": true
  }
}
```

WebSocket close cases:

- `4001` if token is missing or invalid
- `4004` if the conversation is not found or not owned by the user

## Integration Notes

- All protected HTTP routes use Bearer auth
- WebSocket auth uses `?token=...`
- CORS is currently open to all origins
- Timestamps are ISO datetime strings
- The backend creates database tables automatically on startup

## Recommended Mobile Integration Order

1. Implement signup and login.
2. Persist `access_token`.
3. Add land info create/load.
4. Show assistant insights and latest report.
5. Implement HTTP chat first.
6. Add WebSocket chat for real-time experience.
