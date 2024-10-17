from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response

from api.models import *
from api.serializers import QuizSerializer
from django.shortcuts import get_object_or_404
from django.http import JsonResponse

from drf_spectacular.utils import extend_schema, OpenApiResponse

from ..permissions import IsQuizOwner


class QuizView(APIView):
    permission_classes = [IsQuizOwner]

    @extend_schema(
        request=QuizSerializer,
        responses={
            201: OpenApiResponse(
                description="Quiz created successfully",
            ),
            400: OpenApiResponse(description="Bad Request"),
            404: OpenApiResponse(description="Instructor not found"),
        },
        summary="Create a new Quiz",
        description="Creates a new Quiz associated with the authenticated Instructor.",
    )
    def post(self, request):
        """
        Create a new Quiz.
        """
        serializer = QuizSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            quiz = serializer.save()
            return Response(
                {"message": "Quiz created successfully", "quiz_id": quiz.id},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, quiz_id=None):
        if quiz_id:
            quiz = get_object_or_404(Quiz, id=quiz_id)
            return JsonResponse({"quiz": quiz.to_json()})
        else:
            instructor = get_object_or_404(Instructor, user=request.user)
            all_quizzes = Quiz.objects.filter(instructor=instructor).order_by("-created_at")
            quiz_response = [quiz.to_json() for quiz in all_quizzes]
            return JsonResponse({"quizzes": quiz_response})

    def put(self, request, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id)
        self.check_object_permissions(request, quiz)
        quiz.__dict__.update(request.data)
        quiz.save()
        return JsonResponse({"message": "Quiz updated successfully"})

    def delete(self, request, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id)
        self.check_object_permissions(request, quiz)
        quiz.delete()
        return JsonResponse({"message": "Quiz deleted successfully"})


class SettingsView(APIView):
    permission_classes = [IsQuizOwner]

    def get(self, request, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id)
        self.check_object_permissions(request, quiz)
        if not hasattr(quiz, "settings"):
            return JsonResponse({"error": "Quiz has no settings"}, status=404)
        return JsonResponse({"settings": quiz.settings.to_json()})

    def post(self, request, quiz_id):
        print(request.data)
        settings = request.data.pop("settings", {})
        new_settings = Settings.objects.create(**settings)
        quiz = get_object_or_404(Quiz, id=quiz_id)
        self.check_object_permissions(request, quiz)
        quiz.settings = new_settings
        quiz.save()
        return JsonResponse(
            {"message": "Settings created successfully", "settings_id": new_settings.id}
        )

    def patch(self, request, quiz_id):
        print(request.data)
        settings_data = request.data.get("settings", {})
        quiz = get_object_or_404(Quiz, id=quiz_id)
        self.check_object_permissions(request, quiz)

        if not hasattr(quiz, "settings"):
            return JsonResponse({"error": "Quiz has no settings to update"}, status=400)

        settings = quiz.settings

        for field, value in settings_data.items():
            setattr(settings, field, value)

        settings.save()
        return JsonResponse({"message": "Settings updated successfully"})
