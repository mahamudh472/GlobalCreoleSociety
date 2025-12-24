from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet, ProductViewSet, CartViewSet, 
    OrderViewSet, DeliveryAddressAPIView, CheckoutPreviewAPIView, 
    CreateStripeConnectedAccountAPIView, CreateCheckoutSessionAPIView,
    StripeAccountStatusAPIView, ResumeStripeOnboardingAPIView
    )
from .webhook import stripe_webhook

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
    path('checkout/create-session/', CreateCheckoutSessionAPIView.as_view(), name='create-checkout-session'),
    path('stripe/create-connected-account/', CreateStripeConnectedAccountAPIView.as_view(), name='create-stripe-connected-account'),
    path('stripe/account-status/', StripeAccountStatusAPIView.as_view(), name='stripe-account-status'),
    path('stripe/resume-onboarding/', ResumeStripeOnboardingAPIView.as_view(), name='stripe-resume-onboarding'),
    path('webhook/stripe/', stripe_webhook, name='stripe-webhook'),
]
