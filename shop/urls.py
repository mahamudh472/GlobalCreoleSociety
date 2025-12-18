from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProductViewSet, CartViewSet, OrderViewSet, DeliveryAddressAPIView, CheckoutPreviewAPIView

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'delivery-address', DeliveryAddressAPIView, basename='delivery-address')

app_name = 'shop'

urlpatterns = [
    path('', include(router.urls)),
    path('checkout/preview/', CheckoutPreviewAPIView.as_view(), name='checkout-preview'),
]
