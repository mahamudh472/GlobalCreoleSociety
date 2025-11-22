# Shop API Documentation

## Overview
The Shop API provides endpoints for managing an e-commerce platform with product listings, shopping cart, and order management. Products go through an approval workflow where admin users can approve or reject submissions.

## Base URL
```
/api/shop/
```

## Authentication
All endpoints require authentication using JWT tokens. Include the token in the Authorization header:
```
Authorization: Bearer <your_access_token>
```

---

## Categories

### List Categories
Get all product categories.

**Endpoint:** `GET /api/shop/categories/`

**Response:**
```json
[
    {
        "id": 1,
        "name": "Electronics",
        "description": "Electronic devices and accessories",
        "product_count": 15,
        "created_at": "2025-11-20T10:00:00Z",
        "updated_at": "2025-11-20T10:00:00Z"
    }
]
```

### Create Category (Admin Only)
Create a new product category.

**Endpoint:** `POST /api/shop/categories/`

**Request:**
```json
{
    "name": "Electronics",
    "description": "Electronic devices and accessories"
}
```

**Response:** `201 Created`
```json
{
    "id": 1,
    "name": "Electronics",
    "description": "Electronic devices and accessories",
    "product_count": 0,
    "created_at": "2025-11-20T10:00:00Z",
    "updated_at": "2025-11-20T10:00:00Z"
}
```

### Get Category Details
Get details of a specific category.

**Endpoint:** `GET /api/shop/categories/{id}/`

**Response:** `200 OK` (Same as Create response)

### Update Category (Admin Only)
Update a category.

**Endpoint:** `PUT/PATCH /api/shop/categories/{id}/`

**Request:**
```json
{
    "name": "Consumer Electronics",
    "description": "Updated description"
}
```

**Response:** `200 OK` (Returns updated category)

### Delete Category (Admin Only)
Delete a category.

**Endpoint:** `DELETE /api/shop/categories/{id}/`

**Response:** `204 No Content`

---

## Products

### List Products
List all approved products (regular users) or all products (admin).

**Endpoint:** `GET /api/shop/products/`

**Query Parameters:**
- `category` - Filter by category ID
- `status` - Filter by status (pending/approved/rejected) - Admin only
- `search` - Search in product name and description
- `ordering` - Order by fields (created_at, price, name)

**Response:**
```json
[
    {
        "id": 1,
        "name": "Smartphone X",
        "description": "Latest smartphone with amazing features",
        "category": 1,
        "category_name": "Electronics",
        "price": "599.99",
        "stock": 50,
        "status": "approved",
        "seller": 2,
        "seller_name": "john_doe",
        "primary_image": {
            "id": 1,
            "image": "/media/product_images/2025/11/phone.jpg",
            "image_url": "http://localhost:8000/media/product_images/2025/11/phone.jpg",
            "is_primary": true,
            "created_at": "2025-11-20T10:00:00Z"
        },
        "created_at": "2025-11-20T10:00:00Z"
    }
]
```

### Create Product
Create a new product (goes to pending state).

**Endpoint:** `POST /api/shop/products/`

**Request:** (multipart/form-data)
```
name: Smartphone X
description: Latest smartphone with amazing features
category: 1
price: 599.99
stock: 50
uploaded_images: [image1.jpg, image2.jpg]
```

**Response:** `201 Created`
```json
{
    "id": 1,
    "name": "Smartphone X",
    "description": "Latest smartphone with amazing features",
    "category": 1,
    "category_name": "Electronics",
    "price": "599.99",
    "stock": 50,
    "status": "pending",
    "seller": 2,
    "seller_name": "john_doe",
    "images": [
        {
            "id": 1,
            "image": "/media/product_images/2025/11/phone1.jpg",
            "image_url": "http://localhost:8000/media/product_images/2025/11/phone1.jpg",
            "is_primary": true,
            "created_at": "2025-11-20T10:00:00Z"
        },
        {
            "id": 2,
            "image": "/media/product_images/2025/11/phone2.jpg",
            "image_url": "http://localhost:8000/media/product_images/2025/11/phone2.jpg",
            "is_primary": false,
            "created_at": "2025-11-20T10:00:00Z"
        }
    ],
    "rejection_reason": null,
    "created_at": "2025-11-20T10:00:00Z",
    "updated_at": "2025-11-20T10:00:00Z",
    "approved_at": null,
    "approved_by": null
}
```

### Get Product Details
Get detailed information about a product.

**Endpoint:** `GET /api/shop/products/{id}/`

**Response:** `200 OK` (Same as Create response)

### Update Product
Update a product (only owner can update, only if status is pending).

**Endpoint:** `PUT/PATCH /api/shop/products/{id}/`

**Request:** (multipart/form-data)
```
name: Updated Smartphone X
price: 549.99
stock: 60
uploaded_images: [new_image.jpg]  # Optional, adds new images
```

**Response:** `200 OK` (Returns updated product)

