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
| GET | `/accounts/profile/{id}/` | Get other user's profile | Yes |
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
| GET | `/social/friends/suggestions/` | Get friend suggestions | Yes |
| DELETE | `/social/friends/{user_id}/unfriend/` | Remove a friend (user_id=UUID) | Yes |

**Request Body Examples:**

Register:
```json
{
  "email": "user@example.com",
  "profile_name": "John Doe",
  "password": "securePassword123",
  "phone_number": "+1234567890",
  "gender": "male",
  "date_of_birth": "1990-01-15",
  "share_data": false
}
```

Login:
```json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

Login/Register Response:
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "profile_name": "John Doe",
    "description": "",
    "profile_image": "http://localhost:8000/media/profile_images/image.jpg",
    "website": "",
    "phone_number": "+1234567890",
    "gender": "male",
    "date_of_birth": "1990-01-15",
    "profile_lock": false,
    "date_joined": "2025-11-23T10:30:00Z",
    "locations": [],
    "works": [],
    "educations": []
  },
  "tokens": {
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  },
  "message": "Login successful"
}
```

Update Profile (PUT/PATCH):
```json
{
  "profile_name": "Updated Name",
  "description": "My bio here",
  "website": "https://example.com",
  "gender": "female"
}
```

Change Password:
```json
{
  "old_password": "currentPassword",
  "new_password": "newSecurePassword"
}
```

Response:
```json
{
  "message": "Password updated successfully"
}
```

Change Email:
```json
{
  "new_email": "newemail@example.com",
  "password": "currentPassword",
  "code": "123456"
}
```

Add Email:
```json
{
  "email": "extra@example.com",
  "password": "currentPassword",
  "code": "123456"
}
```

---

## Friend Management

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/social/friends/request/` | Send friend request | Yes |
| GET | `/social/friends/requests/` | List pending requests received | Yes |
| POST | `/social/friends/requests/{user_id}/response/` | Accept/reject friend request (user_id=UUID) | Yes |
| GET | `/social/friends/` | List all friends | Yes |
| GET | `/social/friends/suggestions/` | Get friend suggestions | Yes |
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

Friend Request Response:
```json
{
  "id": "uuid",
  "requester": {
    "id": "uuid",
    "email": "user@example.com",
    "profile_name": "John Doe",
    "profile_image": "http://localhost:8000/media/profile_images/image.jpg"
  },
  "receiver": {
    "id": "uuid",
    "email": "friend@example.com",
    "profile_name": "Jane Smith",
    "profile_image": "http://localhost:8000/media/profile_images/image2.jpg"
  },
  "status": "pending",
  "created_at": "2025-11-23T10:30:00Z",
  "updated_at": "2025-11-23T10:30:00Z"
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
society: "uuid"  // optional - must be a member to post
media_files[]: file1.jpg
media_files[]: file2.jpg
media_captions[]: "Caption for first image"
media_captions[]: "Caption for second image"
```

Post Response:
```json
{
  "id": "uuid",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "profile_name": "John Doe",
    "profile_image": "http://localhost:8000/media/profile_images/image.jpg"
  },
  "content": "Post content here",
  "privacy": "public",
  "society": {
    "id": "uuid",
    "name": "Society Name",
    "cover_image": "http://localhost:8000/media/societies/cover.jpg",
    "cover_picture": "http://localhost:8000/media/societies/cover.jpg",
    "members_count": 50
  },
  "media": [
    {
      "id": "uuid",
      "media_type": "image",
      "file": "http://localhost:8000/media/post_media/file1.jpg",
      "caption": "Caption for first image",
      "created_at": "2025-11-23T10:30:00Z"
    }
  ],
  "like_count": 10,
  "comment_count": 5,
  "is_liked": false,
  "created_at": "2025-11-23T10:30:00Z",
  "updated_at": "2025-11-23T10:30:00Z"
}
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

