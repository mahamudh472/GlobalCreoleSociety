# Chat Application API Documentation

## Overview

The Chat Application provides comprehensive messaging functionality including:
- One-on-one private conversations
- Real-time messaging via WebSockets
- File upload support (images, videos, documents)
- Message read receipts
- Unread message counting
- Global chat room for all users
- Conversation management (create, list, delete)

---

## WebSocket Endpoints

### Private Chat WebSocket

**Endpoint:** `ws://localhost:8000/ws/chat/<conversation_id>/`

**Authentication:** Required (JWT token in query params or cookies)

**Connection:**
```javascript
const conversationId = 'uuid-here';
const token = 'your-jwt-token';
const socket = new WebSocket(`ws://localhost:8000/ws/chat/${conversationId}/?token=${token}`);
```

**Message Types:**

#### 1. Send Message
```json
{
  "type": "chat_message",
  "content": "Hello there!"
}
```

#### 2. Mark Message as Read
```json
{
  "type": "mark_read",
  "message_id": "message-uuid"
}
```

#### 3. Typing Indicator
```json
{
  "type": "typing",
  "is_typing": true
}
```

**Received Message Types:**

#### Connection Established
```json
{
  "type": "connection_established",
  "message": "Connected to chat"
}
```

#### Chat Message
```json
{
  "type": "chat_message",
  "message": {
    "id": "uuid",
    "sender": {...},
    "content": "Hello!",
    "created_at": "2025-11-22T10:00:00Z",
    "is_read": false
  }
}
```

#### Message Read Notification
```json
{
  "type": "message_read",
  "message_id": "uuid",
  "user_id": "uuid"
}
```

#### Typing Indicator
```json
{
  "type": "typing_indicator",
  "user_id": "uuid",
  "is_typing": true
}
```

---

### Global Chat WebSocket

**Endpoint:** `ws://localhost:8000/ws/global-chat/`

**Authentication:** Required

**Connection:**
```javascript
const token = 'your-jwt-token';
const socket = new WebSocket(`ws://localhost:8000/ws/global-chat/?token=${token}`);
```

**Message Types:**

#### 1. Send Message
```json
{
  "type": "chat_message",
  "content": "Hello everyone!"
}
```

#### 2. Typing Indicator
```json
{
  "type": "typing",
  "is_typing": true
}
```

**Received Message Types:**

#### User Joined
```json
{
  "type": "user_joined",
  "user_id": "uuid",
  "username": "john_doe"
}
```

#### User Left
```json
{
  "type": "user_left",
  "user_id": "uuid",
  "username": "john_doe"
}
```

#### Chat Message
```json
{
  "type": "chat_message",
  "message": {
    "id": "uuid",
    "sender": {...},
    "content": "Hello everyone!",
    "created_at": "2025-11-22T10:00:00Z"
  }
}
```

#### Typing Indicator
```json
{
  "type": "typing_indicator",
  "user_id": "uuid",
  "username": "jane_doe",
  "is_typing": true
}
```

---

## REST API Endpoints

### Conversations

#### 1. List Conversations
**GET** `/api/chat/conversations/`

Get all conversations for the authenticated user.

**Query Parameters:**
- `unread_only` (boolean): Filter conversations with unread messages only

**Response:**
```json
{
  "count": 10,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "other_participant": {
        "id": "uuid",
        "profile_name": "john_doe",
        "profile_image": "url"
      },
      "last_message": {
        "id": "uuid",
        "content": "Last message...",
        "created_at": "2025-11-22T10:00:00Z",
        "is_read": false
      },
      "unread_count": 5,
      "updated_at": "2025-11-22T10:00:00Z"
    }
  ]
}
```

#### 2. Get Conversation Details
**GET** `/api/chat/conversations/<conversation_id>/`

Get details of a specific conversation.

**Response:**
```json
{
  "id": "uuid",
  "participants": [
    {
      "id": "uuid",
      "profile_name": "john_doe",
      "profile_image": "url",
      "email": "john@example.com"
    }
  ],
  "other_participant": {...},
  "last_message": {...},
  "unread_count": 5,
  "created_at": "2025-11-20T10:00:00Z",
  "updated_at": "2025-11-22T10:00:00Z"
}
```

#### 3. Create/Get Conversation
**POST** `/api/chat/conversations/`

Create a new conversation or get existing one with another user.

**Request Body:**
```json
{
  "user_id": "uuid-of-other-user"
}
```

**Response:**
```json
{
  "id": "uuid",
  "participants": [...],
  "created_at": "2025-11-22T10:00:00Z"
}
```

#### 4. Get Conversation Messages
**GET** `/api/chat/conversations/<conversation_id>/messages/`

Get all messages in a conversation (paginated).

**Response:**
```json
{
  "count": 100,
  "next": "url",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "sender": {
        "id": "uuid",
        "profile_name": "john_doe",
        "profile_image": "url"
      },
      "content": "Hello!",
      "file": null,
      "file_url": null,
      "file_type": "",
      "is_read": true,
      "read_at": "2025-11-22T10:05:00Z",
      "created_at": "2025-11-22T10:00:00Z"
    }
  ]
}
```

#### 5. Send Message (REST)
**POST** `/api/chat/conversations/<conversation_id>/send_message/`

Send a message via REST API (alternative to WebSocket).

**Request Body (JSON):**
```json
{
  "content": "Hello there!"
}
```

**Request Body (Multipart - with file):**
```
content: "Check this out!"
file: <binary file data>
file_type: "image"
```

**Response:**
```json
{
  "id": "uuid",
  "sender": {...},
  "content": "Hello there!",
  "file": null,
  "file_url": null,
  "created_at": "2025-11-22T10:00:00Z"
}
```

#### 6. Mark Conversation as Read
**POST** `/api/chat/conversations/<conversation_id>/mark_as_read/`

Mark all unread messages in a conversation as read.

**Response:**
```json
{
  "message": "Messages marked as read",
  "count": 5
}
```

#### 7. Get Total Unread Count
**GET** `/api/chat/conversations/unread_count/`

Get total number of unread messages across all conversations.

**Response:**
```json
{
  "unread_count": 15
}
```

#### 8. Delete Conversation
**DELETE** `/api/chat/conversations/<conversation_id>/`

Delete a conversation and all its messages.

**Response:** `204 No Content`

---

### Messages

#### 1. List All Messages
**GET** `/api/chat/messages/`

Get all messages from all conversations the user is part of.

**Response:**
```json
{
  "count": 500,
  "next": "url",
  "previous": null,
  "results": [...]
}
```

#### 2. Get Message Details
**GET** `/api/chat/messages/<message_id>/`

Get details of a specific message.

**Response:**
```json
{
  "id": "uuid",
  "conversation": "uuid",
  "sender": {...},
  "content": "Hello!",
  "file": null,
  "file_url": null,
  "file_type": "",
  "is_read": true,
  "read_at": "2025-11-22T10:05:00Z",
  "created_at": "2025-11-22T10:00:00Z"
}
```

#### 3. Mark Single Message as Read
**POST** `/api/chat/messages/<message_id>/mark_read/`

Mark a specific message as read.

**Response:**
```json
{
  "id": "uuid",
  "is_read": true,
  "read_at": "2025-11-22T10:05:00Z",
  ...
}
```

---

### Global Chat

#### 1. List Global Messages
**GET** `/api/chat/global-chat/`

Get global chat messages (paginated, most recent first).

**Response:**
```json
{
  "count": 1000,
  "next": "url",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "sender": {
        "id": "uuid",
        "profile_name": "john_doe",
        "profile_image": "url"
      },
      "content": "Hello everyone!",
      "file": null,
      "file_url": null,
      "file_type": "",
      "created_at": "2025-11-22T10:00:00Z"
    }
  ]
}
```

#### 2. Send Global Message (REST)
**POST** `/api/chat/global-chat/send_message/`

Send a message to global chat via REST API.

**Request Body (JSON):**
```json
{
  "content": "Hello everyone!"
}
```

**Request Body (Multipart - with file):**
```
content: "Check this out!"
file: <binary file data>
file_type: "image"
```

**Response:**
```json
{
  "id": "uuid",
  "sender": {...},
  "content": "Hello everyone!",
  "created_at": "2025-11-22T10:00:00Z"
}
```

---

## File Upload Support

Both private and global chat support file uploads.

**Supported File Types:**
- Images: `image/jpeg`, `image/png`, `image/gif`, etc.
- Videos: `video/mp4`, `video/avi`, etc.
- Documents: `application/pdf`, `application/msword`, etc.
- Audio: `audio/mp3`, `audio/wav`, etc.

**File Upload via REST API:**

Use `multipart/form-data` encoding:

```javascript
const formData = new FormData();
formData.append('content', 'Check out this file!');
formData.append('file', fileObject);
formData.append('file_type', 'image');

