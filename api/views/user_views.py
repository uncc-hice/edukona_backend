from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.db import transaction
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os
from rest_framework.throttling import UserRateThrottle

from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework import serializers

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from api.models import (
    Instructor,
    UserResponse,
    QuizSessionStudent,
    QuestionMultipleChoice,
    QuizSession,
    InstructorRecordings,
)
from api.serializers import (
    InstructorRecordingsSerializer,
    UpdateTranscriptSerializer,
    GetTranscriptResponseSerializer,
    GoogleLoginResponseSerializer,
    GoogleLoginRequestSerializer,
    ContactMessageSerializer,
)
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes

import boto3
import json


def mailInstructor(email):
    message = Mail(from_email="edukona.team@gmail.com", to_emails=email)

    message.template_id = os.getenv("WELCOME_TEMPLATE_ID")
    try:
        sg = SendGridAPIClient(os.environ.get("SENDGRID_API_KEY"))
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e.message)


class SignUpInstructor(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        new_user = request.data.pop("user", {})
        instructor = Instructor.objects.create(user=User.objects.create(**new_user), **request.data)
        user = get_object_or_404(User, id=instructor.user_id)
        user.set_password(new_user["password"])
        user.save()
        token = Token.objects.create(user=user)
        mailInstructor(user.email)
        return JsonResponse({"token": token.key, "user": user.id, "instructor": instructor.id})


class ProfileView(APIView):
    def get(self, request):
        user = request.user
        return Response(
            {
                "user": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
        )


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, style={"input_type": "password"})


class CheckDeveloperStatus(APIView):

    def get(self, request):
        user = request.user
        if user.is_staff:
            return Response({"isDeveloper": True})
        else:
            return Response({"isDeveloper": False}, status=403)


class Login(APIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):

        # use a try catch block to catch the error, and return a 401 status code
        try:
            user = User.objects.get(username=request.data["username"])
        except User.DoesNotExist:
            return JsonResponse(
                {"detail": "Invalid username or password!"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.check_password(request.data["password"]):
            return JsonResponse(
                {"detail": "Invalid username or password!"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        token = Token.objects.get_or_create(user=user)
        if hasattr(user, "instructor"):
            return JsonResponse(
                {
                    "token": token[0].key,
                    "user": user.id,
                    "instructor": user.instructor.id,
                }
            )
        # else:
        #     return JsonResponse({"token": token[0].key, "user": user.id, "student": user.student.id})


class Logout(APIView):
    def post(self, request):
        token = request.user.auth_token
        token.delete()
        token.save()
        return JsonResponse({"message": "User logged out successfully"})


class InstructorView(APIView):

    def post(self, request):
        user_data = request.data.pop("user", {})
        new_instructor = Instructor.objects.create(
            user=User.objects.create(**user_data), **request.data
        )
        return JsonResponse(
            {
                "message": "Instructor created successfully",
                "instructor_id": new_instructor.id,
            }
        )

    def get(self, request, instructor_id):
        instructor = get_object_or_404(Instructor, id=instructor_id)
        instructor_dict = {
            "id": instructor.id,
            "user_id": instructor.user.id,
            "created_at": instructor.user.date_joined if instructor.user else None,
        }
        return JsonResponse({"instructor": instructor_dict})

    def put(self, request, instructor_id):
        instructor = get_object_or_404(Instructor, id=instructor_id)
        instructor.__dict__.update(request.data.get("instructor", {}))
        instructor.save()
        user = get_object_or_404(User, id=instructor.user_id)
        user.__dict__.update(request.data.get("user", {}))
        user.save()
        return JsonResponse({"message": "Instructor updated successfully"})

    def delete(self, request, instructor_id):
        instructor = get_object_or_404(Instructor, id=instructor_id)
        instructor.user.delete()
        instructor.delete()
        return JsonResponse({"message": "Instructor deleted successfully"})


# class StudentView(APIView):

#   def post(self, request):
#     user_data = request.data.pop('user', {})
#     new_student = Student.objects.create(user=User.objects.create(**user_data), **request.data)
#     return JsonResponse({'message': 'Student created successfully', 'student_id': new_student.id})
#
# def get(self, request, student_id):
#     student = get_object_or_404(Student, id=student_id)
#     student_dict = {'id': student.id, 'user_id': student.user.id,
#                     'created_at': student.user.date_joined if student.user else None}
#     return JsonResponse({'student': student_dict})
#
# def put(self, request, student_id):
#     student = get_object_or_404(Student, id=student_id)
#     student.__dict__.update(request.data.get('student', {}))
#     student.save()
#     user = get_object_or_404(User, id=student.user_id)
#     user.__dict__.update(request.data.get('user', {}))
#     user.save()
#     return JsonResponse({'message': 'Student updated successfully'})
#
# def delete(self, request, student_id):
#     student = get_object_or_404(Student, id=student_id)
#     student.user.delete()
#     student.delete()
#     return JsonResponse({'message': 'Student deleted successfully'})


class UserResponseView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        student_data = request.data.pop("student", {})
        student = get_object_or_404(QuizSessionStudent, id=student_data["id"])
        question = get_object_or_404(QuestionMultipleChoice, id=request.data["question_id"])
        selected_answer = request.data["selected_answer"]
        quiz_session = get_object_or_404(QuizSession, code=request.data["quiz_session_code"])

        is_correct = selected_answer == question.correct_answer
        new_user_response = UserResponse.objects.create(
            student=student,
            is_correct=is_correct,
            quiz_session=quiz_session,
            question=question,
            selected_answer=selected_answer,
        )
        return JsonResponse(
            {
                "message": "User response created successfully",
                "response_id": new_user_response.id,
                "is_correct": is_correct,
            }
        )

    #   def get(self, request, response_id):
    #     user_response = get_object_or_404(UserResponse, id=response_id)
    #
    #     response_dict = {
    #         'id': user_response.id, 'student_id': user_response.student.id, 'question_id': user_response.question.id,
    #         'selected_answer': user_response.selected_answer, 'is_correct': user_response.is_correct,
    #     }
    #     return JsonResponse({'response': response_dict})

    def put(self, request, response_id):
        user_response = get_object_or_404(
            UserResponse, id=response_id, student_id=request.data["student_id"]
        )

        is_correct = request.data.get("selected_answer") == user_response.question.correct_answer
        user_response.__dict__.update({"is_correct": is_correct, **request.data})
        user_response.save()

        return JsonResponse(
            {"message": "User response updated successfully", "is_correct": is_correct}
        )

    # def delete(self, request, response_id):
    #     user_response = get_object_or_404(UserResponse, id=response_id)
    #
    #     user_response.delete()
    #     return JsonResponse({'message': 'User response deleted successfully'})


class UploadAudioView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        operation_id="upload_audio",
        summary="Upload an audio file",
        description="Uploads an audio file and saves it to the server.",
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {"file": {"type": "string", "format": "binary"}},
                "required": ["file"],
            }
        },
        responses={
            201: InstructorRecordingsSerializer,
            400: OpenApiTypes.OBJECT,  # Typically, a 400 would return an error object
        },
    )
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        instructor = get_object_or_404(Instructor, user=request.user)
        title = request.data.get("title", "")
        # Create the recording instance first to get the ID
        new_recording = InstructorRecordings.objects.create(instructor=instructor, title=title)

        # Sanitize and get the file details
        file = request.data["file"]
        file_name = self._sanitize_filename(file.name)
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME

        # Generate the S3 key (path)
        key = f"{str(instructor.id).zfill(5)}/{str(new_recording.id)}/{file_name}"

        try:
            # Upload to S3
            boto3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
            boto3_client.upload_fileobj(file, bucket_name, key)

            # Save the S3 path to the model instance
            new_recording.s3_path = key
            new_recording.save()

            # invoke a Lambda function and send the key as a parameter, make the invokation asynchronous
            lambda_client = boto3.client(
                "lambda",
                aws_access_key_id=settings.AWS_LAMBDA_INVOKER_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_LAMBDA_INVOKER_SECRET_ACCESS_KEY,
                region_name=settings.AWS_LAMBDA_INVOKER_REGION_NAME,
            )

            token = request.META.get("HTTP_AUTHORIZATION").split(" ")[1]
            lambda_client.invoke(
                FunctionName="TranscribeAudio",
                InvocationType="Event",
                Payload=json.dumps(
                    {
                        "s3_key": key,
                        "token": token,
                        "recording_id": str(new_recording.id),
                    }
                ),
            )

            return JsonResponse(InstructorRecordingsSerializer(new_recording).data, status=201)

        except Exception as e:
            transaction.set_rollback(True)
            return JsonResponse({"error": str(e)}, status=500)

    @staticmethod
    def _sanitize_filename(filename):
        """
        Sanitize the filename by removing special characters that may not be safe in S3 keys.
        """
        return "".join(
            char for char in filename if char.isalnum() or char in (" ", ".", "_")
        ).strip()


class UpdateTranscriptView(APIView):

    @extend_schema(
        operation_id="update_transcript",
        summary="Update the transcript of a recording",
        description="Updates the transcript of a recording with the given ID.",
        request=UpdateTranscriptSerializer,
        responses={
            200: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
    )
    def patch(self, request, recording_id):
        # Retrieve the InstructorRecordings instance by its ID
        recording = get_object_or_404(InstructorRecordings, id=recording_id)

        # Extract the transcript from the request data
        transcript = request.data.get("transcript", "")

        # Update the transcript field of the recording
        recording.transcript = transcript
        recording.save()

        # Return a success response with the updated data
        return JsonResponse(
            {
                "message": "Transcript updated successfully",
                "recording_id": recording.id,
            },
            status=status.HTTP_200_OK,
        )


class RecordingsView(APIView):
    @extend_schema(
        operation_id="get_recordings",
        summary="Get all recordings",
        description="Returns all recordings uploaded by the instructor.",
        responses={
            200: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        },
    )
    def get(self, request):
        instructor = request.user.instructor
        recordings = InstructorRecordings.objects.filter(instructor=instructor).order_by(
            "-uploaded_at"
        )

        # Filter so that the serializer only returns the s3_path, uploaded_at, id

        serializer = InstructorRecordingsSerializer(recordings, many=True)

        data = serializer.data

        for recording in data:
            if not recording.get("transcript"):
                recording["transcript"] = "pending"
            else:
                recording["transcript"] = "completed"

        return JsonResponse({"recordings": serializer.data})


class DeleteRecordingView(APIView):
    @extend_schema(
        operation_id="delete_recording",
        summary="Delete recording",
        description="Deletes the recording with the specified id",
        responses={
            200: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            500: OpenApiTypes.OBJECT,
        },
    )
    def delete(self, request, recording_id=None):
        instructor = request.user.instructor
        recording = get_object_or_404(InstructorRecordings, id=recording_id)
        if recording.instructor != instructor:
            return JsonResponse(
                {"message": "You do not have permission to delete this recording"},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            bucket_name = settings.AWS_STORAGE_BUCKET_NAME
            boto3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
            boto3_client.delete_object(Bucket=bucket_name, Key=recording.s3_path)
            recording.delete()
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

        return JsonResponse(
            {"message": "Successfully deleted recording"},
            status=status.HTTP_200_OK,
        )


class GetTranscriptView(APIView):
    @extend_schema(
        operation_id="get_transcript",
        summary="Get transcript of a recording",
        description="Returns the transcript of a recording with the specified ID.",
        responses={
            200: GetTranscriptResponseSerializer,
            404: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
        },
    )
    def get(self, request, recording_id):
        instructor = request.user.instructor
        recording = get_object_or_404(InstructorRecordings, id=recording_id)
        if recording.instructor != instructor:
            return JsonResponse(
                {"message": "You do not have permission to view this recording"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not recording.transcript:
            return JsonResponse(
                {"message": "Transcript is not available yet"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return JsonResponse({"transcript": recording.transcript}, status=status.HTTP_200_OK)


class GoogleLogin(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=GoogleLoginRequestSerializer,
        responses={
            200: GoogleLoginResponseSerializer,
            400: OpenApiTypes.OBJECT,
        },
    )
    def post(self, request):
        token = request.data.get("token")

        if not token:
            return Response({"message": "Token not provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Verify the Google token
            id_info = id_token.verify_oauth2_token(
                token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
            )

            # Get the user info from the token
            email = id_info.get("email")

            # Try to get the user based on the email
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response(
                    {"message": "Account does not exist. Please sign up first."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Generate a DRF token for the user
            token, _ = Token.objects.get_or_create(user=user)
            result = {
                "token": token.key,
                "user": {
                    "email": user.email,
                    "first_name": user.first_name,
                },
            }

            return Response(result, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {"message": f"Invalid token: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ContactPageThrottle(UserRateThrottle):
    rate = "10/hour"


class ContactPageView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ContactPageThrottle]
    serializers = ContactMessageSerializer

    @extend_schema(
        operation_id="create_contact_message",
        summary="Add a contact message to the DB",
        description="Creates a contact message entry in the ContactMessage table",
        request=ContactMessageSerializer,
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
        },
    )
    def post(self, request):
        serializer = ContactMessageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Message sent successfully"}, status=status.HTTP_200_OK)
        else:
            # Extracting error messages
            errors = serializer.errors
            if "email" in errors:
                return Response(
                    {"message": "Invalid email format"}, status=status.HTTP_400_BAD_REQUEST
                )
            elif any(field in errors for field in ["first_name", "last_name", "message"]):
                return Response(
                    {"message": "Please provide all required fields"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                # Generic error message
                return Response(
                    {"message": "Invalid data provided"}, status=status.HTTP_400_BAD_REQUEST
                )
