from django.conf import settings
from django.db import transaction

from rest_framework.response import Response
from rest_framework.views import APIView
from api.models import *
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.http import JsonResponse


class QuizView(APIView):
    def post(self, request):
        settings = request.data.pop("settings", {})
        instructor = get_object_or_404(Instructor, user=request.user)
        new_quiz = Quiz.objects.create(instructor=instructor, **request.data)
        new_quiz.settings = Settings.objects.create(**settings)
        new_quiz.save()
        return JsonResponse(
            {"message": "Quiz created successfully", "quiz_id": new_quiz.id}
        )

    def get(self, request, quiz_id=None):
        if quiz_id:
            quiz = get_object_or_404(Quiz, id=quiz_id)
            return JsonResponse({"quiz": quiz.to_json()})
        else:
            instructor = get_object_or_404(Instructor, user=request.user)
            all_quizzes = Quiz.objects.filter(instructor=instructor)
            quiz_response = [quiz.to_json() for quiz in all_quizzes]
            return JsonResponse({"quizzes": quiz_response})

    def put(self, request, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id)
        quiz.__dict__.update(request.data)
        quiz.save()
        return JsonResponse({"message": "Quiz updated successfully"})

    def delete(self, request, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id)
        quiz.delete()
        return JsonResponse({"message": "Quiz deleted successfully"})


class SettingsView(APIView):
    def get(self, request, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id)
        if not hasattr(quiz, "settings"):
            return JsonResponse({"error": "Quiz has no settings"}, status=404)
        return JsonResponse({"settings": quiz.settings.to_json()})

    def post(self, request, quiz_id):
        print(request.data)
        settings = request.data.pop("settings", {})
        new_settings = Settings.objects.create(**settings)
        quiz = get_object_or_404(Quiz, id=quiz_id)
        quiz.settings = new_settings
        quiz.save()
        return JsonResponse(
            {"message": "Settings created successfully", "settings_id": new_settings.id}
        )

    def patch(self, request, quiz_id):
        print(request.data)
        settings_data = request.data.get("settings", {})
        quiz = get_object_or_404(Quiz, id=quiz_id)

        if not hasattr(quiz, "settings"):
            return JsonResponse({"error": "Quiz has no settings to update"}, status=400)

        settings = quiz.settings

        for field, value in settings_data.items():
            setattr(settings, field, value)

        settings.save()
        return JsonResponse({"message": "Settings updated successfully"})