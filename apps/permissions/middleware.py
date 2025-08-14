from asgiref.sync import iscoroutinefunction

from .checks import clear_perm_cache


class PermissionCacheMiddleware:
    """Clear the permission cache after each request."""

    def __init__(self, get_response):
        self.get_response = get_response
        self._is_async = iscoroutinefunction(get_response)

    def __call__(self, request):
        if self._is_async:
            return self._acall(request)
        try:
            response = self.get_response(request)
        finally:
            clear_perm_cache()
        return response

    async def _acall(self, request):
        try:
            response = await self.get_response(request)
        finally:
            clear_perm_cache()
        return response
