"""Custom permission classes for worker and officer roles."""

from rest_framework.permissions import BasePermission


class IsWorker(BasePermission):
    """Allows access only to authenticated workers (via JWT)."""

    def has_permission(self, request, view) -> bool:
        """Return True if request has an attached worker."""
        return hasattr(request, "worker") and request.worker is not None


class IsOfficer(BasePermission):
    """Allows access only to authenticated staff users."""

    def has_permission(self, request, view) -> bool:
        """Return True if request.user is authenticated staff."""
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and user.is_staff)

