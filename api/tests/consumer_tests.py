# api/tests/consumer_tests.py
import pytest
import asyncio
from channels.testing import WebsocketCommunicator
from django.utils import timezone
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from api.models import (
    Quiz,
    Instructor,
    QuizSession,
    QuizSessionStudent,
    UserResponse,
    QuestionMultipleChoice,
)
from hice_backend.asgi import application  # Ensure this path is correct


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_instructor_end_quiz():
    # ----------------------------
    # Step 1: Create a User for Instructor
    # ----------------------------
    user = await sync_to_async(User.objects.create_user)(
        username="instructor_user",
        email="instructor@example.com",
        password="securepassword123",
    )

    # ----------------------------
    # Step 2: Create an Instructor
    # ----------------------------
    instructor = await sync_to_async(Instructor.objects.create)(
        user=user,
    )

    # ----------------------------
    # Step 3: Create a Quiz
    # ----------------------------
    quiz = await sync_to_async(Quiz.objects.create)(
        title="Sample Quiz",
        instructor=instructor,
        created_at=timezone.now(),
        instructor_recording=None,  # Or set to an existing InstructorRecordings instance
    )

    # ----------------------------
    # Step 4: Create a QuizSession associated with the Quiz
    # ----------------------------
    session = await sync_to_async(QuizSession.objects.create)(
        code="TEST01",
        quiz=quiz,
        start_time=timezone.now(),
        # end_time can be left unset; it will be set when the quiz ends
    )

    # ----------------------------
    # Step 5: Create multiple QuizSessionStudents associated with the QuizSession
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
    # Step 6: Create multiple QuestionMultipleChoice associated with the Quiz
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
    # Step 7: Create UserResponses associated with the Students, QuizSession, and Questions
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
    # Step 8: Initialize WebSocket communicator for the instructor consumer
    # Corrected WebSocket path to "/ws/quiz-session-instructor/{session.code}/"
    # ----------------------------
    communicator = WebsocketCommunicator(
        application, f"/ws/quiz-session-instructor/{session.code}/"
    )
    connected, subprotocol = await communicator.connect()
    assert connected, "WebSocket connection failed"

    # ----------------------------
    # Step 9: Receive the initial settings message
    # ----------------------------
    try:
        initial_response = await communicator.receive_json_from(timeout=5)
        assert initial_response["type"] == "settings", "Expected 'settings' message"
        assert "settings" in initial_response, "'settings' not in response"
        assert "user_count" in initial_response, "'user_count' not in response"
    except asyncio.TimeoutError:
        pytest.fail("Did not receive 'settings' response in time")

    # ----------------------------
    # Step 10: Simulate serving the first question
    # ----------------------------
    first_question = questions[0]
    await communicator.send_json_to({"type": "next_question"})

    try:
        response = await communicator.receive_json_from(timeout=5)
        assert (
            response["type"] == "next_question"
        ), "Expected 'next_question' message for the first question"
        assert "question" in response, "'question' not in response"
        assert (
            response["question"]["question_text"] == first_question.question_text
        ), "First question text mismatch"
    except asyncio.TimeoutError:
        pytest.fail(
            f"Did not receive 'next_question' response for question '{first_question.question_text}' in time"
        )

    # ----------------------------
    # Step 11: Simulate serving the second question
    # ----------------------------
    second_question = questions[1]
    await communicator.send_json_to({"type": "next_question"})

    try:
        response = await communicator.receive_json_from(timeout=5)
        assert (
            response["type"] == "next_question"
        ), "Expected 'next_question' message for the second question"
        assert "question" in response, "'question' not in response"
        assert (
            response["question"]["question_text"] == second_question.question_text
        ), "Second question text mismatch"
    except asyncio.TimeoutError:
        pytest.fail(
            f"Did not receive 'next_question' response for question '{second_question.question_text}' in time"
        )

    # ----------------------------
    # Step 12: Send 'skip_question' to skip the second question
    # ----------------------------
    await communicator.send_json_to({"type": "skip_question", "question_id": second_question.id})

    # ----------------------------
    # Step 13: Receive 'next_question' for the third question
    # ----------------------------
    last_question = questions[2]
    try:
        response = await communicator.receive_json_from(timeout=5)
        assert (
            response["type"] == "next_question"
        ), "Expected 'next_question' message after skipping a question"
        assert "question" in response, "'question' not in response"
        assert (
            response["question"]["question_text"] == last_question.question_text
        ), "Last question text mismatch after skipping"
    except asyncio.TimeoutError:
        pytest.fail(
            f"Did not receive 'next_question' response for question '"
            f"{last_question.question_text}' after skipping in time"
        )

    # ----------------------------
    # Step 14: Send one more 'next_question' to trigger 'quiz_ended'
    # ----------------------------
    await communicator.send_json_to({"type": "next_question"})

    # ----------------------------
    # Step 15: Receive 'quiz_ended' response
    # ----------------------------
    try:
        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "quiz_ended", "Expected 'quiz_ended' message"
        assert "grades" in response, "'grades' not in response"

        # Expected grades based on variance and skipped question:
        # - First two students: 2/2 = 100%
        # - Next two students: 1/2 = 50%
        # - Last student: 0/2 = 0%
        expected_grades = {
            "100.0": [students[0].username, students[1].username],
            "50.0": [students[2].username, students[3].username],
            "0.0": [students[4].username],
        }

        # Validate the grades
        assert (
            response["grades"] == expected_grades
        ), f"Grades mismatch: Expected {expected_grades}, got {response['grades']}"
    except asyncio.TimeoutError:
        pytest.fail("Did not receive 'quiz_ended' response in time")

    # ----------------------------
    # Step 16: Disconnect the communicator
    # ----------------------------
    await communicator.disconnect()