### Delete Product
Delete a product (only owner or admin).

**Endpoint:** `DELETE /api/shop/products/{id}/`

**Response:** `204 No Content`

### Get My Products
List all products created by the current user.

**Endpoint:** `GET /api/shop/products/my-products/`

**Response:** `200 OK` (Array of products)

### Get Pending Products (Admin Only)
List all products pending approval.

**Endpoint:** `GET /api/shop/products/pending/`

**Response:** `200 OK` (Array of pending products)

### Approve Product (Admin Only)
Approve a pending product.

**Endpoint:** `POST /api/shop/products/{id}/approve/`

**Response:** `200 OK`
```json
{
    "message": "Product approved successfully",
    "product": {
        "id": 1,
        "name": "Smartphone X",
        "status": "approved",
        "approved_at": "2025-11-20T12:00:00Z",
        "approved_by": 1,
        ...
    }
}
```

### Reject Product (Admin Only)
Reject a pending product.

**Endpoint:** `POST /api/shop/products/{id}/reject/`

**Request:**
```json
{
    "rejection_reason": "Product images are not clear enough"
}
```

**Response:** `200 OK`
```json
{
    "message": "Product rejected successfully",
    "product": {
        "id": 1,
        "name": "Smartphone X",
        "status": "rejected",
        "rejection_reason": "Product images are not clear enough",
        ...
    }
}
```

### Add Product Image
Add an additional image to a product.

**Endpoint:** `POST /api/shop/products/{id}/add-image/`

**Request:** (multipart/form-data)
```
image: image.jpg
is_primary: false
```

**Response:** `201 Created`
```json
{
    "id": 3,
    "image": "/media/product_images/2025/11/image.jpg",
    "image_url": "http://localhost:8000/media/product_images/2025/11/image.jpg",
    "is_primary": false,
    "created_at": "2025-11-20T13:00:00Z"
}
```

### Delete Product Image
Delete a product image.

**Endpoint:** `DELETE /api/shop/products/{product_id}/delete-image/{image_id}/`

**Response:** `200 OK`
```json
{
    "message": "Image deleted successfully"
}
```

---

## Shopping Cart

### Get Cart
View the current user's shopping cart.

**Endpoint:** `GET /api/shop/cart/`

**Response:**
```json
{
    "id": 1,
    "user": 2,
    "items": [
        {
            "id": 1,
            "product": 1,
            "product_name": "Smartphone X",
            "product_price": "599.99",
            "product_image": {
                "id": 1,
                "image": "/media/product_images/2025/11/phone.jpg",
                "image_url": "http://localhost:8000/media/product_images/2025/11/phone.jpg",
                "is_primary": true,
                "created_at": "2025-11-20T10:00:00Z"
            },
            "quantity": 2,
            "subtotal": "1199.98",
            "available_stock": 50,
            "added_at": "2025-11-20T14:00:00Z",
            "updated_at": "2025-11-20T14:30:00Z"
        }
    ],
    "total_items": 2,
    "total_price": "1199.98",
    "created_at": "2025-11-20T14:00:00Z",
    "updated_at": "2025-11-20T14:30:00Z"
}
```

### Add Item to Cart
Add a product to the shopping cart.

**Endpoint:** `POST /api/shop/cart/add-item/`

**Request:**
```json
{
    "product_id": 1,
    "quantity": 2
}
```

**Response:** `201 Created`
```json
{
    "id": 1,
    "product": 1,
    "product_name": "Smartphone X",
    "product_price": "599.99",
    "product_image": {...},
    "quantity": 2,
    "subtotal": "1199.98",
    "available_stock": 50,
    "added_at": "2025-11-20T14:00:00Z",
    "updated_at": "2025-11-20T14:00:00Z"
}
```

**Note:** If the item already exists in the cart, the quantity will be incremented.

### Update Cart Item
Update the quantity of a cart item.

**Endpoint:** `PATCH /api/shop/cart/update-item/{item_id}/`

**Request:**
```json
{
    "quantity": 3
}
```

**Response:** `200 OK` (Returns updated cart item)

### Remove Cart Item
Remove an item from the cart.

**Endpoint:** `DELETE /api/shop/cart/remove-item/{item_id}/`

**Response:** `200 OK`
```json
{
    "message": "Item removed from cart"
}
```

### Clear Cart
Remove all items from the cart.

**Endpoint:** `DELETE /api/shop/cart/clear/`

**Response:** `200 OK`
```json
{
    "message": "Cart cleared successfully"
}
```

---

## Orders

### List Orders
List all orders for the current user (or all orders for admin).

**Endpoint:** `GET /api/shop/orders/`

**Query Parameters:**
- `status` - Filter by status (pending/processing/shipped/delivered/cancelled)
- `ordering` - Order by fields (created_at, total_amount)

