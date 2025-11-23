# Global Creole Society API Documentation

## Base URL
```
http://localhost:8000/api
```

## Authentication
All endpoints require JWT authentication except login and register.
Include the token in the header:
```
Authorization: Bearer <your_access_token>
```

---

## Friend Management

### 1. Send Friend Request
**POST** `/social/friends/request/`

**Request Body:**
```json
{
  "receiver_id": "uuid-of-user"
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "requester": {
    "id": "uuid",
    "email": "user@example.com",
    "profile_name": "username",
    "profile_image": null
  },
  "receiver": {
    "id": "uuid",
    "email": "receiver@example.com",
    "profile_name": "receiver_name",
    "profile_image": null
  },
  "status": "pending",
  "created_at": "2025-11-21T10:30:00Z",
  "updated_at": "2025-11-21T10:30:00Z"
}
```

---

### 2. List Friend Requests
**GET** `/social/friends/requests/`

Lists all pending friend requests received by the authenticated user.

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "requester": {...},
    "receiver": {...},
    "status": "pending",
    "created_at": "2025-11-21T10:30:00Z",
    "updated_at": "2025-11-21T10:30:00Z"
  }
]
```

---

### 3. Respond to Friend Request
**POST** `/social/friends/requests/{user_id}/response/`

**Note:** Use the UUID of the user who sent you the friend request.

**Request Body:**
```json
{
  "action": "accept"  // or "reject"
}
```

**Response:** `200 OK` (if accepted) or `200 OK` (if rejected)

---

### 4. List Friends
**GET** `/social/friends/`

Lists all accepted friends of the authenticated user.

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "requester": {...},
    "receiver": {...},
    "status": "accepted",
    "created_at": "2025-11-20T10:30:00Z",
    "updated_at": "2025-11-21T10:30:00Z"
  }
]
```

---

### 5. Unfriend
**DELETE** `/social/friends/{user_id}/unfriend/`

**Note:** Use the UUID of the user you want to unfriend.

**Response:** `200 OK`
```json
{
  "message": "Friend removed successfully"
}
```

---

## Posts

### 1. Create Post
**POST** `/social/posts/create/`

**Request Body (multipart/form-data):**
```
content: "This is my post content"
privacy: "public"  // or "friends", "private"
society: "uuid-of-society"  // optional
media_files[]: file1.jpg  // optional, multiple files
media_files[]: file2.jpg
media_captions[]: "Caption for first image"  // optional
media_captions[]: "Caption for second image"
```

**Response:** `201 Created`

---

### 2. List Posts (Feed)
**GET** `/social/posts/`

Returns posts visible to the authenticated user (feed).

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "profile_name": "username",
      "profile_image": null
    },
    "content": "Post content",
    "privacy": "public",
    "society": "uuid",
    "society_name": "Society Name",
    "media": [
      {
        "id": 1,
        "media_type": "image",
        "file": "/media/post_media/2025/11/21/image.jpg",
        "caption": "Caption",
        "created_at": "2025-11-21T10:30:00Z"
      }
    ],
    "like_count": 5,
    "comment_count": 3,
    "is_liked": false,
    "created_at": "2025-11-21T10:30:00Z",
    "updated_at": "2025-11-21T10:30:00Z"
  }
]
```

---

### 3. Get Post Details
**GET** `/social/posts/{post_id}/`

**Response:** `200 OK` (same structure as list)

---

### 4. Update Post
**PUT/PATCH** `/social/posts/{post_id}/`

**Request Body:**
```json
{
  "content": "Updated content",
  "privacy": "friends"
}
```

**Response:** `200 OK`

---

### 5. Delete Post
**DELETE** `/social/posts/{post_id}/`

**Response:** `204 No Content`

---

### 6. Like/Unlike Post
**POST** `/social/posts/{post_id}/like/`

Toggles like on a post.

**Response:** `201 Created` or `200 OK`
```json
{
  "message": "Post liked",
  "liked": true
}
```

---

### 7. List Comments on Post
**GET** `/social/posts/{post_id}/comments/`

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "user": {...},
    "post": "uuid",
    "content": "Nice post!",
    "like_count": 2,
    "is_liked": false,
    "created_at": "2025-11-21T10:30:00Z",
    "updated_at": "2025-11-21T10:30:00Z"
  }
]
```

