# test_question_views.py

from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from api.models import User, Instructor, Student, Quiz, QuestionMultipleChoice


class CreateMultipleQuestionsViewTest(APITestCase):
    def setUp(self):
        # Create an instructor user
        self.instructor_user = User.objects.create_user(
            username="instructor@example.com", password="securepassword"
        )
        self.instructor = Instructor.objects.create(user=self.instructor_user)
        self.instructor_token = Token.objects.create(user=self.instructor_user)
        self.instructor_client = APIClient()
        self.instructor_client.credentials(HTTP_AUTHORIZATION="Token " + self.instructor_token.key)

        # Create a student user
        self.student_user = User.objects.create_user(
            username="student@example.com", password="securepassword"
        )
        self.student = Student.objects.create(user=self.student_user)
        self.student_token = Token.objects.create(user=self.student_user)
        self.student_client = APIClient()
        self.student_client.credentials(HTTP_AUTHORIZATION="Token " + self.student_token.key)

        # Create a quiz owned by the instructor
        self.quiz = Quiz.objects.create(title="Sample Quiz", instructor=self.instructor)

        # URL for creating multiple questions
        self.url = reverse("create-multiple-questions")  # Adjust the name to match your URL pattern

    def test_create_multiple_questions_success(self):
        """
        Test that an instructor can successfully create multiple questions.
        """
        data = [
            {
                "question_text": "What is the capital of France?",
                "incorrect_answer_list": ["Berlin", "London", "Madrid"],
                "correct_answer": "Paris",
                "points": 5,
                "quiz_id": self.quiz.id,
                "duration": 30,
            },
            {
                "question_text": "What is 2 + 2?",
                "incorrect_answer_list": ["3", "5", "6"],
                "correct_answer": "4",
                "points": 3,
                "quiz_id": self.quiz.id,
                "duration": 20,
            },
        ]

        response = self.instructor_client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_data = response.json()
        self.assertIn("created_questions", response_data)
        self.assertEqual(len(response_data["created_questions"]), 2)
        self.assertEqual(response_data["errors"], [])

        # Verify that questions are created in the database
        questions = QuestionMultipleChoice.objects.filter(quiz=self.quiz)
        self.assertEqual(questions.count(), 2)

    def test_create_multiple_questions_invalid_quiz_id(self):
        """
        Test that providing an invalid quiz_id results in an error.
        """
        data = [
            {
                "question_text": "What is the capital of France?",
                "incorrect_answer_list": ["Berlin", "London", "Madrid"],
                "correct_answer": "Paris",
                "points": 5,
                "quiz_id": 9999,  # Invalid quiz_id
                "duration": 30,
            }
        ]

        response = self.instructor_client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response_data = response.json()
        self.assertIn("detail", response_data)

        # Verify that no new questions are created
        questions = QuestionMultipleChoice.objects.all()
        self.assertEqual(questions.count(), 0)

    def test_create_multiple_questions_permission_denied(self):
        """
        Test that a student cannot create questions.
        """
        data = [
            {
                "question_text": "What is the capital of France?",
                "incorrect_answer_list": ["Berlin", "London", "Madrid"],
                "correct_answer": "Paris",
                "points": 5,
                "quiz_id": self.quiz.id,
                "duration": 30,
            }
        ]

        response = self.student_client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Verify that no new questions are created
        questions = QuestionMultipleChoice.objects.filter(quiz=self.quiz)
        self.assertEqual(questions.count(), 0)

    def test_create_multiple_questions_empty_list(self):
        """
        Test that providing an empty list results in an error.
        """
        data = []

        response = self.instructor_client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response_data = response.json()
        self.assertIn("error", response_data)
        self.assertEqual(response_data["error"], "Expected a list of questions")

    def test_create_multiple_questions_missing_quiz_id(self):
        """
        Test that missing quiz_id in one of the questions results in an error.
        """
        data = [
            {
                "question_text": "What is the capital of France?",
                "incorrect_answer_list": ["Berlin", "London", "Madrid"],
                "correct_answer": "Paris",
                "points": 5,
                # 'quiz_id' is missing
                "duration": 30,
            }
        ]

        response = self.instructor_client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response_data = response.json()
        self.assertIn("detail", response_data)

    def test_create_multiple_questions_different_quizzes(self):
        """
        Test that creating questions for multiple quizzes works if the instructor owns all quizzes.
        """
        # Create another quiz owned by the instructor
        another_quiz = Quiz.objects.create(title="Another Quiz", instructor=self.instructor)

        data = [
            {
                "question_text": "Question for first quiz?",
                "incorrect_answer_list": ["Option 1", "Option 2", "Option 3"],
                "correct_answer": "Option 4",
                "points": 5,
                "quiz_id": self.quiz.id,
                "duration": 30,
            },
            {
                "question_text": "Question for second quiz?",
                "incorrect_answer_list": ["Option A", "Option B", "Option C"],
                "correct_answer": "Option D",
                "points": 3,
                "quiz_id": another_quiz.id,
                "duration": 20,
            },
        ]

        response = self.instructor_client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_data = response.json()
        self.assertIn("created_questions", response_data)
        self.assertEqual(len(response_data["created_questions"]), 2)
        self.assertEqual(response_data["errors"], [])

        # Verify that questions are created in the database
        questions_quiz1 = QuestionMultipleChoice.objects.filter(quiz=self.quiz)
        questions_quiz2 = QuestionMultipleChoice.objects.filter(quiz=another_quiz)
        self.assertEqual(questions_quiz1.count(), 1)
        self.assertEqual(questions_quiz2.count(), 1)

    def test_create_multiple_questions_different_quizzes_not_owner(self):
        """
        Test that creating questions for a quiz the instructor doesn't own results in an error.
        """
        # Create another instructor and quiz
        another_instructor_user = User.objects.create_user(
            username="another_instructor@example.com", password="securepassword"
        )
        another_instructor = Instructor.objects.create(user=another_instructor_user)
        another_quiz = Quiz.objects.create(title="Another Quiz", instructor=another_instructor)

        data = [
            {
                "question_text": "Question for own quiz?",
                "incorrect_answer_list": ["Option 1", "Option 2", "Option 3"],
                "correct_answer": "Option 4",
                "points": 5,
                "quiz_id": self.quiz.id,
                "duration": 30,
            },
            {
                "question_text": "Question for another quiz?",
                "incorrect_answer_list": ["Option A", "Option B", "Option C"],
                "correct_answer": "Option D",
                "points": 3,
                "quiz_id": another_quiz.id,
                "duration": 20,
            },
        ]

        response = self.instructor_client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Verify that no new questions are created due to atomic transaction
        questions = QuestionMultipleChoice.objects.all()
        self.assertEqual(questions.count(), 0)
