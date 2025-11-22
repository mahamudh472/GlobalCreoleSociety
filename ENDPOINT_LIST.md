# Complete Endpoint List - Global Creole Society API

## Base URL
`http://localhost:8000/api`

---

## Account Management (From accounts app)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/accounts/register/` | Register a new user | No |
| POST | `/accounts/login/` | Login and get JWT token | No |
| POST | `/accounts/logout/` | Logout (blacklist token) | Yes |
| GET | `/accounts/profile/` | Get current user profile | Yes |
| PUT/PATCH | `/accounts/profile/` | Update user profile | Yes |
| POST | `/accounts/token/refresh/` | Refresh JWT token | No |
| POST | `/accounts/send-otp/` | Send OTP for verification | Yes |
| POST | `/accounts/change-password/` | Change password | Yes |
| POST | `/accounts/change-email/` | Change email | Yes |
| POST | `/accounts/change-phone-number/` | Change phone number | Yes |
| POST | `/accounts/add-email/` | Add extra email | Yes |
| POST | `/accounts/add-phone-number/` | Add extra phone | Yes |
| POST | `/accounts/profile-lock/` | Lock/unlock profile | Yes |

---

## Friend Management

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/social/friends/request/` | Send friend request | Yes |
| GET | `/social/friends/requests/` | List pending requests received | Yes |
| POST | `/social/friends/requests/{user_id}/response/` | Accept/reject friend request (user_id=UUID) | Yes |
| GET | `/social/friends/` | List all friends | Yes |
| DELETE | `/social/friends/{user_id}/unfriend/` | Remove a friend (user_id=UUID) | Yes |

**Request Body Examples:**

Send Friend Request:
```json
{
  "receiver_id": "uuid"
}
```

Respond to Friend Request:
```json
{
  "action": "accept"  // or "reject"
}
```

---

## Posts

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/social/posts/` | Get feed (all visible posts) | Yes |
| POST | `/social/posts/create/` | Create a new post | Yes |
| GET | `/social/posts/{id}/` | Get specific post details | Yes |
| PUT | `/social/posts/{id}/` | Update a post (full update) | Yes |
| PATCH | `/social/posts/{id}/` | Update a post (partial) | Yes |
| DELETE | `/social/posts/{id}/` | Delete a post | Yes |
| POST | `/social/posts/{id}/like/` | Like/unlike a post | Yes |
| GET | `/social/posts/{id}/comments/` | List comments on post | Yes |
| POST | `/social/posts/{id}/comments/` | Add comment to post | Yes |

**Request Body Examples:**

Create Post (multipart/form-data):
```
content: "Post content here"
privacy: "public"  // or "friends", "private"
society: "uuid"  // optional
media_files[]: file1.jpg
media_files[]: file2.jpg
media_captions[]: "Caption 1"
media_captions[]: "Caption 2"
```

Update Post:
```json
{
  "content": "Updated content",
  "privacy": "friends"
}
```

Create Comment:
```json
{
  "content": "Great post!"
}
```

---

## Comments

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/social/comments/{id}/` | Get specific comment | Yes |
| PUT | `/social/comments/{id}/` | Update a comment (full) | Yes |
| PATCH | `/social/comments/{id}/` | Update a comment (partial) | Yes |
| DELETE | `/social/comments/{id}/` | Delete a comment | Yes |
| POST | `/social/comments/{id}/like/` | Like/unlike a comment | Yes |

**Request Body Examples:**

Update Comment:
```json
{
  "content": "Updated comment text"
}
```

---

## Societies (Groups)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/social/societies/` | List societies | Yes |
| POST | `/social/societies/create/` | Create a society | Yes |
| GET | `/social/societies/{id}/` | Get society details | Yes |
| PUT | `/social/societies/{id}/` | Update society (full) | Yes |
| PATCH | `/social/societies/{id}/` | Update society (partial) | Yes |
| DELETE | `/social/societies/{id}/` | Delete society | Yes |
| POST | `/social/societies/{id}/join/` | Join a society | Yes |
| DELETE | `/social/societies/{id}/leave/` | Leave a society | Yes |
| GET | `/social/societies/{id}/members/` | List society members | Yes |
| GET | `/social/societies/{id}/posts/` | List posts in society | Yes |

