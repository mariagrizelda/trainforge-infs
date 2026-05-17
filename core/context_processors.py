
from django.conf import settings

def feature_flags(request):

    return {
        "google_oauth_enabled": bool(getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")),
    }
