from django.test import TestCase
from api.models import Course, Instructor, User, Quiz, LectureSummary, InstructorRecordings


class BaseCourseTest(TestCase):
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
        recording1.save()
        recording2.save()
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
        recording.save()
        summary1 = LectureSummary.objects.create(
            recording=recording, course=self.course, published=True
        )
        summary2 = LectureSummary.objects.create(recording=recording, course=self.course)
        summary1.save()
        summary2.save()
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
        quiz1.save()
        quiz2.save()
        retrieved1 = Quiz.objects.filter(id=quiz1.id).first()
        retrieved2 = Quiz.objects.filter(id=quiz2.id).first()
        self.assertEqual(retrieved1.course, self.course)
        self.assertEqual(retrieved2.course, self.course)
        self.assertEqual(retrieved1.published, True)
        self.assertEqual(retrieved2.published, False)
        self.assertEqual(Quiz.objects.filter(course=self.course).count(), 2)
