from unittest.mock import patch

from django.db import transaction
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from rest_framework import status
from api.models import *


# Create your tests here.


class BaseTest(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create Instructor User
        self.new_user_instructor = User.objects.create_user(
            username="test@gmail.com",
            email="test@gmail.com",
            password="password",
            first_name="Test",
            last_name="Instructor",
        )
        self.instructor = Instructor.objects.create(user=self.new_user_instructor)
        token, _ = Token.objects.get_or_create(user=self.new_user_instructor)
        self.client_instructor = APIClient()
        self.client_instructor.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        # Create Student User
        self.new_user_student = User.objects.create_user(
            username="student@gmail.com",
            email="student@gmail.com",
            password="password",
            first_name="Student",
            last_name="User",
        )
        self.student = Student.objects.create(user=self.new_user_student)
        token, _ = Token.objects.get_or_create(user=self.new_user_student)
        self.client_student = APIClient()
        self.client_student.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        # Create Quiz
        self.new_quiz = Quiz.objects.create(
            title="Test Quiz",
            instructor=self.instructor,
            start_time="2021-10-10T00:00:00Z",
            end_time="2021-10-10T00:00:00Z",
        )

        # Create Questions
        self.new_question = QuestionMultipleChoice.objects.create(
            question_text="What is 1+1?",
            incorrect_answer_list=["0", "1", "3"],
            correct_answer="2",
            points=1,
            quiz=self.new_quiz,
        )

        self.second_new_question = QuestionMultipleChoice.objects.create(
            question_text="What is 3 + 3?",
            incorrect_answer_list=["3", "4", "5"],
            correct_answer="6",
            points=5,
            quiz=self.new_quiz,
        )

        # Create Quiz Session
        self.new_quiz_session = QuizSession.objects.create(
            quiz=self.new_quiz, code=QuizSession.generate_unique_code(self)
        )

        # Create Quiz Session Student
        self.new_quiz_session_student = QuizSessionStudent.objects.create(
            quiz_session=self.new_quiz_session, username="test"
        )

        # Create User Response
        self.new_user_response = UserResponse.objects.create(
            student=self.new_quiz_session_student,
            question=self.new_question,
            quiz_session=self.new_quiz_session,
            selected_answer="2",
            is_correct=(self.new_question.correct_answer == "2"),
        )


class InstructorViewTest(BaseTest):
    def test_post_instructor(self):
        url = reverse("instructor-detail")
        data = {
            "user": {"username": "new_instructor", "password": "new_password"},
        }
        response = self.client_instructor.post(url, data, format="json")

        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(response_data["message"], "Instructor created successfully")

        new_instructor = Instructor.objects.get(id=response_data["instructor_id"])
        self.assertEqual(new_instructor.user.username, data["user"]["username"])

    def test_get_instructor(self):
        url = reverse(
            "instructor-detail",
            kwargs={"instructor_id": self.new_user_instructor.instructor.id},
        )
        response = self.client_instructor.get(url)

        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(response_data["instructor"]["id"], self.new_user_instructor.instructor.id)

    def test_put_instructor(self):
        url = reverse(
            "instructor-detail",
            kwargs={"instructor_id": self.new_user_instructor.instructor.id},
        )
        data = {
            "instructor": {},
            "user": {
                "username": "new_test@gmail.com",
            },
        }
        response = self.client_instructor.put(url, data, format="json")
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(response_data["message"], "Instructor updated successfully")

        new_instructor = Instructor.objects.get(id=self.new_user_instructor.instructor.id)
        self.assertEqual(new_instructor.user.username, data["user"]["username"])

    def test_delete_instructor(self):
        url = reverse(
            "instructor-detail",
            kwargs={"instructor_id": self.new_user_instructor.instructor.id},
        )
        response = self.client_instructor.delete(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Instructor deleted successfully")

        with self.assertRaises(Instructor.DoesNotExist):
            Instructor.objects.get(id=self.new_user_instructor.instructor.id)


class QuizViewTest(BaseTest):
    def test_get_quiz(self):
        url = reverse("quiz-detail", kwargs={"quiz_id": self.new_quiz.id})
        response = self.client_instructor.get(url)

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["quiz"]["id"], self.new_quiz.id)
        self.assertEqual(response_data["quiz"]["title"], self.new_quiz.title)
        self.assertEqual(response_data["quiz"]["instructor_id"], self.new_quiz.instructor.id)

    def test_put_quiz(self):
        url = reverse("quiz-detail", kwargs={"quiz_id": self.new_quiz.id})
        data = {
            "title": "Updated Quiz Title",
            "start_time": "2023-01-03T00:00:00Z",
            "end_time": "2023-01-04T00:00:00Z",
        }

        response = self.client_instructor.put(url, data, format="json")

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["message"], "Quiz updated successfully")

        updated_quiz = Quiz.objects.get(id=self.new_quiz.id)
        self.assertEqual(updated_quiz.title, data["title"])
        self.assertEqual(updated_quiz.start_time.isoformat(), "2023-01-03T00:00:00+00:00")
        self.assertEqual(updated_quiz.end_time.isoformat(), "2023-01-04T00:00:00+00:00")

    def test_delete_quiz(self):
        url = reverse("quiz-detail", kwargs={"quiz_id": self.new_quiz.id})
        response = self.client_instructor.delete(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Quiz deleted successfully")

        with self.assertRaises(Quiz.DoesNotExist):
            Quiz.objects.get(id=self.new_quiz.id)


class CreateQuizViewTest(BaseTest):
    def test_post_quiz(self):
        url = reverse("create-quiz")
        data = {
            "title": "Test Quiz",
            "instructor_id": self.new_user_instructor.instructor.id,
            "start_time": "2023-01-01T00:00:00Z",
            "end_time": "2023-01-02T00:00:00Z",
        }

        response = self.client_instructor.post(url, data, format="json")

        self.assertEqual(response.status_code, 201)
        response_data = response.json()
        self.assertEqual(response_data["message"], "Quiz created successfully")
        new_quiz = Quiz.objects.get(id=response_data["quiz_id"])
        self.assertEqual(new_quiz.title, data["title"])
        self.assertEqual(new_quiz.instructor.id, data["instructor_id"])


class InstructorQuizzesViewTest(BaseTest):
    def test_get_quizzes(self):
        url = reverse("instructor-quizzes")
        instructor_response = self.client_instructor.get(url)

        self.assertEqual(instructor_response.status_code, 200)


class QuestionViewTest(BaseTest):
    def test_get_question(self):
        url = reverse("question-detail", kwargs={"question_id": self.new_question.id})
        response = self.client_instructor.get(url)

        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(response_data["id"], self.new_question.id)
        self.assertEqual(response_data["question_text"], self.new_question.question_text)
        self.assertEqual(
            response_data["incorrect_answer_list"],
            self.new_question.incorrect_answer_list,
        )
        self.assertEqual(
            response_data["correct_answer"],
            self.new_question.correct_answer,
        )
        self.assertEqual(response_data["points"], self.new_question.points)
        self.assertEqual(response_data["quiz_id"], self.new_question.quiz.id)

    def test_get_all_questions(self):
        all_questions_url = reverse("all-questions", kwargs={"quiz_id": self.new_quiz.id})
        response = self.client_instructor.get(all_questions_url)

        self.assertEqual(response.status_code, 200)

        response_data = response.json()

        questions = response_data["questions"]
        self.assertTrue(len(questions) > 0)

        expected_questions = {
            self.new_question.id: {
                "question_text": self.new_question.question_text,
                "incorrect_answer_list": self.new_question.incorrect_answer_list,
                "correct_answer": self.new_question.correct_answer,
                "points": self.new_question.points,
                "quiz_id": self.new_question.quiz.id,
            },
            self.second_new_question.id: {
                "question_text": self.second_new_question.question_text,
                "incorrect_answer_list": self.second_new_question.incorrect_answer_list,
                "correct_answer": self.second_new_question.correct_answer,
                "points": self.second_new_question.points,
                "quiz_id": self.second_new_question.quiz.id,
            },
        }

        for question in questions:
            with self.subTest(question=question):
                self.assertIn(question["id"], expected_questions)

                expected = expected_questions[question["id"]]

                self.assertEqual(question["question_text"], expected["question_text"])
                self.assertEqual(
                    question["incorrect_answer_list"], expected["incorrect_answer_list"]
                )
                self.assertEqual(question["correct_answer"], expected["correct_answer"])
                self.assertEqual(question["points"], expected["points"])
                self.assertEqual(question["quiz_id"], expected["quiz_id"])

    def test_put_question(self):
        url = reverse("question-detail", kwargs={"question_id": self.new_question.id})
        data = {
            "question_text": "Updated Question Text",
            "incorrect_answer_list": ["B", "C", "D"],
            "correct_answer": "A",
            "points": 3,
            "quiz_id": self.new_quiz.id,
        }

        response = self.client_instructor.put(url, data, format="json")

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["message"], "Question updated successfully")

        updated_question = QuestionMultipleChoice.objects.get(id=self.new_question.id)
        self.assertEqual(updated_question.question_text, data["question_text"])
        self.assertEqual(updated_question.incorrect_answer_list, data["incorrect_answer_list"])
        self.assertEqual(updated_question.correct_answer, data["correct_answer"])
        self.assertEqual(updated_question.points, data["points"])
        self.assertEqual(updated_question.quiz.id, data["quiz_id"])

    def test_delete_question(self):
        url = reverse("question-detail", kwargs={"question_id": self.new_question.id})
        response = self.client_instructor.delete(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Question deleted successfully")

        with self.assertRaises(QuestionMultipleChoice.DoesNotExist):
            QuestionMultipleChoice.objects.get(id=self.new_question.id)


class UserResponseViewTest(BaseTest):
    def test_put_user_response(self):
        url = reverse("user-response-detail", kwargs={"response_id": self.new_user_response.id})
        data = {"student_id": self.new_quiz_session_student.id, "selected_answer": "1"}
        response = self.client.put(url, data, format="json")

        response_data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data["is_correct"], False)
        self.assertEqual(response_data["message"], "User response updated successfully")


