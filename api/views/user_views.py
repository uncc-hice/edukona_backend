import json
import logging
import os

import boto3
from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    extend_schema,
)
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from api.models import (
    Instructor,
    InstructorRecordings,
    QuestionMultipleChoice,
    Quiz,
    QuizSession,
    QuizSessionStudent,
    UserResponse,
)
from api.serializers import (
    ContactMessageSerializer,
    GetScoreRequestSerializer,
    GetScoreResponseSerializer,
    GetTranscriptResponseSerializer,
    GoogleLoginRequestSerializer,
    GoogleLoginResponseSerializer,
    InstructorRecordingsSerializer,
    LoginErrorResponseSerializer,
    LoginResponseSerializer,
    LoginSerializer,
    LogoutSerializer,
    QuizSerializer,
    ScoreQuizRequestSerializer,
    ScoreQuizResponseSerializer,
    SignUpInstructorSerializer,
    UpdateTranscriptSerializer,
)

from ..permissions import IsRecordingOwner
from ..services import score_session

logger = logging.getLogger(__name__)


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
        logger.error(f"Failed to send email to {email} with error: {str(e)}")


@extend_schema(tags=["Authentication Endpoint"])
class SignUpInstructor(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="sign_up_instructor",
        summary="Sign up as an Instructor",
        description="Allows a new user to sign up as an instructor by "
        "providing first name, last name (optional), email, and password.",
        request=SignUpInstructorSerializer,
        responses={
            201: {
                "description": "Instructor created successfully.",
                "content": {
                    "application/json": {
                        "example": {
                            "token": "abc123def456ghi789",
                            "user": "user-uuid-string",
                            "instructor": "instructor-uuid-string",
                        }
                    }
                },
            },
            400: {
                "description": "Bad Request. Input data is invalid.",
                "content": {
                    "application/json": {
                        "example": {"message": "A user with this email already exists."}
                    }
                },
            },
        },
        examples=[
            OpenApiExample(
                "Valid Input",
                value={
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "john.doe@example.com",
                    "password": "StrongPassword123!",
                },
                request_only=True,
                response_only=False,
            ),
        ],
    )
    def post(self, request):
        serializer = SignUpInstructorSerializer(data=request.data)
        if serializer.is_valid():
            instructor = serializer.save()
            user = instructor.user
            token, created = Token.objects.get_or_create(user=user)
            mailInstructor(user.email)  # Send a welcome email to the instructor
            return Response(
                {"token": token.key, "user": str(user.id), "instructor": str(instructor.id)},
                status=status.HTTP_201_CREATED,
            )
        else:
            # Customize error messages based on validation errors
            errors = serializer.errors
            if "email" in errors:
                return Response({"message": errors["email"][0]}, status=status.HTTP_400_BAD_REQUEST)
            elif "password" in errors:
                return Response(
                    {"message": errors["password"][0]}, status=status.HTTP_400_BAD_REQUEST
                )
            elif "first_name" in errors:
                return Response(
                    {"message": "Please provide all required fields."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                # Generic error message for other validation errors
                return Response(
                    {"message": "Invalid data provided."}, status=status.HTTP_400_BAD_REQUEST
                )


@extend_schema(
    operation_id="sign_up_instructor",
    summary="Sign up as an Instructor",
    description="Allows a new user to sign up as an instructor by providing first name, last name (optional), email, and password. Returns JWT tokens upon successful registration.",
    request=SignUpInstructorSerializer,
    responses={
        201: {
            "description": "Instructor created successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "access": "jwt_access_token",
                        "refresh": "jwt_refresh_token",
                        "user": "user-uuid-string",
                        "instructor": "instructor-uuid-string",
                    }
                }
            },
        },
        400: {
            "description": "Bad Request. Input data is invalid.",
            "content": {
                "application/json": {
                    "example": {"message": "A user with this email already exists."}
                }
            },
        },
        403: {
            "description": "Forbidden. An error occurred while signing up.",
            "content": {
                "application/json": {"example": {"message": "An error occurred while signing up."}}
            },
        },
        500: {
            "description": "Internal Server Error. An error occurred while signing up.",
            "content": {
                "application/json": {"example": {"message": "An error occurred while signing up."}}
            },
        },
    },
    examples=[
        OpenApiExample(
            "Valid Input",
            value={
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "password": "StrongPassword123!",
            },
            request_only=True,
            response_only=False,
        ),
    ],
    tags=["Authentication Endpoint"],
)
class JWTSignUpInstructor(APIView):
    permission_classes = [AllowAny]
    serializer_class = SignUpInstructorSerializer

    def post(self, request):
        serializer = SignUpInstructorSerializer(data=request.data)
        if serializer.is_valid():
            instructor = serializer.save()
            user = instructor.user
            refresh = RefreshToken.for_user(user)

            response = {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": user.id,
                "instructor": instructor.id,
            }

            mailInstructor(user.email)  # Send a welcome email to the instructor
            logger.info(f"Instructor {user.id} signed up successfully.")
            return Response(response, status=status.HTTP_201_CREATED)
        else:
            errors = serializer.errors
            if "email" in errors:
                logger.warning(
                    f"Sign up failed for email {request.data.get('email')}: {errors['email'][0]}"
                )
                return Response({"message": errors["email"][0]}, status=status.HTTP_400_BAD_REQUEST)
            elif "password" in errors:
                logger.warning(
                    f"Sign up failed for email {request.data.get('email')}: {errors['password'][0]}"
                )
                return Response(
                    {"message": errors["password"][0]}, status=status.HTTP_400_BAD_REQUEST
                )
            elif "first_name" in errors:
                logger.warning(
                    f"Sign up failed for email {request.data.get('email')}: Missing first name"
                )
                return Response(
                    {"message": "Please provide all required fields."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                logger.warning(
                    f"Sign up failed for email {request.data.get('email')}: Invalid data provided"
                )
                return Response(
                    {"message": "Invalid data provided."}, status=status.HTTP_400_BAD_REQUEST
                )


@extend_schema(tags=["Profile and User Management"])
class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

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


@extend_schema(tags=["Profile and User Management"])
class CheckDeveloperStatus(APIView):

    def get(self, request):
        user = request.user
        if user.is_staff:
            return Response({"isDeveloper": True})
        else:
            return Response({"isDeveloper": False}, status=403)


@extend_schema(tags=["Authentication Endpoint"])
class Login(APIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            user = User.objects.get(email=request.data["email"])
        except User.DoesNotExist:
            return JsonResponse(
                {"detail": "Invalid email or password!"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.check_password(request.data["password"]):
            return JsonResponse(
                {"detail": "Invalid email or password!"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        # Delete all previous tokens
        Token.objects.filter(user=user).delete()

        token = Token.objects.create(user=user)

        # JWT section
        refresh = RefreshToken.for_user(user)

        response = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "token": token.key,
            "user": user.id,
        }

        if hasattr(user, "instructor"):
            response["instructor"] = user.instructor.id

        logger.info(f"User {user.id} logged in.")
        return JsonResponse(response, status=status.HTTP_200_OK)


@extend_schema(tags=["Authentication Endpoint"])
@extend_schema(
    operation_id="jwt_login",
    summary="Login with JWT",
    description="Allows a user to log in using an email and password, and returns JWT tokens.",
    request=LoginSerializer,
    responses={200: LoginResponseSerializer, 401: LoginErrorResponseSerializer},
)
class JWTLoginView(APIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            user = User.objects.get(email=request.data["email"])
        except User.DoesNotExist:
            return JsonResponse(
                {"detail": "Invalid email or password!"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.check_password(request.data["password"]):
            return JsonResponse(
                {"detail": "Invalid email or password!"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)

        response = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": user.id,
        }

        if hasattr(user, "instructor"):
            response["instructor"] = user.instructor.id

        response_serializer = LoginResponseSerializer(data=response)
        response_serializer.is_valid(raise_exception=True)

        logger.info(f"User {user.id} logged in.")
        return JsonResponse(response, status=status.HTTP_200_OK)


@extend_schema(tags=["Authentication Endpoint"])
class Logout(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logger.info(f"User {request.user.id} logged out.")
        request.user.auth_token.delete()
        return JsonResponse({"message": "User logged out successfully"}, status=status.HTTP_200_OK)


@extend_schema(
    operation_id="jwt_logout",
    summary="Logout with JWT",
    description="Allows a user to log out using a refresh token, and blacklists the token.",
    request=LogoutSerializer,
    responses={
        200: {
            "description": "Logout successful",
            "content": {"application/json": {"example": {"detail": "Logout successful"}}},
        },
        400: {
            "description": "Bad Request. Refresh token is required.",
            "content": {"application/json": {"example": {"detail": "Refresh token is required"}}},
        },
        403: {
            "description": "Forbidden. An error occurred while logging out.",
            "content": {
                "application/json": {"example": {"detail": "An error occurred while logging out."}}
            },
        },
        500: {
            "description": "Internal Server Error. An error occurred while logging out.",
            "content": {
                "application/json": {"example": {"detail": "An error occurred while logging out."}}
            },
        },
    },
    examples=[
        OpenApiExample(
            "Valid Input",
            value={"refresh": "abc123def456ghi789"},
            request_only=True,
            response_only=False,
        ),
    ],
    tags=["Authentication Endpoint"],
)
class JWTLogoutView(APIView):
    serializer_class = LogoutSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logger.info(f"Received logout request from user {request.user.id}")

        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                logger.warning("Refresh token is missing in the request")
                return Response(
                    {"detail": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST
                )

            token = RefreshToken(refresh_token)

            # Ensure the token belongs to the authenticated user
            if token["user_id"] != request.user.id:
                logger.warning(
                    f"User {request.user.id} attempted to log out with a token not belonging to them"
                )
                return Response(
                    {"detail": "An error occurred while logging out."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            token.blacklist()

            logger.info(f"User {request.user.id} logged out successfully.")
            return Response({"detail": "Logout successful"}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Failed to log out user: {str(e)}")
            return Response(
                {"detail": "An error occurred while logging out."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(tags=["Profile and User Management"])
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


@extend_schema(tags=["User Responses"])
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


@extend_schema(tags=["Recordings"])
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
            logger.error(f"Failed to upload audio: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    @staticmethod
    def _sanitize_filename(filename):
        """
        Sanitize the filename by removing special characters that may not be safe in S3 keys.
        """
        return "".join(
            char for char in filename if char.isalnum() or char in (" ", ".", "_")
        ).strip()


@extend_schema(tags=["Recordings"])
class UpdateTranscriptView(APIView):
    permission_classes = [IsRecordingOwner]

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


@extend_schema(tags=["Recordings"])
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


@extend_schema(tags=["Recordings"])
class DeleteRecordingView(APIView):
    permission_classes = [IsRecordingOwner]

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
            logger.warning(
                f"User {instructor.id} attempted to delete recording {recording.id} without permission"
            )
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


@extend_schema(tags=["Recordings"])
class GetTranscriptView(APIView):
    permission_classes = [IsRecordingOwner]

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
        tags=["Authentication Endpoint"],
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

            logger.info(f"User {user.id} logged in with Google.")
            return Response(result, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {"message": f"Invalid token: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class JWTGoogleLogin(APIView):
    permission_classes = [AllowAny]
    serializer_class = GoogleLoginRequestSerializer

    @extend_schema(tags=["Authentication Endpoint"], request=GoogleLoginRequestSerializer)
    def post(self, request):
        token = request.data.get("token")

        if not token:
            return Response({"message": "Token not provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
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
                    status=status.HTTP_403_FORBIDDEN,
                )

            refresh = RefreshToken.for_user(user)

            response = {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": user.id,
            }

            if hasattr(user, "instructor"):
                response["instructor"] = user.instructor.id

            logger.info(f"User {user.id} logged in with Google.")
            return JsonResponse(response, status=status.HTTP_200_OK)

        except ValueError as e:
            logger.error(f"Invalid token: {str(e)}")
            return Response(
                {"message": "Google login failed."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ContactPageThrottle(UserRateThrottle):
    rate = "10/hour"


@extend_schema(tags=["Contact and Support"])
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


@extend_schema(tags=["Authentication Endpoint"])
class DeleteUserView(APIView):
    def delete(self, request):
        id = request.user.id
        user = get_object_or_404(User, id=id)
        logger.info(f"User {id} requested to delete their account")
        if hasattr(user, "instructor"):
            boto3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME,
            )
            bucket_name = settings.AWS_STORAGE_BUCKET_NAME

            target_folder = "user_" + str(user.id) + "/"

            try:
                objects_to_delete = boto3_client.list_objects_v2(
                    Bucket=bucket_name, Prefix=target_folder
                )
                if "Contents" in objects_to_delete:
                    delete_keys = [{"Key": obj["Key"]} for obj in objects_to_delete["Contents"]]
                    boto3_client.delete_objects(Bucket=bucket_name, Delete={"Objects": delete_keys})
            except Exception as e:
                logger.error(f"Failed to delete user files for user {user.id} with error: {str(e)}")

        try:
            with transaction.atomic():
                user.delete()
        except Exception as e:
            logger.error(f"Failed to delete user {user.id} with error: {str(e)}")
            return JsonResponse(
                {"error": f"Failed to delete user: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        logger.info(f"User {id} deleted their account")
        return JsonResponse(
            {"message": "User and associated files deleted successfully"}, status=status.HTTP_200_OK
        )


@extend_schema(tags=["Recordings"])
class QuizByRecordingView(APIView):
    permission_classes = [IsRecordingOwner]

    @extend_schema(
        operation_id="get_quizzes_by_recording",
        summary="Get quizzes by recording ID",
        description="Returns all quizzes associated with a specific recording ID.",
        responses={
            200: QuizSerializer(many=True),
            403: OpenApiTypes.OBJECT,
        },
    )
    def get(self, request, recording_id):
        current_user = request.user

        # Check if the user is an instructor
        if not hasattr(current_user, "instructor"):
            return Response(
                {"message": "You are not authorized to view this resource."},
                status=status.HTTP_403_FORBIDDEN,
            )

        instructor_id = current_user.instructor.id
        quizzes = Quiz.objects.filter(
            instructor_recording_id=recording_id, instructor_id=instructor_id
        )

        if not quizzes.exists():
            return Response([], status=status.HTTP_200_OK)

        serializer = QuizSerializer(quizzes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TokenVerificationView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        return Response({"message": "Token is valid"}, status=status.HTTP_200_OK)


@extend_schema(tags=["Quiz Scoring"])
class UpdateScoresView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="update_scores",
        summary="Update scores",
        description="Updates the scores for a particular session.",
        responses={
            200: ScoreQuizResponseSerializer,
            404: OpenApiTypes.OBJECT,
        },
    )
    def post(self, request, session_id):
        score_session(session_id)
        return Response({"message": "Quiz scored successfully"}, status=status.HTTP_200_OK)


@extend_schema(tags=["Quiz Scoring"])
class GetStudentScoreForSession(APIView):
    @extend_schema(
        operation_id="get_score_by_id",
        summary="Get score by ID",
        description="Returns the score of a student for a particular session.",
        request=GetScoreRequestSerializer,
        responses={
            200: GetScoreResponseSerializer,
            404: OpenApiTypes.OBJECT,
        },
    )
    def get(self, request, student_id, session_id):
        student = get_object_or_404(QuizSessionStudent, id=student_id, quiz_session_id=session_id)
        return JsonResponse({"score": student.score}, status=status.HTTP_200_OK)
