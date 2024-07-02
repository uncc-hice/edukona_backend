from rest_framework import permissions
from .models import Instructor


class AllowInstructor(permissions.BasePermission):
      def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        return Instructor.objects.filter(user=request.user).exists()