from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend

from .models import Category, Product, ProductImage, Cart, CartItem, Order, OrderItem
from .serializers import (
    CategorySerializer, ProductListSerializer, ProductDetailSerializer,
    ProductApprovalSerializer, CartSerializer, CartItemSerializer,
    OrderSerializer, CheckoutSerializer, BuyNowSerializer, ProductImageSerializer
)
from .permissions import (
    IsAdminOrReadOnly, IsProductOwner, CanApproveProduct,
    IsCartOwner, IsOrderOwnerOrAdmin
)


class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing product categories.
    Admin can create, update, delete categories.
    All users can view categories.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing products.
    Users can create products (goes to pending state).
    Admin can approve/reject products.
    Only approved products are visible to regular users.
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'status']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'price', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        
        if user.is_staff:
            # Admin can see all products
            return Product.objects.all().select_related('category', 'seller').prefetch_related('images')
        else:
            # Regular users see approved products and their own products
            return Product.objects.filter(
                Q(status='approved') | Q(seller=user)
            ).select_related('category', 'seller').prefetch_related('images')

    def get_serializer_class(self):
        if self.action in ['list']:
            return ProductListSerializer
        return ProductDetailSerializer

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsProductOwner()]
        elif self.action in ['approve', 'reject']:
            return [IsAuthenticated(), CanApproveProduct()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        """Admin endpoint to approve a product"""
        product = self.get_object()
        serializer = ProductApprovalSerializer(
            product,
            data={'status': 'approved'},
            context={'request': request},
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'message': 'Product approved successfully',
            'product': ProductDetailSerializer(product, context={'request': request}).data
        })

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        """Admin endpoint to reject a product"""
        product = self.get_object()
        rejection_reason = request.data.get('rejection_reason')
        
        if not rejection_reason:
            return Response(
                {'error': 'rejection_reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ProductApprovalSerializer(
            product,
            data={'status': 'rejected', 'rejection_reason': rejection_reason},
            context={'request': request},
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'message': 'Product rejected successfully',
            'product': ProductDetailSerializer(product, context={'request': request}).data
        })

    @action(detail=False, methods=['get'], url_path='pending')
    def pending(self, request):
        """Admin endpoint to list all pending products"""
        if not request.user.is_staff:
            return Response(
                {'error': 'You do not have permission to perform this action.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        pending_products = Product.objects.filter(status='pending').select_related('category', 'seller')
        serializer = ProductListSerializer(pending_products, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='my-products')
    def my_products(self, request):
        """Endpoint to list current user's products"""
        my_products = Product.objects.filter(seller=request.user).select_related('category').prefetch_related('images')
        serializer = ProductListSerializer(my_products, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='add-image')
    def add_image(self, request, pk=None):
        """Add an image to a product"""
        product = self.get_object()
        
        # Check if user is the owner
        if product.seller != request.user and not request.user.is_staff:
            return Response(
                {'error': 'You do not have permission to add images to this product.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        image = request.FILES.get('image')
        is_primary = request.data.get('is_primary', False)
        
        if not image:
            return Response(
                {'error': 'No image provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        product_image = ProductImage.objects.create(
            product=product,
            image=image,
            is_primary=is_primary
        )
        
        serializer = ProductImageSerializer(product_image, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='delete-image/(?P<image_id>[^/.]+)')
    def delete_image(self, request, pk=None, image_id=None):
        """Delete a product image"""
        product = self.get_object()
        
        # Check if user is the owner
        if product.seller != request.user and not request.user.is_staff:
            return Response(
                {'error': 'You do not have permission to delete images from this product.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            image = ProductImage.objects.get(id=image_id, product=product)
            image.delete()
            return Response({'message': 'Image deleted successfully'})
        except ProductImage.DoesNotExist:
            return Response(
                {'error': 'Image not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class CartViewSet(viewsets.ViewSet):
    """
    ViewSet for managing shopping cart.
    Users can view their cart, add items, update quantities, and remove items.
    """
    permission_classes = [IsAuthenticated]

    def get_or_create_cart(self, user):
        """Get or create cart for user"""
        cart, created = Cart.objects.get_or_create(user=user)
        return cart

    def list(self, request):
        """Get user's cart"""
        cart = self.get_or_create_cart(request.user)
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='add-item')
    def add_item(self, request):
        """Add item to cart"""
        cart = self.get_or_create_cart(request.user)
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)

        if not product_id:
            return Response(
                {'error': 'product_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if product is approved
        if product.status != 'approved':
            return Response(
                {'error': 'This product is not available for purchase'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if item already exists in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            # Update quantity if item already exists
            cart_item.quantity += quantity
            cart_item.save()

        serializer = CartItemSerializer(cart_item, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['patch'], url_path='update-item/(?P<item_id>[^/.]+)')
    def update_item(self, request, item_id=None):
        """Update cart item quantity"""
        cart = self.get_or_create_cart(request.user)
        
        try:
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
        except CartItem.DoesNotExist:
            return Response(
                {'error': 'Cart item not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        quantity = request.data.get('quantity')
        if quantity is None:
            return Response(
                {'error': 'quantity is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            quantity = int(quantity)
            if quantity < 1:
                return Response(
                    {'error': 'Quantity must be at least 1'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid quantity'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check stock
        if quantity > cart_item.product.stock:
            return Response(
                {'error': f'Only {cart_item.product.stock} items available in stock'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart_item.quantity = quantity
        cart_item.save()

        serializer = CartItemSerializer(cart_item, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['delete'], url_path='remove-item/(?P<item_id>[^/.]+)')
    def remove_item(self, request, item_id=None):
        """Remove item from cart"""
        cart = self.get_or_create_cart(request.user)
        
        try:
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
            cart_item.delete()
            return Response({'message': 'Item removed from cart'})
        except CartItem.DoesNotExist:
            return Response(
                {'error': 'Cart item not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['delete'], url_path='clear')
    def clear_cart(self, request):
        """Clear all items from cart"""
        cart = self.get_or_create_cart(request.user)
        cart.items.all().delete()
        return Response({'message': 'Cart cleared successfully'})


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing orders.
    Users can view their own orders.
    Admin can view all orders and update order status.
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, IsOrderOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status']
    ordering_fields = ['created_at', 'total_amount']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Order.objects.all().select_related('user').prefetch_related('items')
        return Order.objects.filter(user=user).select_related('user').prefetch_related('items')

    @action(detail=True, methods=['patch'], url_path='update-status')
    def update_status(self, request, pk=None):
        """Admin endpoint to update order status"""
        if not request.user.is_staff:
            return Response(
                {'error': 'You do not have permission to perform this action.'},
                status=status.HTTP_403_FORBIDDEN
            )

        order = self.get_object()
        new_status = request.data.get('status')

        if not new_status:
            return Response(
                {'error': 'status is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_status not in dict(Order.STATUS_CHOICES):
            return Response(
                {'error': 'Invalid status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = new_status
        order.save()

        serializer = OrderSerializer(order, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='checkout')
    def checkout(self, request):
        """
        Checkout with selected cart items.
        Creates an order from cart items.
        """
        serializer = CheckoutSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            return Response(
                {'error': 'Cart is empty'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart_item_ids = serializer.validated_data.get('cart_item_ids')
        
        if cart_item_ids:
            cart_items = CartItem.objects.filter(id__in=cart_item_ids, cart=cart).select_related('product')
        else:
            cart_items = cart.items.all().select_related('product')

        if not cart_items:
            return Response(
                {'error': 'No items to checkout'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify stock availability
        for item in cart_items:
            if item.quantity > item.product.stock:
                return Response(
                    {'error': f'Insufficient stock for {item.product.name}. Only {item.product.stock} available.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Create order
        with transaction.atomic():
            total_amount = sum(item.subtotal for item in cart_items)
            
            order = Order.objects.create(
                user=request.user,
                total_amount=total_amount,
                shipping_address=serializer.validated_data['shipping_address'],
                shipping_city=serializer.validated_data['shipping_city'],
                shipping_postal_code=serializer.validated_data['shipping_postal_code'],
                shipping_country=serializer.validated_data['shipping_country'],
                shipping_phone=serializer.validated_data['shipping_phone'],
                notes=serializer.validated_data.get('notes', '')
            )

            # Create order items and update stock
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    product_name=item.product.name,
                    product_price=item.product.price,
                    quantity=item.quantity
                )
                
                # Reduce stock
                item.product.stock -= item.quantity
                item.product.save()

            # Remove checked out items from cart
            cart_items.delete()

        order_serializer = OrderSerializer(order, context={'request': request})
        return Response(order_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='buy-now')
    def buy_now(self, request):
        """
        Buy a single product directly without adding to cart.
        Creates an order with a single item.
        """
        serializer = BuyNowSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        product = Product.objects.get(id=serializer.validated_data['product_id'])
        quantity = serializer.validated_data['quantity']

        # Verify stock
        if quantity > product.stock:
            return Response(
                {'error': f'Insufficient stock. Only {product.stock} available.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create order
        with transaction.atomic():
            total_amount = product.price * quantity
            
            order = Order.objects.create(
                user=request.user,
                total_amount=total_amount,
                shipping_address=serializer.validated_data['shipping_address'],
                shipping_city=serializer.validated_data['shipping_city'],
                shipping_postal_code=serializer.validated_data['shipping_postal_code'],
                shipping_country=serializer.validated_data['shipping_country'],
                shipping_phone=serializer.validated_data['shipping_phone'],
                notes=serializer.validated_data.get('notes', '')
            )

            # Create order item
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                product_price=product.price,
                quantity=quantity
            )
            
            # Reduce stock
            product.stock -= quantity
            product.save()

        order_serializer = OrderSerializer(order, context={'request': request})
        return Response(order_serializer.data, status=status.HTTP_201_CREATED)


