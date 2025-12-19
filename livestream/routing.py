from django.urls import re_path
from .consumers import LiveStreamConsumer

websocket_urlpatterns = [
    re_path(r'ws/livestream/(?P<livestream_id>[0-9a-f-]+)/$', LiveStreamConsumer.as_asgi()),
]
