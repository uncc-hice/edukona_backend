from django.db import transaction
from rest_framework.views import APIView
from api.models import *
from django.shortcuts import get_object_or_404
from rest_framework import status
from api.serializers import (
    QuestionMultipleChoiceSerializer,
)
from django.http import JsonResponse


class QuestionView(APIView):
    def post(self, request):
        # Expecting request.data to be a list of questions
        if not isinstance(request.data, list):
            return JsonResponse(
                {"error": "Expected a list of questions"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_questions = []
        errors = []

        with transaction.atomic():  # Use a transaction to ensure all or nothing is created
            for question_data in request.data:
                try:
                    new_question = QuestionMultipleChoice.objects.create(**question_data)
                    created_questions.append(
                        {
                            "question_id": new_question.id,
                            "message": "Question created successfully",
                        }
                    )
                except Exception as e:  # Catch exceptions from invalid data or database errors
                    errors.append({"question_data": question_data, "error": str(e)})

        if errors:
            return JsonResponse(
                {"created_questions": created_questions, "errors": errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return JsonResponse(
            {
                "created_questions": created_questions,
                "message": "All questions created successfully",
            },
            status=status.HTTP_201_CREATED,
        )

    # Get method to question by id
    def get(self, request, question_id):
        question = get_object_or_404(QuestionMultipleChoice, id=question_id)
        question_dict = {
            "id": question.id,
            "question_text": question.question_text,
            "incorrect_answer_list": question.incorrect_answer_list,
            "correct_answer": question.correct_answer,
            "points": question.points,
            "quiz_id": question.quiz.id,
        }
        return JsonResponse({"questions": question_dict})

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