**Response:**
```json
[
    {
        "id": 1,
        "user": 2,
        "user_name": "john_doe",
        "total_amount": "1199.98",
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
                "quantity": 2,
                "subtotal": "1199.98"
            }
        ],
        "notes": "",
        "created_at": "2025-11-20T15:00:00Z",
        "updated_at": "2025-11-20T15:00:00Z"
    }
]
```

### Get Order Details
Get detailed information about a specific order.

**Endpoint:** `GET /api/shop/orders/{id}/`

**Response:** `200 OK` (Same format as list item)

### Checkout from Cart
Create an order from cart items.

**Endpoint:** `POST /api/shop/orders/checkout/`

**Request:**
```json
{
    "cart_item_ids": [1, 2],  // Optional, if not provided, all cart items will be used
    "shipping_address": "123 Main St, Apt 4B",
    "shipping_city": "New York",
    "shipping_postal_code": "10001",
    "shipping_country": "USA",
    "shipping_phone": "+1234567890",
    "notes": "Please deliver between 9 AM - 5 PM"  // Optional
}
```

**Response:** `201 Created`
```json
{
    "id": 1,
    "user": 2,
    "user_name": "john_doe",
    "total_amount": "1199.98",
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
            "quantity": 2,
            "subtotal": "1199.98"
        }
    ],
    "notes": "Please deliver between 9 AM - 5 PM",
    "created_at": "2025-11-20T15:00:00Z",
    "updated_at": "2025-11-20T15:00:00Z"
}
```

**Notes:**
- Selected cart items will be removed from the cart after successful checkout
- Product stock will be automatically reduced
- If stock is insufficient, the request will fail with an error

### Buy Now (Single Item Checkout)
Create an order for a single product without adding to cart.

**Endpoint:** `POST /api/shop/orders/buy-now/`

**Request:**
```json
{
    "product_id": 1,
    "quantity": 2,
    "shipping_address": "123 Main St, Apt 4B",
    "shipping_city": "New York",
    "shipping_postal_code": "10001",
    "shipping_country": "USA",
    "shipping_phone": "+1234567890",
    "notes": "Please deliver between 9 AM - 5 PM"  // Optional
}
```

**Response:** `201 Created` (Same format as checkout response)

### Update Order Status (Admin Only)
Update the status of an order.

**Endpoint:** `PATCH /api/shop/orders/{id}/update-status/`

**Request:**
```json
{
    "status": "processing"  // or "shipped", "delivered", "cancelled"
}
```

**Response:** `200 OK` (Returns updated order)

**Valid Status Values:**
- `pending` - Order placed, awaiting processing
- `processing` - Order is being prepared
- `shipped` - Order has been shipped
- `delivered` - Order has been delivered
- `cancelled` - Order has been cancelled

---

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
    "error": "Invalid request",
    "details": {
        "field_name": ["Error message"]
    }
}
```

### 401 Unauthorized
```json
{
    "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
    "error": "You do not have permission to perform this action."
}
```

### 404 Not Found
```json
{
    "error": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
    "error": "An unexpected error occurred"
}
```

---

## Workflow Examples

### Example 1: User Creates and Sells a Product

1. **Create a product** (goes to pending state):
   ```
   POST /api/shop/products/
   ```

2. **Admin reviews pending products**:
   ```
   GET /api/shop/products/pending/
   ```

3. **Admin approves the product**:
   ```
   POST /api/shop/products/{id}/approve/
   ```

4. **Product is now visible to all users** in the product list:
   ```
   GET /api/shop/products/
   ```

### Example 2: User Purchases Products

1. **Browse products**:
   ```
   GET /api/shop/products/
   ```

2. **Add product to cart**:
   ```
   POST /api/shop/cart/add-item/
   {
       "product_id": 1,
       "quantity": 2
   }
   ```

3. **View cart**:
   ```
   GET /api/shop/cart/
   ```

4. **Update quantity if needed**:
   ```
   PATCH /api/shop/cart/update-item/{item_id}/
   {
       "quantity": 3
   }
   ```

5. **Checkout**:
   ```
   POST /api/shop/orders/checkout/
   {
       "shipping_address": "123 Main St",
       "shipping_city": "New York",
       "shipping_postal_code": "10001",
       "shipping_country": "USA",
       "shipping_phone": "+1234567890"
   }
   ```

6. **View order**:
   ```
   GET /api/shop/orders/{id}/
   ```

### Example 3: Quick Purchase (Buy Now)

1. **Browse products**:
   ```
   GET /api/shop/products/
   ```

2. **Buy immediately without cart**:
   ```
   POST /api/shop/orders/buy-now/
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

---

## Notes

- All timestamps are in ISO 8601 format (UTC)
- Prices are stored as decimal values with 2 decimal places
- Product images are uploaded to `/media/product_images/YYYY/MM/`
- The first uploaded image is automatically set as the primary image
- Users can only edit their own products if the product status is "pending"
- Admin users can approve/reject products and manage all orders
- Stock is automatically reduced when an order is created
- Cart items are removed after successful checkout
