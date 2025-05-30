from rest_framework import permissions
from .models import (
    Instructor,
    Quiz,
    QuestionMultipleChoice,
    InstructorRecordings,
    QuizSession,
    LectureSummary,
    Course,
    CourseStudent,
    Student,
)
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned, FieldError
from django.shortcuts import get_object_or_404


class AllowInstructor(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        return Instructor.objects.filter(user=request.user).exists()


class IsOwnerOfAllQuizzes(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Ensure request data is parsed
        if not hasattr(request, "data"):
            return False

        if not isinstance(request.data, list):
            return False  # Expected a list of questions

        quiz_ids = set()
        for question_data in request.data:
            quiz_id = question_data.get("quiz_id")
            if not quiz_id:
                return False  # 'quiz_id' is required
            quiz_ids.add(quiz_id)

        quizzes = Quiz.objects.filter(id__in=quiz_ids)
        if quizzes.count() != len(quiz_ids):
            return False  # One or more quizzes do not exist

        for quiz in quizzes:
            if request.user != quiz.instructor.user:
                return False  # User does not own all quizzes

        return True


class IsQuizOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        quiz_id = view.kwargs.get("quiz_id")
        if not quiz_id:
            quiz_id = request.data.get("quiz_id")

        try:
            quiz = Quiz.objects.get(id=quiz_id)
        except (ObjectDoesNotExist, MultipleObjectsReturned, FieldError):
            return False
        return request.user == quiz.instructor.user


class IsQuestionOwner(AllowInstructor):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        question_id = view.kwargs.get("question_id")
        if not question_id:
            question_id = request.data.get("question_id")

        try:
            question = QuestionMultipleChoice.objects.get(id=question_id)
        except (ObjectDoesNotExist, MultipleObjectsReturned, FieldError):
            return False
        return request.user.id == question.quiz.instructor.user.id


class IsRecordingOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Get recording_id from path parameters
        recording_id = view.kwargs.get("recording_id")

        if recording_id is None:
            recording_id = request.data.get("recording_id")

        try:
            recording = InstructorRecordings.objects.get(id=recording_id)
        except (ObjectDoesNotExist, MultipleObjectsReturned, FieldError):
            return False
        return request.user == recording.instructor.user


class IsSessionOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Get recording_id from path parameters
        session_code = view.kwargs.get("code")

        try:
            session = QuizSession.objects.get(code=session_code)
        except (ObjectDoesNotExist, MultipleObjectsReturned, FieldError):
            return False
        return request.user == session.quiz.instructor.user


class IsSummaryOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Get summary_id from the URL
        summary_id = view.kwargs.get("summary_id")

        try:
            # Retrieve the LectureSummary and verify the ownership of the recording
            summary = get_object_or_404(LectureSummary, id=summary_id)
        except (ObjectDoesNotExist, MultipleObjectsReturned, FieldError):
            return False
        return request.user == summary.recording.instructor.user


class IsCourseOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        course_id = view.kwargs.get("course_id")

        try:
            course = get_object_or_404(Course, id=course_id)
        except (ObjectDoesNotExist, MultipleObjectsReturned, FieldError):
            return False
        return request.user == course.instructor.user


class IsEnrolledInCourse(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        course_id = view.kwargs.get("course_id")

        course = get_object_or_404(Course, id=course_id)

        try:
            if hasattr(request.user, "student"):
                is_member = CourseStudent.objects.filter(
                    course=course, student=request.user.student
                ).exists()
                return is_member
        except (ObjectDoesNotExist, MultipleObjectsReturned, FieldError):
            return False


class AllowStudent(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        return Student.objects.filter(user=request.user).exists()
