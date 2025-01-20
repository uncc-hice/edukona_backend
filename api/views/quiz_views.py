from botocore.exceptions import ClientError
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
import json
import logging
from rest_framework.permissions import AllowAny

from api.models import Quiz, InstructorRecordings
from api.serializers import (
    QuizSerializer,
    QuizListSerializer,
    QuizTitleUpdateSerializer,
    FetchCourseQuizzesSerializer,
)
from django.shortcuts import get_object_or_404
from django.http import JsonResponse

from drf_spectacular.utils import extend_schema, OpenApiResponse

from ..permissions import IsCourseOwner, IsEnrolledInCourse
from ..permissions import IsQuizOwner, AllowInstructor, IsRecordingOwner
import boto3
from django.conf import settings

logger = logging.getLogger(__name__)


@extend_schema(tags=["Quiz Creation and Modification"])
class QuizView(APIView):
    permission_classes = [IsQuizOwner]

    def get(self, request, quiz_id):
        if quiz_id:
            quiz = get_object_or_404(Quiz, id=quiz_id)
            return JsonResponse({"quiz": quiz.to_json()})

    def put(self, request, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id)
        quiz.__dict__.update(request.data)
        quiz.save()
        return JsonResponse({"message": "Quiz updated successfully"})

    def delete(self, request, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id)
        quiz.delete()
        return JsonResponse({"message": "Quiz deleted successfully"})


@extend_schema(tags=["Quiz Creation and Modification"])
class CreateQuizView(APIView):
    permission_classes = [AllowInstructor]

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


@extend_schema(tags=["Quiz Creation and Modification"])
class UpdateQuizTitleView(APIView):
    permission_classes = [IsQuizOwner]

    @extend_schema(
        request=QuizTitleUpdateSerializer,
        description="Endpoint to update the title of a specific quiz",
    )
    def patch(self, request, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id)

        # Pass request data to the serializer for validation
        serializer = QuizTitleUpdateSerializer(data=request.data)

        if serializer.is_valid():
            # If valid, update the quiz title
            quiz.title = serializer.validated_data["title"]
            quiz.save()
            return Response(
                {"message": "Title updated successfully", "title": quiz.title},
                status=status.HTTP_200_OK,
            )

        # If not valid, return validation errors
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["Quiz Creation and Modification"])
class InstructorQuizzesView(APIView):
    permission_class = [AllowInstructor]

    @extend_schema(responses={200: QuizListSerializer}, summary="Get all quizzes by instructor")
    def get(self, request):
        quizzes = Quiz.objects.filter(instructor=request.user.instructor)
        return Response(QuizListSerializer({"quizzes": quizzes}).data, status=status.HTTP_200_OK)


@extend_schema(tags=["Quiz Creation and Modification"])
class CreateQuizFromTranscript(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="create-quiz-from-transcript",
        summary="Creates a new quiz from a transcript",
        description="Created a new quiz for a user given a transcript",
        request=QuizSerializer,
        responses={
            201: QuizSerializer,
            204: OpenApiResponse(description="No Content"),
            400: OpenApiResponse(description="Bad Request"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
        },
    )
    def post(self, request):
        instructor_recording = get_object_or_404(
            InstructorRecordings, id=request.data["instructor_recording"]
        )
        data = request.data.copy()
        data["instructor"] = instructor_recording.instructor
        print(f"The data collected: {data}")
        serializer = QuizSerializer(data=data, context={"request": request})
        print(f"Serializer successfully created")
        if serializer.is_valid():
            serializer.save()
            new_quiz = serializer.instance
            print(f"The new quiz created: {new_quiz}")

        return Response({"message": "This is a test message."}, status=status.HTTP_200_OK)


@extend_schema(tags=["Quiz Creation and Modification"])
class QuizzesByCourseView(APIView):
    permission_classes = [IsCourseOwner | IsEnrolledInCourse]

    @extend_schema(
        responses={200: FetchCourseQuizzesSerializer(many=True)},
        summary="Get all quizzes by course",
    )
    def get(self, request, course_id):
        # check whether request user is student or instructor
        is_instructor = True if hasattr(request.user, "instructor") else False
        if is_instructor:
            # return all quizes for course
            quizzes = Quiz.objects.filter(course_id=course_id)
        else:
            # Return only published quizzes
            quizzes = Quiz.objects.filter(published=True, course_id=course_id)

        return_response = FetchCourseQuizzesSerializer(quizzes, many=True).data
        return Response(return_response, status=status.HTTP_200_OK)
