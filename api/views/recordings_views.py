from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
import boto3
import json


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