class QuizSessionResultsTest(BaseTest):

    def test_quiz_session_results(self):

        instructor_token = Token.objects.get(user=self.new_user_instructor).key
        self.client.credentials(HTTP_AUTHORIZATION="Token " + instructor_token)

        response = self.client.get(
            reverse("quiz-session-results", kwargs={"code": self.new_quiz_session.code})
        )

        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["student_username"], self.new_quiz_session_student.username)
        self.assertEqual(results[0]["correct_answers"], 1)
        self.assertEqual(results[0]["total_questions"], 1)


class QuizSessionsByInstructorViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Create an instructor
        self.instructor_user = User.objects.create(
            username="instructor@example.com", password="securepassword"
        )
        self.instructor = Instructor.objects.create(user=self.instructor_user)
        self.token, _ = Token.objects.get_or_create(user=self.instructor_user)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token.key)

        # Create a quiz owned by the instructor
        self.quiz = Quiz.objects.create(title="Sample Quiz", instructor=self.instructor)

        # Create quiz sessions
        self.quiz_session1 = QuizSession.objects.create(quiz=self.quiz, code="ABC123")
        self.quiz_session2 = QuizSession.objects.create(quiz=self.quiz, code="XYZ789")

    def test_get_sessions_by_instructor(self):
        url = reverse("quiz-sessions-list")
        response = self.client.get(url)

        response_json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_json["quiz_sessions"]), 2)
        self.assertIn(self.quiz_session1.code, str(response.content))
        self.assertIn(self.quiz_session2.code, str(response.content))
        self.assertIn(self.quiz.title, str(response.content))


