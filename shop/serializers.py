from rest_framework import serializers
from .models import Category, Product, ProductImage, Cart, CartItem, Order, OrderItem, DeliveryAddress
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model"""
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'product_count', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_product_count(self, obj):
        return obj.products.filter(status='approved').count()


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for ProductImage model"""

    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'is_primary', 'created_at']
        read_only_fields = ['created_at']



class ProductListSerializer(serializers.ModelSerializer):
    """Serializer for listing products"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    seller_name = serializers.CharField(source='seller.profile_name', read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'category', 'category_name', 'price', 
                  'stock', 'status', 'seller', 'seller_name', 'primary_image', 'created_at']
        read_only_fields = ['status', 'seller', 'created_at']

    def get_primary_image(self, obj):
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            return ProductImageSerializer(primary_image, context=self.context).data
        # Return first image if no primary image is set
        first_image = obj.images.first()
        if first_image:
            return ProductImageSerializer(first_image, context=self.context).data
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    """Serializer for product detail view"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    seller_name = serializers.CharField(source='seller.profile_name', read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'category', 'category_name', 'price', 
                  'stock', 'status', 'seller', 'seller_name', 'images', 'uploaded_images',
                  'rejection_reason', 'created_at', 'updated_at', 'approved_at', 'approved_by']
        read_only_fields = ['status', 'seller', 'rejection_reason', 'created_at', 
                           'updated_at', 'approved_at', 'approved_by']

    def create(self, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        validated_data['seller'] = self.context['request'].user
        product = Product.objects.create(**validated_data)
        
        # Create product images
        for idx, image in enumerate(uploaded_images):
            ProductImage.objects.create(
                product=product,
                image=image,
                is_primary=(idx == 0)  # First image is primary
            )
        
        return product

    def update(self, instance, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', None)
        
        # Update product fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Add new images if provided
        if uploaded_images:
            for image in uploaded_images:
                ProductImage.objects.create(
                    product=instance,
                    image=image
                )
        
        return instance


class ProductApprovalSerializer(serializers.ModelSerializer):
    """Serializer for admin to approve/reject products"""
    class Meta:
        model = Product
        fields = ['id', 'status', 'rejection_reason']

    def validate(self, data):
        if data.get('status') == 'rejected' and not data.get('rejection_reason'):
            raise serializers.ValidationError({
                'rejection_reason': 'Rejection reason is required when rejecting a product.'
            })
        return data

    def update(self, instance, validated_data):
        status = validated_data.get('status')
        if status == 'approved':
            instance.approved_at = timezone.now()
            instance.approved_by = self.context['request'].user
            instance.rejection_reason = None
        elif status == 'rejected':
            instance.approved_at = None
            instance.approved_by = None
        
        instance.status = status
        instance.rejection_reason = validated_data.get('rejection_reason')
        instance.save()
        return instance


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for CartItem model"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2, read_only=True)
    product_image = serializers.SerializerMethodField()
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    available_stock = serializers.IntegerField(source='product.stock', read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_name', 'product_price', 'product_image',
                  'quantity', 'subtotal', 'available_stock', 'added_at', 'updated_at']
        read_only_fields = ['added_at', 'updated_at']

    def get_product_image(self, obj):
        primary_image = obj.product.images.filter(is_primary=True).first()
        if primary_image:
            return ProductImageSerializer(primary_image, context=self.context).data
        first_image = obj.product.images.first()
        if first_image:
            return ProductImageSerializer(first_image, context=self.context).data
        return None

    def validate(self, data):
        product = data.get('product')
        quantity = data.get('quantity', 1)
        
        # Check if product is approved
        if product.status != 'approved':
            raise serializers.ValidationError('This product is not available for purchase.')
        
        # Check stock availability
        if quantity > product.stock:
            raise serializers.ValidationError(f'Only {product.stock} items available in stock.')
        
        return data


class CartSerializer(serializers.ModelSerializer):
    """Serializer for Cart model"""
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_items', 'total_price', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for OrderItem model"""
    product_image = serializers.ImageField(source='product.images.first.image', read_only=True)
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'product_image', 'product_price', 'quantity', 'subtotal']
        read_only_fields = ['product_name', 'product_price', 'subtotal']


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Order model"""
    items = OrderItemSerializer(many=True, read_only=True)
    user_name = serializers.CharField(source='user.profile_name', read_only=True)
    # Alias for frontend compatibility
    total_price = serializers.DecimalField(source='total_amount', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'user', 'user_name', 'total_amount', 'total_price', 'status', 'payment_status',
                  'payment_method', 'delivery_type', 'items', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['user', 'total_amount', 'total_price', 'created_at', 'updated_at']


class CheckoutSerializer(serializers.Serializer):
    """Serializer for checkout process"""
    cart_item_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="List of cart item IDs to checkout. If not provided, all cart items will be used."
    )
    delivery_type = serializers.CharField(required=False, default='home')
    payment_method = serializers.CharField(required=False, default='cash_on_delivery')
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_cart_item_ids(self, value):
        if value:
            user = self.context['request'].user
            cart = getattr(user, 'cart', None)
            if not cart:
                raise serializers.ValidationError("You don't have a cart.")
            
            # Verify all item IDs belong to user's cart
            cart_item_ids = set(cart.items.values_list('id', flat=True))
            invalid_ids = set(value) - cart_item_ids
            if invalid_ids:
                raise serializers.ValidationError(f"Invalid cart item IDs: {invalid_ids}")
        
        return value


class BuyNowSerializer(serializers.Serializer):
    """Serializer for buy now (single item checkout)"""
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    delivery_type = serializers.CharField(required=False, default='home')
    payment_method = serializers.CharField(required=False, default='cash_on_delivery')
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_product_id(self, value):
        try:
            product = Product.objects.get(id=value)
            if product.status != 'approved':
                raise serializers.ValidationError("This product is not available for purchase.")
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found.")
        return value

    def validate(self, data):
        product = Product.objects.get(id=data['product_id'])
        if data['quantity'] > product.stock:
            raise serializers.ValidationError({
                'quantity': f'Only {product.stock} items available in stock.'
            })
        return data
    
class DeliveryAddressSerializer(serializers.Serializer):
    """Serializer for delivery address details"""
    receiver_name = serializers.CharField(max_length=255)
    phone = serializers.CharField(max_length=20)
    city = serializers.CharField(max_length=100)
    address = serializers.CharField()

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        return DeliveryAddress.objects.update_or_create(user=user, defaults=validated_data)