---

### 8. Create Comment on Post
**POST** `/social/posts/{post_id}/comments/`

**Request Body:**
```json
{
  "content": "This is my comment"
}
```

**Response:** `201 Created`

---

### 9. Update Comment
**PUT/PATCH** `/social/comments/{comment_id}/`

**Request Body:**
```json
{
  "content": "Updated comment"
}
```

**Response:** `200 OK`

---

### 10. Delete Comment
**DELETE** `/social/comments/{comment_id}/`

**Response:** `204 No Content`

---

### 11. Like/Unlike Comment
**POST** `/social/comments/{comment_id}/like/`

Toggles like on a comment.

**Response:** `201 Created` or `200 OK`
```json
{
  "message": "Comment liked",
  "liked": true
}
```

---

## Societies (Groups)

### 1. List Societies
**GET** `/social/societies/`

Lists societies with optional filtering.

**Query Parameters:**
- `my_societies=true`: Returns only societies the user is a member of
- `available=true`: Returns only societies the user is NOT a member of (available to join)
- No parameters: Returns both user's societies and public societies

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "name": "Creole Culture Society",
    "description": "A community for Creole culture enthusiasts",
    "cover_image": "/media/society_covers/image.jpg",
    "cover_picture": "/media/society_covers/image.jpg",
    "privacy": "public",
    "creator": {...},
    "member_count": 25,
    "members_count": 25,
    "is_member": true,
    "user_membership": {
      "status": "accepted",
      "role": "member"
    },
    "created_at": "2025-11-21T10:30:00Z",
    "updated_at": "2025-11-21T10:30:00Z"
  }
]
```

---

### 2. Create Society
**POST** `/social/societies/create/`

**Request Body (multipart/form-data):**
```
name: "My Society"
description: "Society description"
privacy: "public"  // or "private"
cover_image: file.jpg  // optional
```

**Response:** `201 Created`

---

### 3. Get Society Details
**GET** `/social/societies/{society_id}/`

**Response:** `200 OK` (same structure as list)

---

### 4. Update Society
**PUT/PATCH** `/social/societies/{society_id}/`

Only admins can update.

**Request Body:**
```json
{
  "name": "Updated Society Name",
  "description": "Updated description"
}
```

**Response:** `200 OK`

---

### 5. Delete Society
**DELETE** `/social/societies/{society_id}/`

Only the creator can delete.

**Response:** `204 No Content`

---

### 6. Join Society
**POST** `/social/societies/{society_id}/join/`

Joins a public society immediately or sends a join request for private societies.

**Response:** `201 Created`
```json
{
  "id": 1,
  "user": {...},
  "society": "Society Name",
  "status": "accepted",  // or "pending" for private societies
  "role": "member",
  "created_at": "2025-11-21T10:30:00Z",
  "updated_at": "2025-11-21T10:30:00Z"
}
```

---

### 7. Leave Society
**DELETE** `/social/societies/{society_id}/leave/`

**Response:** `200 OK`
```json
{
  "message": "Left society successfully"
}
```

---

### 8. List Society Members
**GET** `/social/societies/{society_id}/members/`

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "user": {...},
    "society": "Society Name",
    "status": "accepted",
    "role": "admin",  // or "moderator", "member"
    "created_at": "2025-11-21T10:30:00Z",
    "updated_at": "2025-11-21T10:30:00Z"
  }
]
```

---

### 9. List Society Posts
**GET** `/social/societies/{society_id}/posts/`

Lists all posts in the society.

**Response:** `200 OK` (same structure as post list)

---

## Stories

### 1. List Stories
**GET** `/social/stories/`

