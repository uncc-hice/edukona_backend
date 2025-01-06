from django.test import TestCase
from api.models import (
    Course,
    Instructor,
    User,
    Quiz,
    LectureSummary,
    InstructorRecordings,
    Student,
    CourseStudent,
)
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from datetime import timedelta


class BaseCourseTest(TestCase):
    def setUp(self):
        # Create Instructor User
        self.user_instructor = User.objects.create_user(
            username="test@gmail.com",
            email="test@gmail.com",
            password="password",
            first_name="Test",
            last_name="Instructor",
        )
        self.instructor = Instructor.objects.create(user=self.user_instructor)

        # create secondary instructor
        self.new_user_instructor = User.objects.create_user(
            username="test_two@gmail.com",
            email="test_two@gmail.com",
            password="password",
            first_name="Test",
            last_name="Instructor",
        )
        self.instructor_two = Instructor.objects.create(user=self.new_user_instructor)

        # create course and assign it to first instructor
        self.course = Course.objects.create(
            title="Example Course",
            instructor=self.instructor,
            description="A course used for tests.",
        )

        self.course.code = self.course.generate_code()
        self.course.save()

        # create instructor clients
        instructor_token_1, _ = Token.objects.get_or_create(user=self.user_instructor)
        self.client_instructor_1 = APIClient()
        self.client_instructor_1.credentials(HTTP_AUTHORIZATION="Token " + instructor_token_1.key)

        instructor_token_2, _ = Token.objects.get_or_create(user=self.new_user_instructor)
        self.client_instructor_2 = APIClient()
        self.client_instructor_2.credentials(HTTP_AUTHORIZATION="Token " + instructor_token_2.key)

        # Create Student User
        self.user_student_1 = User.objects.create_user(
            username="student@gmail.com",
            email="student@gmail.com",
            password="password",
            first_name="Student",
            last_name="User",
        )
        self.student_1 = Student.objects.create(user=self.user_student_1)

        # create secondary student
        self.user_student_2 = User.objects.create_user(
            username="student2@gmail.com",
            email="student2@gmail.com",
            password="password2",
            first_name="Student2",
            last_name="User2",
        )
        self.student_2 = Student.objects.create(user=self.user_student_2)

        # Create Student clients
        student_token_1, _ = Token.objects.get_or_create(user=self.user_student_1)
        self.client_student_1 = APIClient()
        self.client_student_1.credentials(HTTP_AUTHORIZATION="Token " + student_token_1.key)

        student_token_2, _ = Token.objects.get_or_create(user=self.user_student_2)
        self.client_student_2 = APIClient()
        self.client_student_2.credentials(HTTP_AUTHORIZATION="Token " + student_token_2.key)

        # Create StudentCourse Object
        self.course_student = CourseStudent.objects.create(
            course=self.course, student=self.student_1
        )


class CourseModelTests(BaseCourseTest):
    def test_generate_course_code(self):
        self.assertEqual(self.course.code, "TInstructorExample-Course")

    def test_non_unique_course_code(self):
        # Will collide since code has already been generated for this course
        new_course_code = self.course.generate_code()
        pattern = r".-[0-9a-f]{2}"
        self.assertRegex(new_course_code, pattern)

    def test_create_course_recording(self):
        recording1 = InstructorRecordings.objects.create(
            instructor=self.instructor, title="test 1", course=self.course, published=True
        )
        recording2 = InstructorRecordings.objects.create(
            instructor=self.instructor, title="test 2", course=self.course
        )
        retrieved1 = InstructorRecordings.objects.filter(id=recording1.id).first()
        retrieved2 = InstructorRecordings.objects.filter(id=recording2.id).first()
        self.assertEqual(retrieved1.course, self.course)
        self.assertEqual(retrieved2.course, self.course)
        self.assertEqual(retrieved1.published, True)
        self.assertEqual(retrieved2.published, False)
        self.assertEqual(InstructorRecordings.objects.filter(course=self.course).count(), 2)

    def test_create_course_lec_summary(self):
        recording = InstructorRecordings.objects.create(
            instructor=self.instructor, title="test", course=self.course
        )
        summary1 = LectureSummary.objects.create(
            recording=recording, course=self.course, published=True
        )
        summary2 = LectureSummary.objects.create(recording=recording, course=self.course)
        retrieved1 = LectureSummary.objects.filter(id=summary1.id).first()
        retrieved2 = LectureSummary.objects.filter(id=summary2.id).first()
        self.assertEqual(retrieved1.course, self.course)
        self.assertEqual(retrieved2.course, self.course)
        self.assertEqual(retrieved1.published, True)
        self.assertEqual(retrieved2.published, False)
        self.assertEqual(LectureSummary.objects.filter(course=self.course).count(), 2)

    def test_create_course_quiz(self):
        quiz1 = Quiz.objects.create(
            instructor=self.instructor, title="test", course=self.course, published=True
        )
        quiz2 = Quiz.objects.create(instructor=self.instructor, title="test", course=self.course)
        retrieved1 = Quiz.objects.filter(id=quiz1.id).first()
        retrieved2 = Quiz.objects.filter(id=quiz2.id).first()
        self.assertEqual(retrieved1.course, self.course)
        self.assertEqual(retrieved2.course, self.course)
        self.assertEqual(retrieved1.published, True)
        self.assertEqual(retrieved2.published, False)
        self.assertEqual(Quiz.objects.filter(course=self.course).count(), 2)


class FetchQuizzesByCourseTests(BaseCourseTest):
    def setUp(self):
        super().setUp()

        self.quiz1 = Quiz.objects.create(
            instructor=self.instructor, title="Quiz Oldest", course=self.course, published=True
        )
        self.quiz2 = Quiz.objects.create(
            instructor=self.instructor, title="Quiz Newest", course=self.course
        )
        self.quiz2.created_at = self.quiz1.created_at + timedelta(days=1)
        self.quiz2.save()
        self.url = reverse("quizzes-by-course", kwargs={"course_id": self.course.id})

    def test_instructor_can_fetch_all_quizzes(self):
        # fetch with instructor added to course
        response = self.client_instructor_1.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        quizzes = response_data["quizzes"]

        self.assertEqual(quizzes[0]["title"], "Quiz Newest")
        self.assertEqual(quizzes[1]["title"], "Quiz Oldest")

        self.assertEqual(len(quizzes), 2)

    def test_student_can_fetch_published_quizzes(self):
        # test with student added to course
        response = self.client_student_1.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        quizzes = response_data["quizzes"]
        self.assertEqual(len(quizzes), 1)
        # Only oldest should show since its the only published one
        self.assertEqual(quizzes[0]["title"], "Quiz Oldest")

    def test_non_member_cannot_fetch_quizzes(self):
        response = self.client_student_2.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_instructor_cannot_fetch_quizzes_for_unowned_course(self):
        # Test with unowned course
        response = self.client_instructor_2.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_response_structure(self):
        response = self.client_instructor_1.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        quizzes = response_data["quizzes"]
        expected_keys = {
            "id",
            "title",
            "start_time",
            "end_time",
            "settings",
            "instructor_recording",
            "created_at",
            "num_questions",
            "num_sessions",
        }
        for quiz in quizzes:
            self.assertTrue(expected_keys.issubset(quiz.keys()))
