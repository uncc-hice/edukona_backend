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
        self.new_user_instructor = User.objects.create_user(
            username="test@gmail.com", password="password"
        )
        Instructor.objects.create(user=self.new_user_instructor)
        token, _ = Token.objects.get_or_create(user=self.new_user_instructor)
        self.client_instructor = APIClient()
        self.client_instructor.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        self.new_user_student = User.objects.create_user(
            username="student@gmail.com", password="password"
        )
        Student.objects.create(user=self.new_user_student)
        token, _ = Token.objects.get_or_create(user=self.new_user_student)
        self.client_student = APIClient()
        self.client_student.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        self.new_quiz = Quiz.objects.create(
            title="Test Quiz",
            instructor_id=1,
            start_time="2021-10-10T00:00:00Z",
            end_time="2021-10-10T00:00:00Z",
        )

        self.new_question = QuestionMultipleChoice.objects.create(
            question_text="What is 1+1?",
            incorrect_answer_list=["0", "1", "3"],
            correct_answer="2",
            points=1,
            quiz_id=1,
        )

        self.second_new_question = QuestionMultipleChoice.objects.create(
            question_text="What is 3 + 3?",
            incorrect_answer_list=["3", "4", "5"],
            correct_answer="6",
            points=5,
            quiz_id=1,
        )

        self.new_quiz_session = QuizSession.objects.create(
            quiz=self.new_quiz, code=QuizSession.generate_unique_code(self)
        )

        self.new_quiz_session_student = QuizSessionStudent.objects.create(
            quiz_session=self.new_quiz_session, username="test"
        )

        self.new_user_response = UserResponse.objects.create(
            student=self.new_quiz_session_student,
            question_id=self.new_question.id,
            quiz_session_id=self.new_quiz_session.id,
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
    def test_post_quiz(self):
        url = reverse("quiz-list")
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


class QuestionViewTest(BaseTest):
    def test_get_question(self):
        url = reverse("question-detail", kwargs={"question_id": self.new_question.id})
        response = self.client_instructor.get(url)

        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(response_data["questions"]["id"], self.new_question.id)
        self.assertEqual(
            response_data["questions"]["question_text"], self.new_question.question_text
        )
        self.assertEqual(
            response_data["questions"]["incorrect_answer_list"],
            self.new_question.incorrect_answer_list,
        )
        self.assertEqual(
            response_data["questions"]["correct_answer"],
            self.new_question.correct_answer,
        )
        self.assertEqual(response_data["questions"]["points"], self.new_question.points)
        self.assertEqual(response_data["questions"]["quiz_id"], self.new_question.quiz.id)

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
        data = {"username": "bad_username", "password": "bad_password!"}
        response = self.client_student.post(url, data, format="json")
        self.assertEqual(response.status_code, 401)
        response_data = response.json()
        self.assertEqual(response_data["detail"], "Invalid username or password!")
