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
        # Handle successful checkout - update order payment status
        session = event['data']['object']
        
        # Get metadata
        metadata = session.get('metadata', {})
        order_id = metadata.get('order_id')
        
        if order_id:
            try:
                from .models import Order
                from django.utils import timezone
                
                order = Order.objects.get(id=order_id)
                order.payment_status = 'paid'
                order.status = 'processing'
                order.payment_at = timezone.now()
                order.save()
                    
            except Order.DoesNotExist:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Order not found for checkout webhook: {order_id}")
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error processing checkout webhook: {e}")
    
    elif event_type == 'checkout.session.expired':
        # Handle expired checkout session - cancel order and restore stock
        session = event['data']['object']
        metadata = session.get('metadata', {})
        order_id = metadata.get('order_id')
        
        if order_id:
            try:
                from .models import Order
                
                order = Order.objects.get(id=order_id)
                
                # Only cancel if still pending payment
                if order.payment_status == 'pending':
                    order.status = 'cancelled'
                    order.payment_status = 'failed'
                    order.save()
                    
                    # Restore stock
                    for item in order.items.select_related('product').all():
                        if item.product:
                            item.product.stock += item.quantity
                            item.product.save()
                            
            except Order.DoesNotExist:
                pass
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error handling expired session: {e}")
    
    elif event_type == 'payment_intent.payment_failed':
        # Handle failed payment - update order status
        payment_intent = event['data']['object']
        session_id = payment_intent.get('metadata', {}).get('session_id')
        
        if session_id:
            try:
                from .models import Order
                
                order = Order.objects.get(stripe_session_id=session_id)
                if order.payment_status == 'pending':
                    order.payment_status = 'failed'
                    order.save()
            except Order.DoesNotExist:
                pass
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error handling payment failed: {e}")

    return HttpResponse(status=200)