Comment Response:
```json
{
  "id": "uuid",
  "user": {
    "id": "uuid",
    "email": "commenter@example.com",
    "profile_name": "Jane Smith",
    "profile_image": "http://localhost:8000/media/profile_images/image2.jpg"
  },
  "post": "post-uuid",
  "content": "Great post!",
  "like_count": 2,
  "is_liked": false,
  "created_at": "2025-11-23T10:35:00Z",
  "updated_at": "2025-11-23T10:35:00Z"
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

Society Response:
```json
{
  "id": "uuid",
  "name": "Society Name",
  "description": "Description here",
  "cover_image": "http://localhost:8000/media/societies/cover.jpg",
  "cover_picture": "http://localhost:8000/media/societies/cover.jpg",
  "privacy": "public",
  "creator": {
    "id": "uuid",
    "email": "creator@example.com",
    "profile_name": "John Doe",
    "profile_image": "http://localhost:8000/media/profile_images/image.jpg"
  },
  "member_count": 50,
  "members_count": 50,
  "user_membership": {
    "status": "accepted",
    "role": "admin"
  },
  "is_member": true,
  "created_at": "2025-11-23T10:30:00Z",
  "updated_at": "2025-11-23T10:30:00Z"
}
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

Story Response:
```json
{
  "id": "uuid",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "profile_name": "John Doe",
    "profile_image": "http://localhost:8000/media/profile_images/image.jpg"
  },
  "content": "Story text",
  "privacy": "public",
  "media": [
    {
      "id": "uuid",
      "media_type": "image",
      "file": "http://localhost:8000/media/story_media/file1.jpg",
      "created_at": "2025-11-23T10:30:00Z"
    }
  ],
  "view_count": 25,
  "is_viewed": false,
  "is_active": true,
  "created_at": "2025-11-23T10:30:00Z",
  "expires_at": "2025-11-24T10:30:00Z"
}
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

Notification Response:
```json
{
  "id": "uuid",
  "sender": {
    "id": "uuid",
    "email": "friend@example.com",
    "profile_name": "Jane Smith",
    "profile_image": "http://localhost:8000/media/profile_images/image2.jpg"
  },
  "notification_type": "like",
  "message": "Jane Smith liked your post",
  "post": "post-uuid",
  "post_content": "Original post content...",
  "comment": null,
  "society": null,
  "society_name": null,
  "is_read": false,
  "created_at": "2025-11-23T10:30:00Z"
}
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
| PUT | `/chat/conversations/{id}/` | Update a conversation | Yes |
| PATCH | `/chat/conversations/{id}/` | Partially update a conversation | Yes |
| DELETE | `/chat/conversations/{id}/` | Delete a conversation | Yes |
| GET | `/chat/conversations/{id}/messages/` | Get messages in conversation (paginated) | Yes |
| POST | `/chat/conversations/{id}/send_message/` | Send message in conversation | Yes |
| POST | `/chat/conversations/{id}/mark_as_read/` | Mark conversation messages as read | Yes |
| GET | `/chat/conversations/unread_count/` | Get total unread message count | Yes |
| GET | `/chat/conversations/search_friends/` | Search friends to start conversations | Yes |
| GET | `/chat/messages/` | List user's messages | Yes |
| GET | `/chat/messages/{id}/` | Get specific message | Yes |
| PUT | `/chat/messages/{id}/` | Update a message | Yes |
| PATCH | `/chat/messages/{id}/` | Partially update a message | Yes |
| DELETE | `/chat/messages/{id}/` | Delete a message | Yes |
| POST | `/chat/messages/{id}/mark_read/` | Mark a message as read | Yes |
| GET | `/chat/global-chat/` | List global chat messages (paginated) | Yes |
| GET | `/chat/global-chat/{id}/` | Get specific global chat message | Yes |
| POST | `/chat/global-chat/send_message/` | Send global chat message | Yes |

**Request Body Examples:**

Create/Get Conversation:
```json
{
  "user_id": "uuid"
}
```

Conversation List Response:
```json
[
  {
    "id": "uuid",
    "other_participant": {
      "id": "uuid",
      "email": "friend@example.com",
      "profile_name": "Jane Smith",
      "description": "",
      "profile_image": "http://localhost:8000/media/profile_images/image2.jpg",
      "website": "",
      "phone_number": "",
      "gender": "",
      "date_of_birth": null,
      "profile_lock": false,
      "date_joined": "2025-11-20T10:00:00Z",
      "locations": [],
      "works": [],
      "educations": []
    },
    "last_message": {
      "id": "uuid",
      "conversation": "conversation-uuid",
      "sender": {
        "id": "uuid",
        "email": "friend@example.com",
        "profile_name": "Jane Smith",
        "description": "",
        "profile_image": "http://localhost:8000/media/profile_images/image2.jpg",
        "website": "",
        "phone_number": "",
        "gender": "",
        "date_of_birth": null,
        "profile_lock": false,
        "date_joined": "2025-11-20T10:00:00Z",
        "locations": [],
        "works": [],
        "educations": []
      },
      "content": "Hello there!",
      "file": null,
      "file_url": null,
      "file_type": "",
      "is_read": false,
      "read_at": null,
      "created_at": "2025-11-23T10:30:00Z",
      "updated_at": "2025-11-23T10:30:00Z"
    },
    "unread_count": 3,
    "updated_at": "2025-11-23T10:30:00Z"
  }
]
```

