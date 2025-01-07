from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase
from api.models import Course, Instructor, User, Quiz, LectureSummary, InstructorRecordings
from django.urls import reverse


class BaseCourseTest(APITestCase):
    def setUp(self):
        # Create Instructor User
        self.user = User.objects.create_user(
            username="test@gmail.com",
            email="test@gmail.com",
            password="password",
            first_name="Test",
            last_name="Instructor",
        )

        self.instructor = Instructor.objects.create(user=self.user)

        self.course = Course.objects.create(
            title="Example Course",
            instructor=self.instructor,
            description="A course used for tests.",
        )

        self.course.code = self.course.generate_code()
        self.course.save()


class CourseViewsTest(BaseCourseTest):
    def setUp(self):
        super().setUp()
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

        self.alt_course.code = self.alt_course.generate_code()
        self.alt_course.save()

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
