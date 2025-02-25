from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, PolymorphicProxySerializer, inline_serializer
from rest_framework import status, serializers

from api.serializers import (
    InstructorRecordingsSerializer,
    RecordingTitleUpdateSerializer,
    RecordingDurationUpdateSerializer,
    QuizTypedSerializer,
    LectureSummaryTypedSerializer,
    QuizAndSummarySerializer,
    UpdateRecordingCourseSerializer,
)
from django.conf import settings
from django.shortcuts import get_object_or_404
from itertools import chain
from django.db.models import CharField, Value


from api.models import Instructor, InstructorRecordings, Quiz, LectureSummary
import boto3
import json

from ..permissions import IsRecordingOwner


@extend_schema(tags=["Authentication Endpoint"])
class GenerateTemporaryCredentialsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        user_id = str(user.id)
        folder = f"user_{user_id}"

        # Initialize STS client
        sts_client = boto3.client(
            "sts",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )

        # Define session policy to restrict access to the user's folder
        session_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AllowS3UserFolderWrite",
                    "Effect": "Allow",
                    "Action": ["s3:PutObject", "s3:PutObjectAcl"],
                    "Resource": f"arn:aws:s3:::{settings.AWS_STORAGE_BUCKET_NAME}/{folder}/*",
                }
            ],
        }

        try:
            # Assume the role with the session policy
            assumed_role = sts_client.assume_role(
                RoleArn=settings.AWS_ROLE_ARN,  # ARN of the IAM role to assume
                RoleSessionName=f"upload-session-{user_id}",
                Policy=json.dumps(session_policy),
                DurationSeconds=900,  # Valid for 15 minutes
            )

            # Extract temporary credentials
            credentials = assumed_role["Credentials"]

            # Return the credentials and additional info to the frontend
            return Response(
                {
                    "AccessKeyId": credentials["AccessKeyId"],
                    "SecretAccessKey": credentials["SecretAccessKey"],
                    "SessionToken": credentials["SessionToken"],
                    "Expiration": credentials["Expiration"],
                    "Region": settings.AWS_S3_REGION_NAME,
                    "BucketName": settings.AWS_STORAGE_BUCKET_NAME,
                    "Folder": folder,
                }
            )
        except Exception as e:
            return Response({"error": str(e)}, status=500)


@extend_schema(tags=["Recordings"])
class UpdateRecordingTitleView(APIView):
    permission_classes = [IsRecordingOwner]

    @extend_schema(
        request=RecordingTitleUpdateSerializer,
        description="Endpoint to update the title of a recording",
    )
    def patch(self, request, recording_id):
        recording = get_object_or_404(InstructorRecordings, id=recording_id)

        # Pass request data to the serializer for validation
        serializer = RecordingTitleUpdateSerializer(data=request.data)

        if serializer.is_valid():
            # If valid, update the recording title
            recording.title = serializer.validated_data["title"]
            recording.save()
            return Response(
                {"message": "Title updated successfully", "title": recording.title},
                status=status.HTTP_200_OK,
            )

        # If not valid, return validation errors
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["Recordings"])
class UpdateRecordingDurationView(APIView):
    permission_classes = [IsRecordingOwner]

    @extend_schema(
        request=RecordingDurationUpdateSerializer,
        description="Endpoint too update the duration of the recording",
    )
    def patch(self, request, recording_id):
        recording = InstructorRecordings.objects.get(id=recording_id)

        serializer = RecordingDurationUpdateSerializer(data=request.data)

        if serializer.is_valid():
            # If valid, update the recording title
            recording.duration = serializer.validated_data["duration"]
            recording.save()
            return Response(
                {"message": "Duration updated successfully", "duration": recording.duration},
                status=status.HTTP_200_OK,
            )

        # If not valid, return validation errors
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["Recordings"])
class CreateRecordingView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="create_recording",
        summary="Create a new recording entry",
        description="Creates a new InstructorRecordings entry in the database with the provided S3 key and metadata.",
        request=InstructorRecordingsSerializer,
        responses={
            201: InstructorRecordingsSerializer,
            400: "Bad Request",
            401: "Unauthorized",
        },
    )
    def post(self, request):
        instructor = get_object_or_404(Instructor, user=request.user)
        data = request.data.copy()
        data["instructor"] = instructor.id  # Add the instructor ID to the data

        serializer = InstructorRecordingsSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            new_recording = serializer.instance  # Get the newly created recording instance

            # Invoke the Lambda function asynchronously
            try:
                lambda_client = boto3.client(
                    "lambda",
                    aws_access_key_id=settings.AWS_LAMBDA_INVOKER_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_LAMBDA_INVOKER_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_LAMBDA_INVOKER_REGION_NAME,
                )

                # Extract the token from the Authorization header
                token = jwt_token = None
                if "Authorization" in request.headers:
                    if request.headers["Authorization"].startswith("Bearer "):
                        jwt_token = request.headers["Authorization"].split()[1]
                    else:
                        token = request.headers["Authorization"].split()[1]

                # Prepare the payload for the Lambda function
                payload = {
                    "s3_key": new_recording.s3_path,
                    "token": token,
                    "jwt_token": jwt_token,
                    "recording_id": str(new_recording.id),
                }

                # Invoke the Lambda function asynchronously
                lambda_client.invoke(
                    FunctionName="TranscribeAudio",  # Replace with your Lambda function name
                    InvocationType="Event",  # Asynchronous invocation
                    Payload=json.dumps(payload),
                )
            except Exception as e:
                # Handle Lambda invocation errors if necessary
                return Response(
                    {"error": f"Recording saved, but failed to invoke Lambda: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["Recordings"])
class GetQuizzesAndSummaries(APIView):
    permission_classes = [IsRecordingOwner]

    @extend_schema(
        operation_id="get-quizzes-and-summaries",
        summary="Get quizzes and summaries in chronological order.",
        description="Returns all quizzes and summaries associated with a specific recording ID.",
        responses={
            200: PolymorphicProxySerializer(
                component_name="QuizzesAndSummaries",
                serializers=[QuizTypedSerializer, LectureSummaryTypedSerializer],
                resource_type_field_name="type",
                many=True,
            ),
            401: inline_serializer("detail_response", {"detail": serializers.CharField()}),
            403: inline_serializer("detail_response", {"detail": serializers.CharField()}),
        },
    )
    def get(self, request, recording_id):

        quizzes = Quiz.objects.filter(instructor_recording_id=recording_id).annotate(
            type=Value("quiz", output_field=CharField())
        )
        summaries = LectureSummary.objects.filter(recording_id=recording_id).annotate(
            type=Value("summary", output_field=CharField())
        )

        data = sorted(chain(quizzes, summaries), key=lambda obj: obj.created_at, reverse=True)
        serializer = QuizAndSummarySerializer(data, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["Recordings"])
class UpdateRecordingCourse(APIView):
    permission_classes = [IsRecordingOwner]

    @extend_schema(
        request=UpdateRecordingCourseSerializer,
        description="Endpoint to update the course of a recording",
        responses={
            200: InstructorRecordingsSerializer,
            400: "Bad Request",
            401: "Unauthorized",
        },
    )
    def patch(self, request, recording_id):
        recording = get_object_or_404(InstructorRecordings, id=recording_id)
        serializer = UpdateRecordingCourseSerializer(data=request.data)

        if serializer.is_valid():
            validated_data = serializer.validated_data
            recording.course_id = validated_data["course_id"]
            recording.save()
            updated_recording_serializer = InstructorRecordingsSerializer(recording)
            return Response(
                updated_recording_serializer.data,
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