class LoginViewTest(BaseTest):

    def test_post_login(self):
        url = reverse("login")
        data = {"email": "bad_email", "password": "bad_password!"}
        response = self.client_student.post(url, data, format="json")
        self.assertEqual(response.status_code, 401)
        response_data = response.json()
        self.assertEqual(response_data["detail"], "Invalid email or password!")


class ContactPageViewTests(BaseTest):
    def setUp(self):
        super().setUp()  # Inherit from BaseTest
        # Define the URL for the contact page
        self.url = reverse("contact-us")  # Ensure that 'contact-us' is the name of your URL pattern

        # Sample valid data
        self.valid_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "message": "Hello, this is a test message.",
        }

    def test_post_contact_success(self):
        """
        Ensure that a POST request with all required fields creates a ContactMessage
        and returns a 200 OK response.
        """
        response = self.client.post(self.url, data=self.valid_data, format="json")

        # Check the response status
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Message sent successfully")

        # Check that the ContactMessage was created
        self.assertEqual(ContactMessage.objects.count(), 1)
        contact_message = ContactMessage.objects.first()
        self.assertEqual(contact_message.first_name, self.valid_data["first_name"])
        self.assertEqual(contact_message.last_name, self.valid_data["last_name"])
        self.assertEqual(contact_message.email, self.valid_data["email"])
        self.assertEqual(contact_message.message, self.valid_data["message"])

    def test_post_contact_missing_required_field(self):
        """
        Ensure that a POST request missing a required field (e.g., first_name) returns a 400 Bad Request.
        """
        data = self.valid_data.copy()
        del data["first_name"]  # Remove a required field

        response = self.client.post(self.url, data=data, format="json")

        # Check the response status
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Please provide all required fields")

        # Ensure no ContactMessage was created
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_post_contact_invalid_email(self):
        """
        Ensure that a POST request with an invalid email format returns a 400 Bad Request.
        """
        data = self.valid_data.copy()
        data["email"] = "invalid-email"  # Set to an invalid email format

        response = self.client.post(self.url, data=data, format="json")

        # Check the response status
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Invalid email format")

        # Ensure no ContactMessage was created
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_post_contact_optional_last_name_missing_or_blank(self):
        """
        Ensure that a POST request missing the optional last_name field or providing it as blank is handled correctly.
        """
        # Test case 1: Missing last_name
        data_missing_last_name = self.valid_data.copy()
        del data_missing_last_name["last_name"]

        response_missing = self.client.post(self.url, data=data_missing_last_name, format="json")

        # Check the response status for missing last_name
        self.assertEqual(response_missing.status_code, status.HTTP_200_OK)
        self.assertEqual(response_missing.data["message"], "Message sent successfully")

        # Check that the ContactMessage was created with empty last_name
        self.assertEqual(ContactMessage.objects.count(), 1)
        contact_message_missing = ContactMessage.objects.first()
        self.assertEqual(contact_message_missing.first_name, self.valid_data["first_name"])
        self.assertEqual(contact_message_missing.last_name, "")  # Should default to empty string
        self.assertEqual(contact_message_missing.email, self.valid_data["email"])
        self.assertEqual(contact_message_missing.message, self.valid_data["message"])

        # Reset the database for the next test case
        ContactMessage.objects.all().delete()

        # Test case 2: Blank last_name
        data_blank_last_name = self.valid_data.copy()
        data_blank_last_name["last_name"] = ""  # Set last_name to blank

        response_blank = self.client.post(self.url, data=data_blank_last_name, format="json")

        # Check the response status for blank last_name
        self.assertEqual(response_blank.status_code, status.HTTP_200_OK)
        self.assertEqual(response_blank.data["message"], "Message sent successfully")

        # Check that the ContactMessage was created with empty last_name
        self.assertEqual(ContactMessage.objects.count(), 1)
        contact_message_blank = ContactMessage.objects.first()
        self.assertEqual(contact_message_blank.first_name, self.valid_data["first_name"])
        self.assertEqual(contact_message_blank.last_name, "")  # Should be empty string
        self.assertEqual(contact_message_blank.email, self.valid_data["email"])
        self.assertEqual(contact_message_blank.message, self.valid_data["message"])


