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
    CourseCreationSerializer,
)
from drf_spectacular.utils import extend_schema, OpenApiResponse

from api.permissions import AllowInstructor, IsCourseOwner, IsEnrolledInCourse


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
        data = InstructorRecordingsSerializer(recordings, many=True).data

        for recording in data:
            recording["transcript"] = "completed" if recording.get("transcript") else "pending"
        return Response(data, status=status.HTTP_200_OK)


@extend_schema(tags=["Instructor Course Management"])
class GetCourseByCourseID(APIView):
    permission_classes = None

    def get(self, course_id):
        pass


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


@extend_schema(tags=["Instructor Course Management"])
class CreateCourse(APIView):
    permission_classes = [AllowInstructor]

    @extend_schema(
        request=CourseCreationSerializer(),
        responses={
            201: CourseSerializer,
            400: OpenApiResponse(description="Bad Request"),
            401: OpenApiResponse(description="Unauthorized"),
        },
    )
    def post(self, request):
        instructor = request.user.instructor
        serializer = CourseCreationSerializer(data=request.data, context={"instructor": instructor})
        if serializer.is_valid():
            course = serializer.save()
            course.save()
            return Response(CourseSerializer(course).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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


@extend_schema(tags=["Summaries"])
class FetchPublishedSummariesView(APIView):
    permission_classes = [IsEnrolledInCourse]

    @extend_schema(
        description="Endpoint for students to get published summaries given course id that they are in"
    )
    def get(self, request, course_id):
        summaries = LectureSummary.objects.filter(course=course_id, published=True)
        return Response(
            LectureSummarySerializer(summaries, many=True).data, status=status.HTTP_200_OK
        )
