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
from datetime import timedelta
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase


class BaseCourseTest(APITestCase):
    def setUp(self):
        # Create Instructor User
        self.user_instructor = User.objects.create_user(
            username="test_one@gmail.com",
            email="test_one@gmail.com",
            password="password",
            first_name="TestFirst",
            last_name="Instructor",
        )
        self.instructor = Instructor.objects.create(user=self.user_instructor)

        # create secondary instructor
        self.new_user_instructor = User.objects.create_user(
            username="test_two@gmail.com",
            email="test_two@gmail.com",
            password="password",
            first_name="Test Two",
            last_name="Instructor",
        )
        self.instructor_two = Instructor.objects.create(user=self.new_user_instructor)

        # create course and assign it to first instructor
        self.course = Course.objects.create(
            title="Example Course",
            instructor=self.instructor,
            description="A course used for tests.",
        )

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


class CourseViewsTest(BaseCourseTest):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="test@gmail.com",
            email="test@gmail.com",
            password="password",
            first_name="Test",
            last_name="Instructor",
        )

        self.instructor = Instructor.objects.create(user=self.user)

        self.course.instructor = self.instructor
        self.course.save()

        # Create an alternative Instructor User
        self.alt_user = User.objects.create_user(
            username="secondtest@gmail.com",
            email="secondtest@gmail.com",
            password="password",
            first_name="Second",
            last_name="Instructor",
        )
        self.alt_instructor = Instructor.objects.create(user=self.alt_user)

        self.alt_course = Course.objects.create(
            title="Example Course",
            instructor=self.alt_instructor,
            description="A course used for tests.",
        )

        # Setup instructor client
        self.prim_instructor_token = Token.objects.create(user=self.user)
        self.prim_instructor_client = APIClient()
        self.prim_instructor_client.credentials(
            HTTP_AUTHORIZATION="Token " + self.prim_instructor_token.key
        )

        # Setup alternative instructor client
        self.alt_instructor_token = Token.objects.create(user=self.alt_user)
        self.alt_instructor_client = APIClient()
        self.alt_instructor_client.credentials(
            HTTP_AUTHORIZATION="Token " + self.alt_instructor_token.key
        )

        # Add recordings to primary course
        self.prim_recordings = [
            InstructorRecordings.objects.create(
                instructor=self.instructor, title=f"prim-{x}", course=self.course
            )
            for x in range(5)
        ]

        # Add recordings to alternative course
        self.alt_recordings = [
            InstructorRecordings.objects.create(
                instructor=self.alt_instructor, title=f"alt-{x}", course=self.alt_course
            )
            for x in range(7)
        ]


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

        quizzes = response.json()

        self.assertEqual(quizzes[0]["title"], "Quiz Newest")
        self.assertEqual(quizzes[1]["title"], "Quiz Oldest")

        self.assertEqual(len(quizzes), 2)

    def test_student_can_fetch_published_quizzes(self):
        # test with student added to course
        response = self.client_student_1.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        quizzes = response.json()
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

        quizzes = response.json()
        expected_keys = {
            "id",
            "title",
            "start_time",
            "end_time",
            "timer",
            "live_bar_chart",
            "skip_question",
            "skip_count_per_student",
            "skip_question_logic",
            "skip_question_streak_count",
            "skip_question_percentage",
            "instructor_recording",
            "created_at",
            "num_questions",
            "num_sessions",
        }
        for quiz in quizzes:
            self.assertTrue(expected_keys.issubset(quiz.keys()))


class CourseRecordingsTests(CourseViewsTest):
    def setUp(self):
        super().setUp()
        self.prim_url = reverse("get-course-recordings", kwargs={"course_id": self.course.id})
        self.alt_url = reverse("get-course-recordings", kwargs={"course_id": self.alt_course.id})

    def test_get_recordings_by_course(self):
        prim_response = self.prim_instructor_client.get(self.prim_url)
        alt_response = self.alt_instructor_client.get(self.alt_url)
        prim_data = prim_response.json()
        alt_data = alt_response.json()

        self.assertEqual(prim_response.status_code, 200)
        self.assertEqual(alt_response.status_code, 200)
        self.assertEqual(len(prim_data), 5)
        self.assertEqual(len(alt_data), 7)

    def test_get_recordings_sorted(self):
        prim_response = self.prim_instructor_client.get(self.prim_url)
        alt_response = self.alt_instructor_client.get(self.alt_url)
        prim_data = prim_response.json()
        alt_data = alt_response.json()

        self.assertEqual(prim_data[0]["id"], self.prim_recordings[-1].id.__str__())
        self.assertEqual(alt_data[0]["id"], self.alt_recordings[-1].id.__str__())

    def test_get_recordings_unauthorized(self):
        tmp_client = APIClient()
        prim_response = tmp_client.get(self.prim_url)
        alt_response = tmp_client.get(self.alt_url)

        self.assertEqual(prim_response.status_code, 401)
        self.assertEqual(alt_response.status_code, 401)

    def test_get_recordings_forbidden(self):
        # Attempt to get the courses of the other user
        prim_response = self.prim_instructor_client.get(self.alt_url)
        alt_response = self.alt_instructor_client.get(self.prim_url)

        self.assertEqual(prim_response.status_code, 403)
        self.assertEqual(alt_response.status_code, 403)