class ProfileViewTest(BaseTest):
    def test_get_profile_instructor_authenticated(self):
        """
        Ensure that an authenticated instructor can retrieve their profile information.
        """
        url = reverse("profile")
        response = self.client_instructor.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        instructor_user = self.new_user_instructor

        self.assertEqual(response_data["user"], instructor_user.id)
        self.assertEqual(response_data["username"], instructor_user.username)
        self.assertEqual(response_data["email"], instructor_user.email)
        self.assertEqual(response_data["first_name"], instructor_user.first_name)
        self.assertEqual(response_data["last_name"], instructor_user.last_name)

    def test_get_profile_unauthenticated(self):
        """
        Ensure that unauthenticated users cannot access the profile information.
        """
        # Create a new APIClient without credentials
        unauthenticated_client = APIClient()
        url = reverse("profile")
        response = unauthenticated_client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response_data = response.json()
        self.assertIn("detail", response_data)
        self.assertEqual(response_data["detail"], "Authentication credentials were not provided.")


class SignUpInstructorTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.signup_url = reverse(
            "sign-up-instructor"
        )  # Ensure this name matches your URL configuration

    @patch("api.views.user_views.mailInstructor")  # Adjust the path based on your project structure
    def test_signup_instructor_success(self, mock_mailInstructor):
        """
        Test that a user can successfully sign up as an instructor with all required fields.
        """
        data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane.doe@example.com",
            "password": "StrongPassword123!",
        }

        response = self.client.post(self.signup_url, data, format="json")

        # Assert HTTP 201 Created
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Assert response contains token, user, and instructor IDs
        self.assertIn("token", response.data)
        self.assertIn("user", response.data)
        self.assertIn("instructor", response.data)

        # Verify User creation
        user = User.objects.get(email=data["email"])
        self.assertEqual(user.first_name, data["first_name"])
        self.assertEqual(user.last_name, data["last_name"])
        self.assertTrue(user.check_password(data["password"]))

        # Verify Token creation
        token = Token.objects.get(user=user)
        self.assertEqual(response.data["token"], token.key)

        # Verify Instructor creation
        instructor = Instructor.objects.get(user=user)
        self.assertEqual(str(instructor.id), response.data["instructor"])

        # Assert that mailInstructor was called once with correct email
        mock_mailInstructor.assert_called_once_with(user.email)

    @patch("api.views.user_views.mailInstructor")
    def test_signup_instructor_invalid_email_format(self, mock_mailInstructor):
        """
        Test that signing up with an invalid email format fails.
        """
        data = {
            "first_name": "Alice",
            "last_name": "Wonderland",
            "email": "invalid-email-format",
            "password": "ValidPass123!",
        }

        response = self.client.post(self.signup_url, data, format="json")

        # Assert HTTP 400 Bad Request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Assert error message
        self.assertIn("message", response.data)
        self.assertEqual(response.data["message"], "Enter a valid email address.")

        # Ensure no User or Instructor was created
        self.assertFalse(User.objects.filter(email=data["email"]).exists())

        # Assert that mailInstructor was not called
        mock_mailInstructor.assert_not_called()

    @patch("api.views.user_views.mailInstructor")
    def test_signup_instructor_missing_required_fields(self, mock_mailInstructor):
        """
        Test that signing up without required fields fails.
        """
        data = {
            "last_name": "NoFirstName",
            "email": "nofirstname@example.com",
            "password": "ValidPass123!",
        }

        response = self.client.post(self.signup_url, data, format="json")

        # Assert HTTP 400 Bad Request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Assert error message
        self.assertIn("message", response.data)
        self.assertEqual(response.data["message"], "Please provide all required fields.")

        # Ensure no User or Instructor was created
        self.assertFalse(User.objects.filter(email=data["email"]).exists())

        # Assert that mailInstructor was not called
        mock_mailInstructor.assert_not_called()

    @patch("api.views.user_views.mailInstructor")
    def test_signup_instructor_blank_last_name(self, mock_mailInstructor):
        """
        Test that signing up with a blank last_name sets it to an empty string.
        """
        data = {
            "first_name": "Charlie",
            "last_name": "",  # Blank last_name
            "email": "charlie@example.com",
            "password": "StrongPass123!",
        }

        response = self.client.post(self.signup_url, data, format="json")

        # Assert HTTP 201 Created
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Assert response contains token, user, and instructor IDs
        self.assertIn("token", response.data)
        self.assertIn("user", response.data)
        self.assertIn("instructor", response.data)

        # Verify User creation
        user = User.objects.get(email=data["email"])
        self.assertEqual(user.first_name, data["first_name"])
        self.assertEqual(user.last_name, "")  # Should be empty string
        self.assertTrue(user.check_password(data["password"]))

        # Verify Token creation
        token = Token.objects.get(user=user)
        self.assertEqual(response.data["token"], token.key)

        # Verify Instructor creation
        instructor = Instructor.objects.get(user=user)
        self.assertEqual(str(instructor.id), response.data["instructor"])

        # Assert that mailInstructor was called once with correct email
        mock_mailInstructor.assert_called_once_with(user.email)


