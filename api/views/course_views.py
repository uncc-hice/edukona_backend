from rest_framework.views import APIView
from api.models import InstructorRecordings, Course, LectureSummary, CourseStudent
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from api.serializers import (
    InstructorRecordingsSerializer,
    CourseSerializer,
    LectureSummarySerializer,
    CourseStudentSerializer,
    Student,
)
from drf_spectacular.utils import extend_schema, OpenApiResponse

from api.permissions import AllowInstructor, IsCourseOwner


@extend_schema(tags=["Instructor Course Management"])
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
        recordings = InstructorRecordings.objects.filter(
            instructor=request.user.instructor, course=course_id
        ).order_by("-uploaded_at")
        return Response(
            InstructorRecordingsSerializer(recordings, many=True).data, status=status.HTTP_200_OK
        )


@extend_schema(tags=["Instructor Course Management"])
class GetCoursesByInstructor(APIView):
    permission_classes = [AllowInstructor]

    @extend_schema(
        responses={
            200: CourseSerializer(many=True),
            401: OpenApiResponse(description="Unauthorized"),
        }
    )
    def get(self, request):
        courses = Course.objects.filter(instructor=request.user.instructor).order_by("-created_at")
        return Response(CourseSerializer(courses, many=True).data, status=status.HTTP_200_OK)


@extend_schema(tags=["Instructor Course Management"])
class GetSummariesByCourse(APIView):
    permission_classes = [AllowInstructor & IsCourseOwner]

    @extend_schema(
        responses={
            200: LectureSummarySerializer(many=True),
            400: OpenApiResponse(description="Bad Request"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Course not found"),
        }
    )
    def get(self, request, course_id):
        summaries = LectureSummary.objects.filter(course=course_id)
        return Response(
            LectureSummarySerializer(summaries, many=True).data, status=status.HTTP_200_OK
        )


@extend_schema(tags=["Instructor Course Management"])
class GetStudentsByCourse(APIView):
    permission_classes = [AllowInstructor & IsCourseOwner]

    @extend_schema(
        responses={
            200: CourseStudentSerializer(many=True),
            400: OpenApiResponse(description="Bad Request"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Course not found"),
        }
    )
    def get(self, request, course_id):
        course_students = CourseStudent.objects.filter(course=course_id).order_by(
            "student__user__last_name"
        )
        students = [
            {
                "first_name": s.student.user.first_name,
                "last_name": s.student.user.last_name,
                "email": s.student.user.email,
                "joined_at": s.joined_at,
            }
            for s in course_students
        ]
        return Response(
            CourseStudentSerializer(students, many=True).data, status=status.HTTP_200_OK
        )


@extend_schema(tags=["Student Course Management"])
class GetCoursesByStudent(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: CourseSerializer(many=True),
            401: OpenApiResponse(description="Unauthorized"),
        }
    )
    def get(self, request):
        student_courses = CourseStudent.objects.filter(student__user=request.user).order_by(
            "-joined_at"
        )
        courses = [sc.course for sc in student_courses]
        return Response(CourseSerializer(courses, many=True).data, status=status.HTTP_200_OK)