**Request Body Examples:**

Create Society (multipart/form-data):
```
name: "Society Name"
description: "Description here"
privacy: "public"  // or "private"
cover_image: file.jpg  // optional
```

Update Society:
```json
{
  "name": "Updated Name",
  "description": "Updated description"
}
```

---

## Stories

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/social/stories/` | List active stories | Yes |
| POST | `/social/stories/create/` | Create a story | Yes |
| GET | `/social/stories/{id}/` | View a story (auto-marks viewed) | Yes |
| DELETE | `/social/stories/{id}/` | Delete a story | Yes |

**Request Body Examples:**

Create Story (multipart/form-data):
```
content: "Story text"  // optional
privacy: "public"  // or "friends", "private"
media_files[]: file1.jpg
media_files[]: file2.mp4
```

---

## Notifications

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/social/notifications/` | List all notifications | Yes |
| POST | `/social/notifications/mark-read/` | Mark notification(s) as read | Yes |

**Request Body Examples:**

Mark Specific Notifications as Read:
```json
{
  "notification_ids": ["uuid1", "uuid2"]
}
```

Mark All as Read:
```json
{}
```

---

## User Blocking

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/social/users/{id}/block/` | Block a user | Yes |
| DELETE | `/social/users/{id}/unblock/` | Unblock a user | Yes |

---

## Chat & Messaging

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/chat/conversations/` | List all user's conversations | Yes |
| POST | `/chat/conversations/` | Create/get conversation with a user | Yes |
| GET | `/chat/conversations/{id}/` | Get conversation details | Yes |
| DELETE | `/chat/conversations/{id}/` | Delete a conversation | Yes |
| GET | `/chat/conversations/{id}/messages/` | Get messages in conversation | Yes |
| POST | `/chat/conversations/{id}/send_message/` | Send message in conversation | Yes |
| POST | `/chat/conversations/{id}/mark_as_read/` | Mark conversation messages as read | Yes |
| GET | `/chat/conversations/unread_count/` | Get total unread message count | Yes |
| GET | `/chat/messages/` | List user's messages | Yes |
| GET | `/chat/messages/{id}/` | Get specific message | Yes |
| POST | `/chat/messages/{id}/mark_read/` | Mark a message as read | Yes |
| GET | `/chat/global-chat/` | List global chat messages | Yes |
| POST | `/chat/global-chat/send_message/` | Send global chat message | Yes |

**Request Body Examples:**

Create/Get Conversation:
```json
{
  "user_id": "uuid"
}
```

Send Message in Conversation (multipart/form-data):
```
content: "Hello there!"
file: image.jpg  // optional
file_type: "image"  // optional: "image", "video", "document"
```

Send Global Chat Message (multipart/form-data):
```
content: "Hello everyone!"
file: image.jpg  // optional
file_type: "image"  // optional
```

**Query Parameters:**

List Conversations:
```
?unread_only=true  // Filter to show only conversations with unread messages
```

**WebSocket Endpoints:**

Real-time chat functionality is available through WebSocket connections:

- Private Chat: `ws://localhost:8000/ws/chat/{conversation_id}/`
- Global Chat: `ws://localhost:8000/ws/global-chat/`

WebSocket Message Format (Send):
```json
{
  "type": "chat_message",
  "content": "Hello!",
  "file_type": "image",  // optional
  "file_url": "/media/..."  // optional
}
```

WebSocket Message Format (Receive):
```json
{
  "type": "chat_message",
  "message": {
    "id": "uuid",
    "sender": {
      "id": "uuid",
      "username": "user123",
      "profile_picture": "..."
    },
    "content": "Hello!",
    "file": "...",
    "file_type": "image",
    "created_at": "2025-11-23T...",
    "is_read": false
  }
}
```

---

## Shop Management

