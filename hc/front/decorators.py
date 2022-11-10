from functools import wraps

from django.conf import settings
from django.http import HttpResponse


def require_setting(key):
    def decorator(f):
        @wraps(f)
        def wrapper(request, *args, **kwds):
            return (
                f(request, *args, **kwds)
                if getattr(settings, key)
                else HttpResponse(status=404)
            )

        return wrapper

    return decorator