Send Message in Conversation (multipart/form-data):
```
content: "Hello there!"
file: image.jpg  // optional
file_type: "image"  // optional: "image", "video", "document"
```

Message Response:
```json
{
  "id": "uuid",
  "conversation": "conversation-uuid",
  "sender": {
    "id": "uuid",
    "email": "user@example.com",
    "profile_name": "John Doe",
    "description": "",
    "profile_image": "http://localhost:8000/media/profile_images/image.jpg",
    "website": "",
    "phone_number": "",
    "gender": "",
    "date_of_birth": null,
    "profile_lock": false,
    "date_joined": "2025-11-22T10:00:00Z",
    "locations": [],
    "works": [],
    "educations": []
  },
  "content": "Hello there!",
  "file": "http://localhost:8000/media/chat_files/image.jpg",
  "file_url": "http://localhost:8000/media/chat_files/image.jpg",
  "file_type": "image",
  "is_read": false,
  "read_at": null,
  "created_at": "2025-11-23T10:35:00Z",
  "updated_at": "2025-11-23T10:35:00Z"
}
```

Send Global Chat Message (multipart/form-data):
```
content: "Hello everyone!"
file: image.jpg  // optional
file_type: "image"  // optional
```

Global Chat Message Response:
```json
{
  "id": "uuid",
  "sender": {
    "id": "uuid",
    "email": "user@example.com",
    "profile_name": "John Doe",
    "description": "",
    "profile_image": "http://localhost:8000/media/profile_images/image.jpg",
    "website": "",
    "phone_number": "",
    "gender": "",
    "date_of_birth": null,
    "profile_lock": false,
    "date_joined": "2025-11-22T10:00:00Z",
    "locations": [],
    "works": [],
    "educations": []
  },
  "content": "Hello everyone!",
  "file": "http://localhost:8000/media/chat_files/image.jpg",
  "file_url": "http://localhost:8000/media/chat_files/image.jpg",
  "file_type": "image",
  "created_at": "2025-11-23T10:35:00Z",
  "updated_at": "2025-11-23T10:35:00Z"
}
```

**Query Parameters:**

List Conversations:
```
?unread_only=true  // Filter to show only conversations with unread messages
```

