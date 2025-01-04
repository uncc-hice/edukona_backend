from rest_framework.views import APIView
from api.models import InstructorRecordings
from rest_framework import status
from rest_framework.response import Response
from api.serializers import InstructorRecordingsSerializer
from drf_spectacular.utils import extend_schema, OpenApiResponse

from api.permissions import AllowInstructor, IsCourseOwner


class GetRecordingsByCourse(APIView):
    permission_classes = [AllowInstructor & IsCourseOwner]

    @extend_schema(
        responses={
            200: InstructorRecordingsSerializer(many=True),
            400: OpenApiResponse(description="Bad Request"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Course not found"),
        }
    )
    def get(self, request, course_id):
        recordings = InstructorRecordings.objects.filter(course=course_id).order_by("-uploaded_at")
        return Response(
            InstructorRecordingsSerializer(recordings, many=True).data, status=status.HTTP_200_OK
        )
