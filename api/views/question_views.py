from django.db import transaction
from rest_framework.views import APIView
from api.models import *
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from api.serializers import (
    QuestionMultipleChoiceSerializer,
)
from rest_framework import serializers
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, OpenApiResponse

from ..permissions import IsQuestionOwner
from ..permissions import AllowInstructor


class QuestionView(APIView):
    # permission_classes = [IsQuestionOwner]
    permission_classes = [AllowInstructor]

    @extend_schema(
        request=QuestionMultipleChoiceSerializer(many=True),
        responses={
            201: OpenApiResponse(description="Questions created successfully"),
            400: OpenApiResponse(description="Bad Request"),
            403: OpenApiResponse(description="Forbidden"),
        },
    )
    def post(self, request):
        # Expecting request.data to be a list of questions
        if not isinstance(request.data, list):
            return JsonResponse(
                {"error": "Expected a list of questions"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_questions = []
        errors = []

        with transaction.atomic():
            for question_data in request.data:
                try:
                    serializer = QuestionMultipleChoiceSerializer(data=question_data)
                    serializer.is_valid(raise_exception=True)
                    serializer.save()
                    created_questions.append(serializer.data)
                except PermissionDenied as e:
                    return JsonResponse({"detail": e.__str__()}, status=status.HTTP_403_FORBIDDEN)
                except serializers.ValidationError as e:
                    errors.append({"question_data": question_data, "error": e.detail})
                except Exception as e:
                    errors.append({"question_data": question_data, "error": str(e)})

        if errors:
            return JsonResponse(
                {"created_questions": created_questions, "errors": errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return JsonResponse(
            {"created_questions": created_questions, "errors": errors},
            status=status.HTTP_201_CREATED,
        )

    # Get method to question by id
    def get(self, request, question_id):
        question = get_object_or_404(QuestionMultipleChoice, id=question_id)
        serializer = QuestionMultipleChoiceSerializer(question)
        return JsonResponse(serializer.data)

    # Put method to update text of a question by taking in an id
    def put(self, request, question_id):
        question = get_object_or_404(QuestionMultipleChoice, id=question_id)
        question.__dict__.update(request.data)
        question.save()
        return JsonResponse({"message": "Question updated successfully"})

    # delete method to delete question by id
    def delete(self, request, question_id):
        question = get_object_or_404(QuestionMultipleChoice, id=question_id)
        question.delete()
        return JsonResponse({"message": "Question deleted successfully"})


class AllQuizQuestionsView(APIView):
    def get(self, request, quiz_id):
        questions = QuestionMultipleChoice.objects.filter(quiz_id=quiz_id)
        serializer = QuestionMultipleChoiceSerializer(questions, many=True)
        return JsonResponse({"questions": serializer.data})