Search Friends:
```
?q=search_query  // Search by profile name or email
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
| PUT | `/shop/categories/{id}/` | Update a category (full) | Yes | Yes |
| PATCH | `/shop/categories/{id}/` | Update a category (partial) | Yes | Yes |
| DELETE | `/shop/categories/{id}/` | Delete a category | Yes | Yes |
| GET | `/shop/products/` | List products (filtered by status) | Yes | No |
| POST | `/shop/products/` | Create a product (pending status) | Yes | No |
| GET | `/shop/products/{id}/` | Get product details | Yes | No |
| PUT | `/shop/products/{id}/` | Update a product (full) | Yes | Owner |
| PATCH | `/shop/products/{id}/` | Update a product (partial) | Yes | Owner |
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

Category Response:
```json
{
  "id": 1,
  "name": "Electronics",
  "description": "Electronic devices and accessories",
  "product_count": 15,
  "created_at": "2025-11-23T10:30:00Z",
  "updated_at": "2025-11-23T10:30:00Z"
}
```

Create Product (multipart/form-data):
```
name: "Smartphone X"
description: "Latest smartphone with 5G"
category: 1
price: 599.99
stock: 50
uploaded_images[]: image1.jpg
uploaded_images[]: image2.jpg
```

Product List Response:
```json
{
  "id": 1,
  "name": "Smartphone X",
  "description": "Latest smartphone with 5G",
  "category": 1,
  "category_name": "Electronics",
  "price": "599.99",
  "stock": 50,
  "status": "pending",
  "seller": "user-uuid",
  "seller_name": "john_doe",
  "primary_image": {
    "id": 1,
    "image": "http://localhost:8000/media/products/image1.jpg",
    "image_url": "http://localhost:8000/media/products/image1.jpg",
    "is_primary": true,
    "created_at": "2025-11-23T10:30:00Z"
  },
  "created_at": "2025-11-23T10:30:00Z"
}
```

Product Detail Response:
```json
{
  "id": 1,
  "name": "Smartphone X",
  "description": "Latest smartphone with 5G",
  "category": 1,
  "category_name": "Electronics",
  "price": "599.99",
  "stock": 50,
  "status": "approved",
  "seller": "user-uuid",
  "seller_name": "john_doe",
  "images": [
    {
      "id": 1,
      "image": "http://localhost:8000/media/products/image1.jpg",
      "image_url": "http://localhost:8000/media/products/image1.jpg",
      "is_primary": true,
      "created_at": "2025-11-23T10:30:00Z"
    },
    {
      "id": 2,
      "image": "http://localhost:8000/media/products/image2.jpg",
      "image_url": "http://localhost:8000/media/products/image2.jpg",
      "is_primary": false,
      "created_at": "2025-11-23T10:30:00Z"
    }
  ],
  "rejection_reason": null,
  "created_at": "2025-11-23T10:30:00Z",
  "updated_at": "2025-11-23T10:30:00Z",
  "approved_at": "2025-11-23T11:00:00Z",
  "approved_by": "admin-uuid"
}
```

Approve Product:
```
POST /shop/products/{id}/approve/
(No body required)
```

Reject Product:
```json
{
  "rejection_reason": "Images are not clear enough"
}
```

Add Item to Cart:
```json
{
  "product_id": 1,
  "quantity": 2
}
```

Cart Response:
```json
{
  "id": 1,
  "user": "user-uuid",
  "items": [
    {
      "id": 1,
      "product": 1,
      "product_name": "Smartphone X",
      "product_price": "599.99",
      "product_image": {
        "id": 1,
        "image": "http://localhost:8000/media/products/image1.jpg",
        "image_url": "http://localhost:8000/media/products/image1.jpg",
        "is_primary": true,
        "created_at": "2025-11-23T10:30:00Z"
      },
      "quantity": 2,
      "subtotal": "1199.98",
      "available_stock": 50,
      "added_at": "2025-11-23T10:30:00Z",
      "updated_at": "2025-11-23T10:30:00Z"
    }
  ],
  "total_items": 1,
  "total_price": "1199.98",
  "created_at": "2025-11-23T10:00:00Z",
  "updated_at": "2025-11-23T10:30:00Z"
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
  "shipping_address": "123 Main St, Apt 4B",
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
  "shipping_address": "123 Main St, Apt 4B",
  "shipping_city": "New York",
  "shipping_postal_code": "10001",
  "shipping_country": "USA",
  "shipping_phone": "+1234567890",
  "notes": "Please ring doorbell"
}
```

Order Response:
```json
{
  "id": 1,
  "user": "user-uuid",
  "user_name": "john_doe",
  "total_amount": "599.99",
  "status": "pending",
  "shipping_address": "123 Main St, Apt 4B",
  "shipping_city": "New York",
  "shipping_postal_code": "10001",
  "shipping_country": "USA",
  "shipping_phone": "+1234567890",
  "items": [
    {
      "id": 1,
      "product": 1,
      "product_name": "Smartphone X",
      "product_price": "599.99",
      "quantity": 1,
      "subtotal": "599.99"
    }
  ],
  "notes": "Please ring doorbell",
  "created_at": "2025-11-23T10:35:00Z",
  "updated_at": "2025-11-23T10:35:00Z"
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
- **Account Management**: 14 endpoints
- **Friend Management**: 6 endpoints
- **Posts**: 9 endpoints
- **Comments**: 5 endpoints
- **Societies**: 10 endpoints
- **Stories**: 4 endpoints
- **Notifications**: 2 endpoints
- **User Blocking**: 2 endpoints
- **Chat & Messaging**: 20 endpoints (+ 2 WebSocket endpoints)
- **Shop Management**: 29 endpoints

### Total: 101 REST endpoints + 2 WebSocket endpoints

### By HTTP Method
- **GET**: 44 endpoints (read operations)
- **POST**: 38 endpoints (create/action operations)
- **PUT**: 6 endpoints (full update operations)
- **PATCH**: 8 endpoints (partial update operations)
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