class LectureSummaryViewTest(BaseTest):
    def setUp(self):
        super().setUp()
        # Set up a sample InstructorRecordings instance for valid recording_id tests
        self.recording = InstructorRecordings.objects.create(instructor=self.instructor)

    def test_create_lecture_summary_success(self):
        url = reverse("lecture_summary", kwargs={"recording_id": str(self.recording.id)})
        data = {"summary": "This is a test summary"}
        response = self.client_instructor.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)
        self.assertEqual(str(response.data["recording_id"]), str(self.recording.id))
        self.assertIn("created_at", response.data)

    def test_create_lecture_summary_invalid_recording_id(self):
        url = reverse(
            "lecture_summary", kwargs={"recording_id": "127ac01a-379b-44af-97e6-286bac44ff7f"}
        )
        data = {"summary": "Test summary with invalid recording_id"}
        response = self.client_instructor.post(url, data, format="json")

        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN
        )  # Instructor doesn't own the recording

    def test_create_lecture_summary_unexpected_error(self):
        url = reverse("lecture_summary", kwargs={"recording_id": str(self.recording.id)})
        data = {"summary": "Test summary"}
        with self.assertRaises(Exception):
            with transaction.atomic():
                response = self.client_instructor.post(url, data, format="json")
                self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_get_lecture_summary_successful(self):
        url = reverse("lecture_summary", kwargs={"recording_id": str(self.recording.id)})
        LectureSummary.objects.create(summary="Test Summary 1", recording=self.recording)
        LectureSummary.objects.create(summary="Test summary 2", recording=self.recording)

        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, dict)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["summary"], "Test Summary 1")
        self.assertEqual(response.data[1]["summary"], "Test Summary 2")

    def test_get_lecture_summary_not_found(self):
        url = reverse("lecture_summary", kwargs={"recording_id": str(self.recording.id)})
        LectureSummary.objects.filter(recording=self.recording).delete()

        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("message", response.data)
        self.assertEqual(response.data["message"], "Lecture summary not found")

    def test_get_lecture_summary_forbidden(self):
        url = reverse("lecture_summary", kwargs={"recording_id": str(self.recording.id)})
        self.client_instructor.force_authenticate(user=None)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("message", response.data)
        self.assertEqual(response.data["message"], "Forbidden")

    def test_get_lecture_summary_server_error(self):
        url = reverse("lecture_summary", kwargs={"recording_id": str(self.recording.id)})
        with patch("api.views.user_views.mailInstructor"):
            response = self.client.get(url, format="json")
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            self.assertIn("message", response.data)
            self.assertEqual(response.data["message"], "Server error")

class RecordingTitleChangeTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.recording = InstructorRecordings.objects.create(
            title="Initial Title", instructor=self.instructor
        )

        # Create another instructor user to act as a non-owner
        self.other_user_instructor = User.objects.create_user(
            username="other_instructor@gmail.com",
            email="other_instructor@gmail.com",
            password="password",
            first_name="Other",
            last_name="Instructor",
        )
        self.other_instructor = Instructor.objects.create(user=self.other_user_instructor)
        other_token, _ = Token.objects.get_or_create(user=self.other_user_instructor)
        self.client_other_instructor = APIClient()
        self.client_other_instructor.credentials(HTTP_AUTHORIZATION="Token " + other_token.key)
        self.url = reverse("recording-update-title", kwargs={"recording_id": self.recording.id})

    def test_change_recording_title_by_owner(self):
        data = {"title": "New Title From Owner"}

        response = self.client_instructor.patch(self.url, data, format="json")

        # Assert HTTP 200 OK and title change
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], data["title"])

        # Verify the recording title in the database was changed
        changed_recording = InstructorRecordings.objects.get(id=self.recording.id)
        self.assertEqual(changed_recording.title, data["title"])

    def test_change_recording_title_by_non_owner(self):
        data = {"title": "Unauthorized Title Change"}

        response = self.client_other_instructor.patch(self.url, data, format="json")

        # Assert forbidden response and no title change
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data["error"],
            "You do not have permission to modify this recording.",
        )

        # Verify the title remains unchanged in the database
        unchanged_recording = InstructorRecordings.objects.get(id=self.recording.id)
        self.assertEqual(unchanged_recording.title, "Initial Title")


class RecordingDurationChangeTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.recording = InstructorRecordings.objects.create(
            title="Initial Title",
            instructor=self.instructor,
            # duration defaults to 0
        )

        # confirm duration defaults to 0
        self.assertEqual(self.recording.duration, 0)

        # Create another instructor user to act as a non-owner
        self.other_user_instructor = User.objects.create_user(
            username="other_instructor@gmail.com",
            email="other_instructor@gmail.com",
            password="password",
            first_name="Other",
            last_name="Instructor",
        )
        self.other_instructor = Instructor.objects.create(user=self.other_user_instructor)
        other_token, _ = Token.objects.get_or_create(user=self.other_user_instructor)
        self.client_other_instructor = APIClient()
        self.client_other_instructor.credentials(HTTP_AUTHORIZATION="Token " + other_token.key)
        self.url = reverse("update-recording-duration", kwargs={"recording_id": self.recording.id})

    def test_change_recording_duration_by_owner(self):
        data = {"duration": 10}

        response = self.client_instructor.patch(self.url, data, format="json")

        # Assert HTTP 200 OK and duration change
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["duration"], data["duration"])

        # Verify the recording duration in the database was changed
        changed_recording = InstructorRecordings.objects.get(id=self.recording.id)
        self.assertEqual(changed_recording.duration, data["duration"])

    def test_change_recording_duration_by_non_owner(self):
        data = {"duration": "100"}

        response = self.client_other_instructor.patch(self.url, data, format="json")

        # Assert forbidden response
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Verify the duration remains unchanged in the database
        unchanged_recording = InstructorRecordings.objects.get(id=self.recording.id)
        self.assertEqual(unchanged_recording.duration, 0)


class QuizTitleChangeTest(BaseTest):
    def setUp(self):
        super().setUp()

        # Create another instructor user to act as a non-owner
        self.other_user_instructor = User.objects.create_user(
            username="other_instructor@gmail.com",
            email="other_instructor@gmail.com",
            password="password",
            first_name="Other",
            last_name="Instructor",
        )

        self.other_instructor = Instructor.objects.create(user=self.other_user_instructor)
        other_token, _ = Token.objects.get_or_create(user=self.other_user_instructor)
        self.client_other_instructor = APIClient()
        self.client_other_instructor.credentials(HTTP_AUTHORIZATION="Token " + other_token.key)
        self.url = reverse("quiz-update-title", kwargs={"quiz_id": self.new_quiz.id})

    def test_change_quiz_title_by_owner(self):
        data = {"title": "New Title From Owner"}

        response = self.client_instructor.patch(self.url, data, format="json")

        # Assert HTTP 200 OK and title change
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], data["title"])

        # Verify the quiz title in the database was changed
        changed_quiz = Quiz.objects.get(id=self.new_quiz.id)
        self.assertEqual(changed_quiz.title, data["title"])

    def test_change_quiz_title_by_non_owner(self):
        data = {"title": "Unauthorized Title Change"}

        response = self.client_other_instructor.patch(self.url, data, format="json")

        # Assert forbidden response and no title change
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # Verify the title remains unchanged in the database
        unchanged_quiz = Quiz.objects.get(id=self.new_quiz.id)
        self.assertEqual(unchanged_quiz.title, "Test Quiz")


class UserAuthTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.login_url = reverse("login")
        self.logout_url = reverse("logout")

    def test_login_success(self):
        data = {"email": "test@gmail.com", "password": "password"}
        response = self.client.post(self.login_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertIn("token", response_data)
        self.assertEqual(response_data["user"], self.new_user_instructor.id)

    def test_login_invalid_email(self):
        data = {"email": "invalid@example.com", "password": "password"}
        response = self.client.post(self.login_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response_data = response.json()
        self.assertEqual(response_data["detail"], "Invalid email or password!")

    def test_login_invalid_password(self):
        data = {"email": "test@gmail.com", "password": "wrongpassword"}
        response = self.client.post(self.login_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response_data = response.json()
        self.assertEqual(response_data["detail"], "Invalid email or password!")

    def test_logout_success(self):
        token = Token.objects.get(user=self.new_user_instructor)
        self.client.credentials(HTTP_AUTHORIZATION="Token {}".format(token.key))
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data["message"], "User logged out successfully")
        self.assertFalse(Token.objects.filter(user=self.new_user_instructor).exists())

    def test_logout_without_token(self):
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