| Method | Endpoint | Description | Auth Required | Admin Only |
|--------|----------|-------------|---------------|------------|
| GET | `/shop/categories/` | List all categories | Yes | No |
| POST | `/shop/categories/` | Create a category | Yes | Yes |
| GET | `/shop/categories/{id}/` | Get category details | Yes | No |
| PUT/PATCH | `/shop/categories/{id}/` | Update a category | Yes | Yes |
| DELETE | `/shop/categories/{id}/` | Delete a category | Yes | Yes |
| GET | `/shop/products/` | List products (filtered by status) | Yes | No |
| POST | `/shop/products/` | Create a product (pending status) | Yes | No |
| GET | `/shop/products/{id}/` | Get product details | Yes | No |
| PUT/PATCH | `/shop/products/{id}/` | Update a product | Yes | Owner |
| DELETE | `/shop/products/{id}/` | Delete a product | Yes | Owner/Admin |
| GET | `/shop/products/my-products/` | List current user's products | Yes | No |
| GET | `/shop/products/pending/` | List pending products | Yes | Yes |
| POST | `/shop/products/{id}/approve/` | Approve a product | Yes | Yes |
| POST | `/shop/products/{id}/reject/` | Reject a product | Yes | Yes |
| POST | `/shop/products/{id}/add-image/` | Add image to product | Yes | Owner |
| DELETE | `/shop/products/{id}/delete-image/{image_id}/` | Delete product image | Yes | Owner |
| GET | `/shop/cart/` | Get user's cart | Yes | No |
| POST | `/shop/cart/add-item/` | Add item to cart | Yes | No |
| PATCH | `/shop/cart/update-item/{item_id}/` | Update cart item quantity | Yes | No |
| DELETE | `/shop/cart/remove-item/{item_id}/` | Remove item from cart | Yes | No |
| DELETE | `/shop/cart/clear/` | Clear all cart items | Yes | No |
| GET | `/shop/orders/` | List orders | Yes | No |
| GET | `/shop/orders/{id}/` | Get order details | Yes | Owner/Admin |
| POST | `/shop/orders/checkout/` | Checkout from cart | Yes | No |
| POST | `/shop/orders/buy-now/` | Buy single item directly | Yes | No |
| PATCH | `/shop/orders/{id}/update-status/` | Update order status | Yes | Yes |

**Request Body Examples:**

Create Category:
```json
{
  "name": "Electronics",
  "description": "Electronic devices and accessories"
}
```

Create Product (multipart/form-data):
```
name: "Smartphone X"
description: "Latest smartphone"
category: 1
price: 599.99
stock: 50
uploaded_images[]: image1.jpg
uploaded_images[]: image2.jpg
```

Approve Product:
```
POST /shop/products/{id}/approve/
(No body required)
```

Reject Product:
```json
{
  "rejection_reason": "Images are not clear"
}
```

Add Item to Cart:
```json
{
  "product_id": 1,
  "quantity": 2
}
```

Update Cart Item:
```json
{
  "quantity": 3
}
```

Checkout from Cart:
```json
{
  "cart_item_ids": [1, 2],
  "shipping_address": "123 Main St",
  "shipping_city": "New York",
  "shipping_postal_code": "10001",
  "shipping_country": "USA",
  "shipping_phone": "+1234567890",
  "notes": "Deliver between 9-5 PM"
}
```

Buy Now:
```json
{
  "product_id": 1,
  "quantity": 1,
  "shipping_address": "123 Main St",
  "shipping_city": "New York",
  "shipping_postal_code": "10001",
  "shipping_country": "USA",
  "shipping_phone": "+1234567890"
}
```

Update Order Status:
```json
{
  "status": "shipped"
}
```

---

## Endpoint Statistics

### By Category
- **Account Management**: 13 endpoints
- **Friend Management**: 5 endpoints
- **Posts**: 9 endpoints
- **Comments**: 5 endpoints
- **Societies**: 10 endpoints
- **Stories**: 4 endpoints
- **Notifications**: 2 endpoints
- **User Blocking**: 2 endpoints
- **Chat & Messaging**: 13 endpoints (+ 2 WebSocket endpoints)
- **Shop Management**: 26 endpoints

### Total: 89 REST endpoints + 2 WebSocket endpoints

### By HTTP Method
- **GET**: 30 endpoints (read operations)
- **POST**: 35 endpoints (create/action operations)
- **PUT**: 4 endpoints (full update operations)
- **PATCH**: 6 endpoints (partial update operations)
- **DELETE**: 14 endpoints (delete operations)

---

## Common URL Parameters

