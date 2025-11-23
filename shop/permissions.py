from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admin users to edit objects.
    Read-only permissions are allowed for any request.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or admin to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Admin can do anything
        if request.user and request.user.is_staff:
            return True
        
        # Check if object has seller attribute (Product)
        if hasattr(obj, 'seller'):
            return obj.seller == request.user
        
        # Check if object has user attribute (Cart, Order)
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False


class IsProductOwner(permissions.BasePermission):
    """
    Custom permission to only allow product owners to edit their products.
    Admin can also edit products for approval/rejection.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # Admin can do anything
        if request.user and request.user.is_staff:
            return True
        
        # Product owner can edit their own products
        if hasattr(obj, 'seller'):
            return obj.seller == request.user
        
        return False


class CanApproveProduct(permissions.BasePermission):
    """
    Permission to approve/reject products - only admin users.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_staff

    def has_object_permission(self, request, view, obj):
        return request.user and request.user.is_staff


class IsCartOwner(permissions.BasePermission):
    """
    Custom permission to only allow cart owners to manage their cart.
    """
    def has_object_permission(self, request, view, obj):
        # Cart belongs to the user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # CartItem belongs to user's cart
        if hasattr(obj, 'cart'):
            return obj.cart.user == request.user
        
        return False


class IsOrderOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow order owners to view their orders.
    Admin can view and edit all orders.
    """
    def has_object_permission(self, request, view, obj):
        # Admin can do anything
        if request.user and request.user.is_staff:
            return True
        
        # Order owner can view their orders
        if hasattr(obj, 'user'):
            if request.method in permissions.SAFE_METHODS:
                return obj.user == request.user
            # Only admin can edit orders
            return False
        
        return False