class InstructorCoursesTests(CourseViewsTest):
    def setUp(self):
        super().setUp()
        # Add 9 more courses for the primary instructor for a total of 10
        self.prim_courses = [
            Course.objects.create(instructor=self.instructor, title=f"Prim Course {x}")
            for x in range(9)
        ]

        # Add the existing course to the start of the list of courses
        self.prim_courses.insert(0, self.course)

        # Add 9 more courses for the alternative instructor for a toal of 10
        self.alt_courses = [
            Course.objects.create(instructor=self.alt_instructor, title=f"Alt Course {x}")
            for x in range(9)
        ]

        self.alt_courses.insert(0, self.alt_course)
        self.url = reverse("get-instructor-courses")

    def test_get_courses(self):
        prim_response = self.prim_instructor_client.get(self.url)
        alt_response = self.alt_instructor_client.get(self.url)
        prim_data = prim_response.json()
        alt_data = alt_response.json()

        self.assertEqual(prim_response.status_code, 200)
        self.assertEqual(alt_response.status_code, 200)
        self.assertEqual(len(prim_data), 10)
        self.assertEqual(len(alt_data), 10)

    def test_get_courses_sorted(self):
        prim_response = self.prim_instructor_client.get(self.url)
        alt_response = self.alt_instructor_client.get(self.url)
        prim_data = prim_response.json()
        alt_data = alt_response.json()

        self.assertEqual(prim_data[0]["id"], self.prim_courses[-1].id.__str__())
        self.assertEqual(alt_data[0]["id"], self.alt_courses[-1].id.__str__())

    def test_get_courses_unauthorized(self):
        tmp_client = APIClient()
        response = tmp_client.get(self.url)

        self.assertEqual(response.status_code, 401)


class CourseSummariesTests(CourseViewsTest):
    def setUp(self):
        super().setUp()
        self.prim_summary_course = Course.objects.create(
            instructor=self.instructor, title="primary course for summaries tests"
        )
        # Add a summary for each primary recording
        self.prim_summaries = [
            LectureSummary.objects.create(
                recording=recording, course=self.prim_summary_course, published=True
            )
            for recording in self.prim_recordings
        ]

        self.alt_summary_course = Course.objects.create(
            instructor=self.alt_instructor, title="alt course for summaries tests"
        )

        # Add a summary for each alternative recording
        self.alt_summaries = [
            LectureSummary.objects.create(
                recording=recording, course=self.alt_summary_course, published=True
            )
            for recording in self.alt_recordings
        ]

        self.prim_url = reverse(
            "get-instructor-course-summaries", kwargs={"course_id": self.prim_summary_course.id}
        )
        self.alt_url = reverse(
            "get-instructor-course-summaries", kwargs={"course_id": self.alt_summary_course.id}
        )

    def test_get_summaries(self):
        prim_response = self.prim_instructor_client.get(self.prim_url)
        alt_response = self.alt_instructor_client.get(self.alt_url)
        prim_data = prim_response.json()
        alt_data = alt_response.json()

        self.assertEqual(prim_response.status_code, 200)
        self.assertEqual(alt_response.status_code, 200)
        self.assertEqual(len(prim_data), len(self.prim_recordings))
        self.assertEqual(len(alt_data), len(self.alt_recordings))

    def test_get_summaries_sorted(self):
        prim_response = self.prim_instructor_client.get(self.prim_url)
        alt_response = self.alt_instructor_client.get(self.alt_url)
        prim_data = prim_response.json()
        alt_data = alt_response.json()

        self.assertEqual(prim_data[0]["id"], self.prim_summaries[-1].id.__str__())
        self.assertEqual(alt_data[0]["id"], self.alt_summaries[-1].id.__str__())

    def test_get_courses_unauthorized(self):
        tmp_client = APIClient()
        prim_response = tmp_client.get(self.prim_url)
        alt_response = tmp_client.get(self.alt_url)

        self.assertEqual(prim_response.status_code, 401)
        self.assertEqual(alt_response.status_code, 401)

    def test_get_courses_forbidden(self):
        prim_response = self.prim_instructor_client.get(self.alt_url)
        alt_response = self.alt_instructor_client.get(self.prim_url)

        self.assertEqual(prim_response.status_code, 403)
        self.assertEqual(alt_response.status_code, 403)
