# views.py
from cProfile import Profile
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import stripe

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        return HttpResponse(status=400)

    # Handle the event
    if event['type'] == 'account.updated':
        account = event['data']['object']
        # Check if they finished onboarding
        if account.get('details_submitted', False):
            profile = Profile.objects.get(stripe_account_id=account['id'])
            profile.is_onboarding_complete = True
            profile.save()

    return HttpResponse(status=200)