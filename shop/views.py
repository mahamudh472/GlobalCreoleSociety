from rest_framework import viewsets, status, filters, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend

from .models import Category, Product, ProductImage, Cart, CartItem, Order, OrderItem, DeliveryAddress
from .serializers import (
    CategorySerializer, DeliveryAddressSerializer, ProductListSerializer, ProductDetailSerializer,
    ProductApprovalSerializer, CartSerializer, CartItemSerializer,
    OrderSerializer, CheckoutSerializer, BuyNowSerializer, ProductImageSerializer
)
from .permissions import (
    IsAdminOrReadOnly, IsProductOwner, CanApproveProduct,
    IsCartOwner, IsOrderOwnerOrAdmin
)
import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

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
        
        # Handle unauthenticated users - show only approved products
        if not user.is_authenticated:
            return Product.objects.filter(
                status='approved'
            ).select_related('category', 'seller').prefetch_related('images')
        
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
        # Allow unauthenticated access for viewing products
        if self.action in ['list', 'retrieve', 'suggested_products']:
            return [AllowAny()]
        elif self.action in ['update', 'partial_update', 'destroy']:
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

    @action(detail=True, methods=['get'], url_path='suggested')
    def suggested_products(self, request, pk=None):
        """Get suggested products based on the current product's category"""
        product = self.get_object()
        
        # Get products from the same category, excluding the current product
        suggested = Product.objects.filter(
            category=product.category,
            status='approved'
        ).exclude(
            id=product.id
        ).select_related('category', 'seller').prefetch_related('images')[:8]
        
        serializer = ProductListSerializer(suggested, many=True, context={'request': request})
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

        # Prevent users from buying their own products
        if product.seller == request.user:
            return Response(
                {'error': 'You cannot add your own product to cart'},
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
            subtotal = sum(item.subtotal for item in cart_items)
            
            # Get tax and shipping from site settings
            from accounts.models import SiteSetting
            from decimal import Decimal
            site_setting = SiteSetting.get()
            tax_amount = (Decimal(site_setting.product_tax) / 100) * subtotal
            shipping_cost = Decimal(site_setting.shipping_cost)
            total_amount = subtotal + tax_amount + shipping_cost
            
            order = Order.objects.create(
                user=request.user,
                total_amount=total_amount,
                delivery_type=serializer.validated_data.get('delivery_type', 'home'),
                payment_method=serializer.validated_data.get('payment_method', 'cash_on_delivery'),
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

        # Prevent users from buying their own products
        if product.seller == request.user:
            return Response(
                {'error': 'You cannot buy your own product'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify stock
        if quantity > product.stock:
            return Response(
                {'error': f'Insufficient stock. Only {product.stock} available.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create order
        with transaction.atomic():
            subtotal = product.price * quantity
            
            # Get tax and shipping from site settings
            from accounts.models import SiteSetting
            from decimal import Decimal
            site_setting = SiteSetting.get()
            tax_amount = (Decimal(site_setting.product_tax) / 100) * subtotal
            shipping_cost = Decimal(site_setting.shipping_cost)
            total_amount = subtotal + tax_amount + shipping_cost
            
            order = Order.objects.create(
                user=request.user,
                total_amount=total_amount,
                delivery_type=serializer.validated_data.get('delivery_type', 'home'),
                payment_method=serializer.validated_data.get('payment_method', 'cash_on_delivery'),
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

class CheckoutPreviewAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Preview the total amount for checkout without creating an order.
        """
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.items.select_related('product')
        
        # Build products list with all needed info
        products = []
        for item in cart_items:
            product = item.product
            # Get first product image
            first_image = product.images.first()
            image_url = None
            if first_image and first_image.image:
                image_url = request.build_absolute_uri(first_image.image.url)
            
            products.append({
                'id': product.id,
                'name': product.name,
                'price': str(product.price),
                'quantity': item.quantity,
                'subtotal': str(item.subtotal),
                'image': image_url,
            })

        if not DeliveryAddress.objects.filter(user=request.user).exists():
            deliver_address = None
        else:
            deliver_address = DeliveryAddressSerializer(DeliveryAddress.objects.get(user=request.user)).data

        if not cart_items:
            return Response({
                'item_count': 0,
                'delivery_address': deliver_address,
                'products': [],
                'subtotal': 0,
                'delivery_fee': 0,
                'tax_amount': 0,
                'shipping_cost': 0,
                'total_amount': 0,
            })
        
        subtotal = sum(item.subtotal for item in cart_items)

        from accounts.models import SiteSetting
        site_setting = SiteSetting.get()
        tax_amount = (site_setting.product_tax / 100) * subtotal
        shipping_cost = site_setting.shipping_cost
        total_amount = subtotal + tax_amount + shipping_cost

        return Response({
            'item_count': cart_items.count(),
            'delivery_address': deliver_address,
            'products': products,
            'subtotal': str(subtotal),
            'delivery_fee': 0,
            'tax_amount': str(tax_amount),
            'shipping_cost': str(shipping_cost),
            'total_amount': str(total_amount),
        })


class DeliveryAddressAPIView(viewsets.ViewSet):
    """
    API View for handling delivery address details.
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='add-address')
    def add_address(self, request):
        """Add delivery address details"""
        serializer = DeliveryAddressSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Here you would typically save the address to the user's profile or a related model
        # For demonstration, we'll just return the validated data
        
        return Response({
            'message': 'Delivery address added successfully',
        })
    

class StripeAccountStatusAPIView(generics.GenericAPIView):
    """Get Stripe account status and verification details."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get the Stripe account status for the authenticated user.
        Returns account details including verification status.
        """
        user = request.user

        if not user.stripe_account_id:
            return Response({
                'has_account': False,
                'is_onboarding_completed': False,
                'message': 'No Stripe account connected.'
            })

        try:
            # Retrieve account details from Stripe
            account = stripe.Account.retrieve(user.stripe_account_id)
            
            # Check if onboarding is complete
            details_submitted = account.get('details_submitted', False)
            charges_enabled = account.get('charges_enabled', False)
            payouts_enabled = account.get('payouts_enabled', False)
            
            # Update local database if status changed
            if details_submitted and not user.is_onboarding_completed:
                user.is_onboarding_completed = True
                user.save()
            
            # Get requirements if any
            requirements = account.get('requirements', {})
            currently_due = requirements.get('currently_due', [])
            eventually_due = requirements.get('eventually_due', [])
            pending_verification = requirements.get('pending_verification', [])
            
            return Response({
                'has_account': True,
                'stripe_account_id': user.stripe_account_id,
                'is_onboarding_completed': user.is_onboarding_completed,
                'details_submitted': details_submitted,
                'charges_enabled': charges_enabled,
                'payouts_enabled': payouts_enabled,
                'requirements': {
                    'currently_due': currently_due,
                    'eventually_due': eventually_due,
                    'pending_verification': pending_verification,
                },
                'needs_action': len(currently_due) > 0 or not details_submitted,
            })

        except stripe.error.InvalidRequestError:
            # Account doesn't exist on Stripe anymore, clean up
            user.stripe_account_id = None
            user.is_onboarding_completed = False
            user.save()
            return Response({
                'has_account': False,
                'is_onboarding_completed': False,
                'message': 'Stripe account was removed or invalid. Please create a new account.'
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResumeStripeOnboardingAPIView(generics.GenericAPIView):
    """Resume Stripe onboarding for incomplete accounts."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Generate a new onboarding link for an existing Stripe account.
        Use this when a user needs to complete or update their account.
        """
        user = request.user

        if not user.stripe_account_id:
            return Response(
                {'error': 'No Stripe account found. Please create an account first.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Verify account still exists on Stripe
            account = stripe.Account.retrieve(user.stripe_account_id)
            
            # Get frontend URL from request or use default
            frontend_url = request.data.get('frontend_url', 'http://localhost:5173')
            
            # Create new account link for onboarding
            account_link = stripe.AccountLink.create(
                account=user.stripe_account_id,
                refresh_url=f'{frontend_url}/marketplace/myproduct/addproduct?stripe_refresh=true',
                return_url=f'{frontend_url}/marketplace/myproduct/addproduct?stripe_onboarding=complete',
                type='account_onboarding',
            )

            return Response({
                'message': 'Onboarding link generated successfully.',
                'account_link_url': account_link.url,
                'stripe_account_id': user.stripe_account_id,
            })

        except stripe.error.InvalidRequestError:
            # Account doesn't exist on Stripe anymore, clean up
            user.stripe_account_id = None
            user.is_onboarding_completed = False
            user.save()
            return Response(
                {'error': 'Stripe account not found. Please create a new account.', 'account_deleted': True},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CreateStripeConnectedAccountAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Create a Stripe Connected Account for the authenticated user.
        If account already exists but onboarding incomplete, returns a new onboarding link.
        """
        user = request.user

        # Check if user already has a Stripe account
        if user.stripe_account_id:
            try:
                # Verify account exists on Stripe
                account = stripe.Account.retrieve(user.stripe_account_id)
                
                # If account exists and onboarding is complete, return error
                if user.is_onboarding_completed and account.get('details_submitted', False):
                    return Response(
                        {'error': 'Stripe Connected Account already exists and is fully set up.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Account exists but onboarding incomplete - generate new link
                frontend_url = request.data.get('frontend_url', 'http://localhost:5173')
                
                account_link = stripe.AccountLink.create(
                    account=user.stripe_account_id,
                    refresh_url=f'{frontend_url}/marketplace/myproduct/addproduct?stripe_refresh=true',
                    return_url=f'{frontend_url}/marketplace/myproduct/addproduct?stripe_onboarding=complete',
                    type='account_onboarding',
                )

                return Response({
                    'message': 'Resuming Stripe onboarding.',
                    'stripe_account_id': user.stripe_account_id,
                    'account_link_url': account_link.url,
                    'is_resuming': True
                }, status=status.HTTP_200_OK)
                
            except stripe.error.InvalidRequestError:
                # Account doesn't exist on Stripe, clear local reference and create new
                user.stripe_account_id = None
                user.is_onboarding_completed = False
                user.save()

        try:
            account = stripe.Account.create(
                type='express',
                email=user.email,
                capabilities={
                    'card_payments': {'requested': True},
                    'transfers': {'requested': True},
                },
            )

            # Save the Stripe account ID to the user's profile
            user.stripe_account_id = account.id
            user.save()
            
            # Get frontend URL from request or use default
            frontend_url = request.data.get('frontend_url', 'http://localhost:5173')
            
            account_link = stripe.AccountLink.create(
                account=account.id,
                refresh_url=f'{frontend_url}/marketplace/myproduct/addproduct?stripe_refresh=true',
                return_url=f'{frontend_url}/marketplace/myproduct/addproduct?stripe_onboarding=complete',
                type='account_onboarding',
            )

            return Response({
                'message': 'Stripe Connected Account created successfully.',
                'stripe_account_id': account.id,
                'account_link_url': account_link.url,
                'is_resuming': False
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class CreateCheckoutSessionAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Create a Stripe Checkout Session for the authenticated user's cart.
        Groups items by seller and creates a single session with platform fees.
        """
        user = request.user
        
        # Get cart items
        try:
            cart = Cart.objects.get(user=user)
            cart_items = cart.items.select_related('product__seller').all()
        except Cart.DoesNotExist:
            return Response(
                {'error': 'Cart is empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not cart_items.exists():
            return Response(
                {'error': 'Cart is empty'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get site settings for tax and shipping
        from accounts.models import SiteSetting
        site_setting = SiteSetting.get()
        
        # Build line items from cart
        line_items = []
        subtotal = 0
        seller_account = None
        
        for item in cart_items:
            product = item.product
            # Get seller's Stripe account
            if product.seller and product.seller.stripe_account_id:
                seller_account = product.seller.stripe_account_id
            
            item_subtotal = int(float(product.price) * item.quantity * 100)  # Convert to cents
            subtotal += item_subtotal
            
            # Get first product image if available
            image_url = None
            first_image = product.images.first()
            if first_image and first_image.image:
                image_url = request.build_absolute_uri(first_image.image.url)
            
            line_item = {
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': product.name,
                        'description': product.description[:500] if product.description else None,
                    },
                    'unit_amount': int(float(product.price) * 100),  # Convert to cents
                },
                'quantity': item.quantity,
            }
            
            # Add image if available
            if image_url:
                line_item['price_data']['product_data']['images'] = [image_url]
            
            line_items.append(line_item)
        
        # Calculate platform fee (2% of subtotal)
        platform_fee_amount = int(subtotal * 0.02)
        
        # Calculate tax and shipping in cents
        tax_amount = int((site_setting.product_tax / 100) * subtotal)
        shipping_amount = int(float(site_setting.shipping_cost) * 100)
        
        # Add tax as a line item if applicable
        if tax_amount > 0:
            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Tax',
                    },
                    'unit_amount': tax_amount,
                },
                'quantity': 1,
            })
        
        # Add shipping as a line item if applicable
        if shipping_amount > 0:
            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Shipping',
                    },
                    'unit_amount': shipping_amount,
                },
                'quantity': 1,
            })

        try:
            # Get success and cancel URLs from frontend
            frontend_url = request.data.get('frontend_url', 'http://localhost:5173')
            delivery_type = request.data.get('delivery_type', 'home')
            
            # Calculate total amount in decimal for order
            from decimal import Decimal
            subtotal_decimal = sum(item.subtotal for item in cart_items)
            tax_decimal = (Decimal(site_setting.product_tax) / 100) * subtotal_decimal
            shipping_decimal = Decimal(site_setting.shipping_cost)
            total_amount = subtotal_decimal + tax_decimal + shipping_decimal
            
            # Create order immediately with pending payment status
            with transaction.atomic():
                order = Order.objects.create(
                    user=user,
                    total_amount=total_amount,
                    status='pending',
                    delivery_type=delivery_type,
                    payment_method='card',
                    payment_status='pending',
                )
                
                # Create order items and update stock
                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        product_name=item.product.name,
                        product_price=item.product.price,
                        quantity=item.quantity,
                    )
                    
                    # Reduce stock immediately to prevent overselling
                    item.product.stock -= item.quantity
                    item.product.save()
                
                # Clear the cart
                cart.items.all().delete()
            
            session_data = {
                'payment_method_types': ['card'],
                'line_items': line_items,
                'mode': 'payment',
                'success_url': f'{frontend_url}/marketplace/order-success?session_id={{CHECKOUT_SESSION_ID}}&order_id={order.id}',
                'cancel_url': f'{frontend_url}/marketplace/checkout?order_id={order.id}&cancelled=true',
                'customer_email': user.email,
                'metadata': {
                    'user_id': str(user.id),
                    'order_id': str(order.id),
                },
            }
            
            # If seller has Stripe account, add transfer data
            if seller_account:
                session_data['payment_intent_data'] = {
                    'application_fee_amount': platform_fee_amount,
                    'transfer_data': {
                        'destination': seller_account,
                    },
                }
            
            checkout_session = stripe.checkout.Session.create(**session_data)
            
            # Save stripe session id to order
            order.stripe_session_id = checkout_session.id
            order.save()

            return Response({
                'checkout_session_id': checkout_session.id,
                'checkout_url': checkout_session.url,
                'order_id': str(order.id),
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
