from rest_framework import permissions
from .models import Instructor, Quiz, QuestionMultipleChoice


class AllowInstructor(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        return Instructor.objects.filter(user=request.user).exists()


class IsQuizOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        quiz_id = view.kwargs.get("quiz_id")
        if not quiz_id:
            quiz_id = request.data.get("quiz_id")

        quiz = Quiz.objects.get(id=quiz_id)
        return request.user == quiz.instructor.user


class IsQuestionOwner(AllowInstructor):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        question_id = view.kwargs.get("question_id")
        if not question_id:
            question_id = request.data.get("question_id")

        question = QuestionMultipleChoice.objects.get(id=question_id)
        return request.user.id == question.quiz.instructor.user.id