Lists active stories from friends and public stories.

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "user": {...},
    "content": "Story text",
    "privacy": "public",
    "media": [
      {
        "id": 1,
        "media_type": "image",
        "file": "/media/story_media/2025/11/21/story.jpg",
        "created_at": "2025-11-21T10:30:00Z"
      }
    ],
    "view_count": 10,
    "is_viewed": false,
    "is_active": true,
    "created_at": "2025-11-21T10:30:00Z",
    "expires_at": "2025-11-22T10:30:00Z"
  }
]
```

---

### 2. Create Story
**POST** `/social/stories/create/`

**Request Body (multipart/form-data):**
```
content: "Story text"  // optional
privacy: "public"  // or "friends", "private"
media_files[]: file1.jpg  // optional, multiple files
```

**Response:** `201 Created`

---

### 3. Get Story Details
**GET** `/social/stories/{story_id}/`

Viewing a story automatically records it as viewed.

**Response:** `200 OK` (same structure as list)

---

### 4. Delete Story
**DELETE** `/social/stories/{story_id}/`

Only the story owner can delete.

**Response:** `204 No Content`

---

## Notifications

### 1. List Notifications
**GET** `/social/notifications/`

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "sender": {...},
    "notification_type": "friend_request",
    "message": "John sent you a friend request",
    "post": "uuid",
    "post_content": "Post content",
    "comment": "uuid",
    "society": "uuid",
    "society_name": "Society Name",
    "is_read": false,
    "created_at": "2025-11-21T10:30:00Z"
  }
]
```

**Notification Types:**
- `friend_request` - Someone sent you a friend request
- `friend_accept` - Someone accepted your friend request
- `post_like` - Someone liked your post
- `post_comment` - Someone commented on your post
- `comment_like` - Someone liked your comment
- `society_invite` - You were invited to a society
- `society_join` - Someone wants to join your society

---

### 2. Mark Notifications as Read
**POST** `/social/notifications/mark-read/`

**Request Body (optional):**
```json
{
  "notification_ids": ["uuid1", "uuid2"]  // optional, omit to mark all as read
}
```

**Response:** `200 OK`
```json
{
  "message": "Notifications marked as read"
}
```

---

## User Blocking

### 1. Block User
**POST** `/social/users/{user_id}/block/`

Blocks a user and removes friendship if exists.

**Response:** `201 Created`
```json
{
  "message": "User blocked successfully"
}
```

---

### 2. Unblock User
**DELETE** `/social/users/{user_id}/unblock/`

**Response:** `200 OK`
```json
{
  "message": "User unblocked successfully"
}
```

---

## Privacy & Permissions

### Post Privacy Levels:
- **public**: Everyone can see
- **friends**: Only friends can see
- **private**: Only the post owner can see

### Society Privacy Levels:
- **public**: Anyone can view and join immediately
- **private**: Only members can view, join requests require approval

### Society Roles:
- **admin**: Can manage settings, moderate, and post
- **moderator**: Can moderate (delete posts/comments) and post
- **member**: Can post only

---

## Error Responses

All endpoints may return the following error responses:

**400 Bad Request**
```json
{
  "error": "Error message here"
}
```

**401 Unauthorized**
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**403 Forbidden**
```json
{
  "error": "You don't have permission to perform this action"
}
```

**404 Not Found**
```json
{
  "detail": "Not found."
}
```

---

## Testing the API

### Example: Create a post with curl

```bash
curl -X POST http://localhost:8000/api/social/posts/create/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "content=Hello World!" \
  -F "privacy=public" \
  -F "media_files=@/path/to/image.jpg"
```

### Example: Get feed

```bash
curl -X GET http://localhost:8000/api/social/posts/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Example: Send friend request

```bash
curl -X POST http://localhost:8000/api/social/friends/request/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"receiver_id": "uuid-of-user"}'
```

---

## Running the Server

```bash
# Activate virtual environment
source env/bin/activate

# Run migrations (first time only)
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

The API will be available at `http://localhost:8000/api/`