fetch('/api/chat/conversations/<id>/send_message/', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + token
  },
  body: formData
});
```

**File Upload via WebSocket:**

For file uploads via WebSocket, first upload the file using the REST API, then broadcast the message via WebSocket.

---

## Authentication

All endpoints require JWT authentication.

**Header Format:**
```
Authorization: Bearer <your-jwt-token>
```

**WebSocket Authentication:**

Pass token as query parameter:
```
ws://localhost:8000/ws/chat/<id>/?token=<your-jwt-token>
```

Or use cookies if configured.

---

## Error Responses

**400 Bad Request:**
```json
{
  "error": "Message must have content or file"
}
```

**403 Forbidden:**
```json
{
  "error": "You are not a participant in this conversation"
}
```

**404 Not Found:**
```json
{
  "error": "User not found"
}
```

---

## Usage Examples

### Create and Start a Conversation

1. **Create conversation:**
```javascript
POST /api/chat/conversations/
{
  "user_id": "other-user-uuid"
}
```

2. **Connect to WebSocket:**
```javascript
const socket = new WebSocket(`ws://localhost:8000/ws/chat/${conversationId}/?token=${token}`);

socket.onopen = () => {
  console.log('Connected to chat');
};

socket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};
```

3. **Send messages:**
```javascript
socket.send(JSON.stringify({
  type: 'chat_message',
  content: 'Hello!'
}));
```

### List Unread Conversations

```javascript
GET /api/chat/conversations/?unread_only=true
```

### Upload File with Message

```javascript
const formData = new FormData();
formData.append('content', 'Check this image!');
formData.append('file', imageFile);
formData.append('file_type', 'image');

fetch('/api/chat/conversations/<id>/send_message/', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + token
  },
  body: formData
});
```

---

## Notes

1. **Redis Required:** The WebSocket functionality requires Redis to be running:
   ```bash
   redis-server
   ```

2. **Running the Server:**
   ```bash
   # For development with WebSocket support
   python manage.py runserver
   # Or use Daphne for production
   daphne -b 0.0.0.0 -p 8000 GlobalCreoleSociety.asgi:application
   ```

3. **Message Ordering:** Messages are ordered by creation time in ascending order within conversations.

4. **Pagination:** Most list endpoints support pagination. Use `page` and `page_size` query parameters.

5. **Real-time Updates:** For best user experience, use WebSockets for real-time messaging and REST API for initial data loading and file uploads.
