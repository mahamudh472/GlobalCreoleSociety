# webhook.py
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import stripe
import json

stripe.api_key = settings.STRIPE_SECRET_KEY

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)
    except Exception as e:
        return HttpResponse(status=400)

    # Handle the event
    event_type = event['type']
    
    if event_type == 'account.updated':
        # Handle Stripe Connect account updates
        account = event['data']['object']
        account_id = account.get('id')
        charges_enabled = account.get('charges_enabled', False)
        payouts_enabled = account.get('payouts_enabled', False)

        if charges_enabled and payouts_enabled and account_id:

            try:
                from accounts.models import User
                user = User.objects.get(stripe_account_id=account_id)
                user.is_onboarding_completed = True
                user.save()
            except User.DoesNotExist:
                pass
    
    elif event_type == 'checkout.session.completed':
        # Handle successful checkout
        session = event['data']['object']
        
        # Get metadata
        user_id = session.get('metadata', {}).get('user_id')
        cart_id = session.get('metadata', {}).get('cart_id')
        
        if user_id and cart_id:
            try:
                with transaction.atomic():
                    from accounts.models import User
                    from .models import Cart, Order, OrderItem
                    
                    user = User.objects.get(id=user_id)
                    cart = Cart.objects.get(id=cart_id, user=user)
                    
                    # Create order from cart
                    total_amount = sum(item.subtotal for item in cart.items.all())
                    
                    order = Order.objects.create(
                        user=user,
                        total_amount=total_amount,
                        status='processing',
                        payment_method='card',
                        payment_status='paid',
                        stripe_session_id=session.get('id'),
                    )
                    
                    # Create order items from cart items
                    for cart_item in cart.items.select_related('product').all():
                        OrderItem.objects.create(
                            order=order,
                            product=cart_item.product,
                            product_name=cart_item.product.title,
                            product_price=cart_item.product.price,
                            quantity=cart_item.quantity,
                        )
                        
                        # Reduce stock
                        cart_item.product.stock -= cart_item.quantity
                        cart_item.product.save()
                    
                    # Clear the cart
                    cart.items.all().delete()
                    
            except Exception as e:
                # Log the error but don't fail the webhook
                print(f"Error processing checkout webhook: {e}")
    
    elif event_type == 'checkout.session.expired':
        # Handle expired checkout session
        session = event['data']['object']
        # You could notify the user here or clean up any pending records
        pass
    
    elif event_type == 'payment_intent.payment_failed':
        # Handle failed payment
        payment_intent = event['data']['object']
        # You could notify the user here
        pass

    return HttpResponse(status=200)