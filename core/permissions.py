
from rest_framework.permissions import BasePermission, IsAuthenticated

class IsTrainerOwned(IsAuthenticated):

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        trainer_id = getattr(obj, "trainer_id", None)
        if trainer_id is None:

            parent = (
                getattr(obj, "plan", None)
                or getattr(obj, "day", None)
                or getattr(obj, "session", None)
                or getattr(obj, "client", None)
            )
            while parent is not None and getattr(parent, "trainer_id", None) is None:
                parent = (
                    getattr(parent, "plan", None)
                    or getattr(parent, "day", None)
                    or getattr(parent, "client", None)
                )
            trainer_id = getattr(parent, "trainer_id", None)
        return trainer_id == request.user.id
