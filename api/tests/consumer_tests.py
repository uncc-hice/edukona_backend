import asyncio

import pytest
from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from api.models import (
    Instructor,
    InstructorRecordings,
    QuestionMultipleChoice,
    Quiz,
    QuizSession,
    QuizSessionStudent,
    UserResponse,
)
from hice_backend.asgi import application

import random
from .test_services import BaseQuizTest

from typing import List


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_quiz():
    # ----------------------------
    # Create a User for Instructor
    # ----------------------------
    user = await sync_to_async(User.objects.create_user)(
        username="instructor_user",
        email="instructor@example.com",
        password="securepassword123",
    )

    # ----------------------------
    # Create an Instructor
    # ----------------------------
    instructor = await sync_to_async(Instructor.objects.create)(
        user=user,
    )

    # ----------------------------
    # Create a Recording
    # ----------------------------
    recording = await sync_to_async(InstructorRecordings.objects.create)(
        instructor=instructor, title="test"
    )

    # ----------------------------
    # Create a Quiz
    # ----------------------------
    quiz = await sync_to_async(Quiz.objects.create)(
        title="Sample Quiz",
        instructor=instructor,
        timer=True,
        created_at=timezone.now(),
        instructor_recording=recording,
    )

    # ----------------------------
    # Create a QuizSession associated with the Quiz
    # ----------------------------
    session = await sync_to_async(QuizSession.objects.create)(
        code="TEST01",
        quiz=quiz,
        start_time=timezone.now(),
        # end_time can be left unset; it will be set when the quiz ends
    )

    # ----------------------------
    # Create multiple QuizSessionStudents associated with the QuizSession
    # ----------------------------
    students = []
    num_students = 5  # Number of students to create
    for i in range(num_students):
        student = await sync_to_async(QuizSessionStudent.objects.create)(
            username=f"test_student_{i}",
            quiz_session=session,
        )
        students.append(student)

    # ----------------------------
    # Create multiple QuestionMultipleChoice associated with the Quiz
    # ----------------------------
    questions = []
    question_texts = [
        "What is the capital of France?",
        "What is 2 + 2?",
        "What color is the sky?",
    ]
    for idx, text in enumerate(question_texts, start=1):
        question = await sync_to_async(QuestionMultipleChoice.objects.create)(
            question_text=text,
            incorrect_answer_list=["Option A", "Option B", "Option C"],
            correct_answer="Correct Answer",
            points=1,
            quiz=quiz,
            duration=20,
        )
        questions.append(question)

    # ----------------------------
    # Create UserResponses associated with the Students, QuizSession, and Questions
    # Introduce variance in student responses
    # ----------------------------
    # Variance Setup:
    # - First 2 students answer all questions correctly
    # - Next 2 students answer the first question correctly and others incorrectly
    # - Last student answers all questions incorrectly
    for idx, student in enumerate(students):
        for question in questions:
            if idx < 2:
                # First two students answer all correctly
                selected_answer = "Correct Answer"
                is_correct = True
            elif idx < 4:
                # Next two students answer the first question correctly, others incorrectly
                if question == questions[0]:
                    selected_answer = "Correct Answer"
                    is_correct = True
                else:
                    selected_answer = "Option A"  # Assuming this is incorrect
                    is_correct = False
            else:
                # Last student answers all incorrectly
                selected_answer = "Option A"  # Assuming this is incorrect
                is_correct = False

            await sync_to_async(UserResponse.objects.create)(
                student=student,
                quiz_session=session,
                question=question,
                selected_answer=selected_answer,
                is_correct=is_correct,
            )

    # ----------------------------
    # Initialize WebSocket communicator for the instructor consumer
    # Corrected WebSocket path to "/ws/quiz-session-instructor/{session.code}/"
    # ----------------------------
    communicator = WebsocketCommunicator(
        application, f"/ws/quiz-session-instructor/{session.code}/"
    )
    connected, subprotocol = await communicator.connect()
    assert connected, "WebSocket connection failed"

    # ----------------------------
    # Initialize WebSocket communicator for the instructor consumer
    # ----------------------------
    try:
        initial_response = await communicator.receive_json_from(timeout=5)
        assert initial_response["type"] == "quiz_details", "Expected 'quiz_details' message"
        assert "quiz" in initial_response, "'quiz' not in response"
        assert "timer" in initial_response["quiz"], "'timer' not in quiz"
        assert "user_count" in initial_response, "'user_count' not in response"
    except asyncio.TimeoutError:
        pytest.fail("Did not receive 'quiz_details' response in time")

    # ----------------------------
    # Simulate serving the first question
    # ----------------------------
    first_question = questions[0]
    await communicator.send_json_to({"type": "next_question"})

    try:
        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "next_question", (
            "Expected 'next_question' message for the first question"
        )
        assert "question" in response, "'question' not in response"
        assert response["question"]["question_text"] == first_question.question_text, (
            "First question text mismatch"
        )
    except asyncio.TimeoutError:
        pytest.fail(
            f"Did not receive 'next_question' response for question '{first_question.question_text}' in time"
        )

    # ----------------------------
    # Simulate serving the second question
    # ----------------------------
    second_question = questions[1]
    await communicator.send_json_to({"type": "next_question"})

    try:
        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "next_question", (
            "Expected 'next_question' message for the second question"
        )
        assert "question" in response, "'question' not in response"
        assert response["question"]["question_text"] == second_question.question_text, (
            "Second question text mismatch"
        )
    except asyncio.TimeoutError:
        pytest.fail(
            f"Did not receive 'next_question' response for question '{second_question.question_text}' in time"
        )

    # ----------------------------
    # Simulate serving the third question
    # ----------------------------
    await communicator.send_json_to({"type": "next_question"})

    # ----------------------------
    # Receive 'next_question' for the third question
    # ----------------------------
    last_question = questions[2]
    try:
        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "next_question", (
            "Expected 'next_question' message after second question"
        )
        assert "question" in response, "'question' not in response"
        assert response["question"]["question_text"] == last_question.question_text, (
            "Last question text mismatch after second question"
        )
    except asyncio.TimeoutError:
        pytest.fail(
            f"Did not receive 'next_question' response in time for question '"
            f"{last_question.question_text}' after finshing second question"
        )

    # ----------------------------
    # Send one more 'next_question' to trigger 'quiz_ended'
    # ----------------------------
    await communicator.send_json_to({"type": "next_question"})

    # ----------------------------
    # Receive 'quiz_ended' response
    # ----------------------------
    try:
        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "quiz_ended", "Expected 'quiz_ended' message"
        assert "grades" in response, "'grades' not in response"

        # Expected grades based on variance
        # - First two students: 2/2 = 100%
        # - Next two students: 1/3 = 33%
        # - Last student: 0/2 = 0%
        expected_grades = {
            "100.0": [students[0].username, students[1].username],
            "33.33": [students[2].username, students[3].username],
            "0.0": [students[4].username],
        }

        # Validate the grades
        print(f"\n\n\n{response['grades']}\n\n\n")
        assert response["grades"] == expected_grades, (
            f"Grades mismatch: Expected {expected_grades}, got {response['grades']}"
        )
    except asyncio.TimeoutError:
        pytest.fail("Did not receive 'quiz_ended' response in time")

    # ----------------------------
    # Disconnect the communicator
    # ----------------------------
    await communicator.disconnect()


class RecordingConsumerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.refresh = RefreshToken.for_user(self.user)
        self.jwt_token = str(self.refresh.access_token)

    @pytest.mark.asyncio
    async def test_jwt_authentication(self):
        communicator = WebsocketCommunicator(application, f"/ws/recordings/?jwt={self.jwt_token}")

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        await communicator.disconnect()

    @pytest.mark.asyncio
    async def test_invalid_jwt_authentication(self):
        invalid_jwt_token = "invalidtoken"

        communicator = WebsocketCommunicator(
            application, f"/ws/recordings/?jwt={invalid_jwt_token}"
        )

        connected, _ = await communicator.connect()
        self.assertFalse(connected)


class StudentConsumerReconnectTest(BaseQuizTest):
    def setUp(self):
        super().setUp(student_count=2)
        self.student_responses = self._generate_responses()
        self.student_grades = self._calculate_expected_grades(self.student_responses)
        self.timeout = 1

    def _generate_responses(self) -> List[List[str]]:
        def generate_student_response():
            responses = []
            for question in self.questions:
                options = question["incorrect_answer_list"] + [question["correct_answer"]]
                responses.append(random.choice(options))
            return responses

        return [generate_student_response() for _ in range(self.student_count)]

    def _calculate_expected_grades(self, responses: List[List[str]]) -> List[int]:
        grades = []
        for student_responses in responses:
            score = 0
            for i, response in enumerate(student_responses):
                if response == self.questions[i]["correct_answer"]:
                    score += 1
            grades.append(score)
        return grades

    async def setUp_quiz_environment(self):
        """Common setup to prepare a quiz with connected instructor and students."""
        self.instructor_communicator = WebsocketCommunicator(
            application, f"/ws/quiz-session-instructor/{self.code}/"
        )
        connected, _ = await self.instructor_communicator.connect()
        assert connected, "Instructor failed to connect"

        response = await self.instructor_communicator.receive_json_from(timeout=self.timeout)
        assert response["type"] == "quiz_details", "Expected type: 'quiz_details' in message"
        assert response["user_count"] == 0, "Expected initial user_count of 0"

        # Connect students
        for student in self.students:
            student["communicator"] = await self.connect_student(student["username"])

    async def connect_student(self, username):
        communicator = WebsocketCommunicator(
            application, f"/ws/student/join/{self.code}/?username={username}"
        )
        connected, _ = await communicator.connect()
        assert connected, f"Student {username} failed to connect"

        await communicator.send_json_to({"type": "join", "username": username})
        response = await communicator.receive_json_from(timeout=self.timeout)
        assert response["type"] == "success", "Expected 'success' message"

        for student in self.students:
            if student["username"] == username:
                student["id"] = response["student_id"]
                break

        response = await self.instructor_communicator.receive_json_from(timeout=self.timeout)
        assert response["type"] == "student_joined", "Expected 'student_joined' message"

        return communicator

    async def serve_question(self, question_index):
        question = self.questions[question_index]
        await self.instructor_communicator.send_json_to({"type": "next_question"})

        response = await self.instructor_communicator.receive_json_from(timeout=self.timeout)
        assert response["type"] == "next_question", "Expected 'next_question' message"
        assert response["question"]["question_text"] == question["question_text"]

        questions = [response["question"]["correct_answer"]]
        questions.extend(response["question"]["incorrect_answer_list"])
        random.shuffle(questions)
        await self.instructor_communicator.send_json_to(
            {"type": "update_order", "order": questions}
        )

        return response["question"]

    async def submit_student_answer(self, student_index, question_index):
        """Helper to submit a student answer and verify responses."""
        student = self.students[student_index]
        communicator = student["communicator"]

        response = await communicator.receive_json_from(timeout=self.timeout)
        assert response["type"] == "next_question", "Student didn't receive question"

        # Submit answer
        data = {
            "student": {"id": student["id"]},
            "question_id": self.questions[question_index]["id"],
            "selected_answer": self.student_responses[student_index][question_index],
            "quiz_session_code": self.code,
        }
        await communicator.send_json_to({"type": "response", "data": data})

        # Verify student confirmation
        response = await communicator.receive_json_from(timeout=self.timeout)
        assert response["type"] == "answer", "Expected 'answer' confirmation"
        assert response["status"] == "success", "Answer submission failed"

        # Verify instructor receives the response (both update_answers and user_response)
        response = await self.instructor_communicator.receive_json_from(timeout=self.timeout)
        assert response["type"] == "update_answers", "Instructor didn't receive answer update"

        response = await self.instructor_communicator.receive_json_from(timeout=self.timeout)
        assert response["type"] == "user_response", "Instructor didn't receive user response"

        return response

    async def perform_reconnect(self, student_index):
        student = self.students[student_index]
        await student["communicator"].disconnect()

        new_communicator = WebsocketCommunicator(
            application, f"/ws/student/join/{self.code}/?username={student['username']}"
        )
        connected, _ = await new_communicator.connect()
        assert connected, f"Student {student_index} failed to reconnect"

        await new_communicator.send_json_to({"type": "reconnect", "student_id": student["id"]})
        response = await new_communicator.receive_json_from(timeout=self.timeout)
        assert response["type"] == "reconnect_success", "Failed to reconnect"

        self.students[student_index]["communicator"] = new_communicator

        return new_communicator

    async def cleanup(self):
        await self.instructor_communicator.disconnect()
        for student in self.students:
            if "communicator" in student:
                await student["communicator"].disconnect()

    @pytest.mark.asyncio
    async def test_student_reconnection_during_quiz(self):
        await self.setUp_quiz_environment()
        student_foo = 0
        student_bar = 1
        await self.serve_question(0)
        await self.submit_student_answer(student_foo, 0)
        await self.submit_student_answer(student_bar, 0)

        await self.serve_question(1)

        # First student answers
        await self.submit_student_answer(student_foo, 1)

        # Second student disconnects and reconnects
        reconnected_communicator = await self.perform_reconnect(student_bar)

        response = await reconnected_communicator.receive_json_from(timeout=self.timeout)
        assert (
            response["type"] == "next_question"
        ), "Reconnected student didn't receive current question"
        assert response["question"]["question_text"] == self.questions[1]["question_text"]

        await self.cleanup()

    @pytest.mark.asyncio
    async def test_answering_after_reconnection(self):
        await self.setUp_quiz_environment()
        await self.serve_question(0)

        # Disconnect and reconnect student
        student_index = 0
        await self.perform_reconnect(student_index)
        await self.submit_student_answer(student_index, 0)

        await self.cleanup()

    @pytest.mark.asyncio
    async def test_complete_quiz_with_reconnection(self):
        await self.setUp_quiz_environment()

        student_foo = 0
        student_bar = 1

        await self.serve_question(0)
        await self.submit_student_answer(student_foo, 0)
        await self.submit_student_answer(student_bar, 0)

        # Question 2 with reconnection
        await self.serve_question(1)
        await self.submit_student_answer(student_foo, 1)
        await self.perform_reconnect(student_bar)
        await self.submit_student_answer(student_bar, 1)

        await self.serve_question(2)
        await self.submit_student_answer(student_foo, 2)
        await self.submit_student_answer(student_bar, 2)

        # End quiz
        await self.instructor_communicator.send_json_to({"type": "next_question"})
        response = await self.instructor_communicator.receive_json_from(timeout=self.timeout)
        assert response["type"] == "quiz_ended", "Expected 'quiz_ended' message"

        await self.cleanup()
