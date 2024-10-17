from rest_framework import permissions
from .models import Instructor, Quiz


class AllowInstructor(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        return Instructor.objects.filter(user=request.user).exists()


class IsQuizOwner(AllowInstructor):
    def has_object_permission(self, request, view, obj):
        return request.user.id == obj.instructor.user.id


class IsQuestionOwner(AllowInstructor):
    def has_object_permission(sel, request, view, obj):
        if isinstance(obj, Quiz):
            return request.user.id == obj.instructor.user.id
        return request.user.id == obj.quiz.instructor.user.id
