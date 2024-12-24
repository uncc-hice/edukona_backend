from django.test import TestCase
from api.models import Course, Instructor, User


class CourseModelTests(TestCase):
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

    def test_generate_course_code(self):
        self.assertEqual(self.course.code, "TInstructorExample-Course")

    def test_non_unique_course_code(self):
        # Will collide since code has already been generated for this course
        new_course_code = self.course.generate_code()
        pattern = r".-[0-9a-f]{2}"
        self.assertRegex(new_course_code, pattern)