### Path Parameters (in URL)
- `{id}` or `{pk}` - UUID of the resource
- Examples:
  - `/social/posts/{id}/` - Replace `{id}` with actual post UUID
  - `/social/friends/{id}/unfriend/` - Replace `{id}` with friendship UUID

### Query Parameters (optional, not implemented yet but can be added)
- `?page=1` - Page number for pagination
- `?limit=20` - Number of items per page
- `?search=keyword` - Search filter
- `?ordering=-created_at` - Sort order

---

## Response Formats

### Success Response (200, 201)
```json
{
  "id": "uuid",
  "field1": "value1",
  "field2": "value2",
  ...
}
```

### List Response (200)
```json
[
  {
    "id": "uuid1",
    ...
  },
  {
    "id": "uuid2",
    ...
  }
]
```

### Action Response (200)
```json
{
  "message": "Action completed successfully"
}
```

### Delete Response (204)
No content returned

### Error Response (400, 403, 404)
```json
{
  "error": "Error message here"
}
```

or for validation errors:
```json
{
  "field_name": ["Error message for this field"]
}
```

---

## Content Types

### For JSON Data
```
Content-Type: application/json
```

### For File Uploads
```
Content-Type: multipart/form-data
```

### Authentication Header
```
Authorization: Bearer <your_access_token>
```

---

## HTTP Status Codes Used

- `200 OK` - Successful GET, PUT, PATCH
- `201 Created` - Successful POST (resource created)
- `204 No Content` - Successful DELETE
- `400 Bad Request` - Validation error or bad input
- `401 Unauthorized` - Not authenticated or invalid token
- `403 Forbidden` - No permission to perform action
- `404 Not Found` - Resource doesn't exist
- `500 Internal Server Error` - Server error

---

## Rate Limiting (Not Implemented Yet)

Consider adding rate limiting in production:
- Login attempts: 5 per minute
- Friend requests: 20 per hour
- Posts: 50 per hour
- Comments: 100 per hour
- API calls: 1000 per hour

---

## Pagination (Not Implemented Yet)

Can be added to list endpoints:
```
GET /social/posts/?page=2&limit=20
```

Response with pagination:
```json
{
  "count": 100,
  "next": "http://localhost:8000/api/social/posts/?page=3",
  "previous": "http://localhost:8000/api/social/posts/?page=1",
  "results": [...]
}
```

---

## Testing Endpoints

### Using curl
```bash
# GET request
curl -X GET http://localhost:8000/api/social/posts/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# POST request (JSON)
curl -X POST http://localhost:8000/api/social/friends/request/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"receiver_id": "uuid"}'

# POST request (with files)
curl -X POST http://localhost:8000/api/social/posts/create/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "content=Hello" \
  -F "privacy=public" \
  -F "media_files=@image.jpg"

# DELETE request
curl -X DELETE http://localhost:8000/api/social/posts/{id}/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Using Postman
1. Set Method (GET, POST, etc.)
2. Enter URL
3. Add Header: `Authorization: Bearer YOUR_TOKEN`
4. For JSON: Set Body > raw > JSON
5. For files: Set Body > form-data

### Using Python requests
```python
import requests

token = "YOUR_TOKEN"
headers = {"Authorization": f"Bearer {token}"}

# GET
response = requests.get(
    "http://localhost:8000/api/social/posts/",
    headers=headers
)

# POST (JSON)
response = requests.post(
    "http://localhost:8000/api/social/friends/request/",
    headers=headers,
    json={"receiver_id": "uuid"}
)

# POST (files)
files = {"media_files": open("image.jpg", "rb")}
data = {"content": "Hello", "privacy": "public"}
response = requests.post(
    "http://localhost:8000/api/social/posts/create/",
    headers=headers,
    data=data,
    files=files
)
```

---

## Notes

1. All UUID fields use UUIDv4 format
2. All timestamps are in ISO 8601 format (UTC)
3. File uploads have size limits (configure in settings)
4. Supported image formats: jpg, jpeg, png, gif
5. Supported video formats: mp4, mov, avi
6. Stories automatically expire after 24 hours
7. Deleted objects cascade to related objects
8. Media files are automatically cleaned up when objects are deleted
