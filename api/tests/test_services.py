import random

import pytest
from asgiref.sync import sync_to_async
from django.test import TestCase
from django.utils import timezone

from api.models import (
    QuestionMultipleChoice,
    Quiz,
    QuizSession,
    QuizSessionQuestion,
    QuizSessionStudent,
    UserResponse,
)
from api.services import score_session
from typing import List, Set


class BaseQuizTest(TestCase):
    def setUp(self, student_count=5):
        self.quiz = Quiz.objects.create(
            title="Sample Quiz",
        )
        self.code = "TEST00"
        self.session = QuizSession.objects.create(
            code=self.code,
            quiz=self.quiz,
            start_time=timezone.now(),
        )

        self.question_duration = 10

        self.question_count = 3
        self.questions = [
            {
                "question_text": "What is the capital of France?",
                "incorrect_answer_list": ["London", "Berlin", "Madrid"],
                "correct_answer": "Paris",
            },
            {
                "question_text": "What is 2 + 2?",
                "incorrect_answer_list": ["3", "5", "6"],
                "correct_answer": "4",
            },
            {
                "question_text": "What color is the sky?",
                "incorrect_answer_list": ["Red", "Green", "Yellow"],
                "correct_answer": "Blue",
            },
        ]

        self.question_records = []

        for question in self.questions:
            new_question = QuestionMultipleChoice.objects.create(
                question_text=question["question_text"],
                incorrect_answer_list=question["incorrect_answer_list"],
                correct_answer=question["correct_answer"],
                points=1,
                quiz=self.quiz,
                duration=self.question_duration,
            )
            question["id"] = new_question.id
            self.question_records.append(new_question)

        self.skipped_questions: Set[int] = set()

        # student-side setup
        self.student_count = student_count
        self.students = [{"username": f"student_{i}"} for i in range(self.student_count)]


class ScoreSessionServiceTest(BaseQuizTest):
    def setUp(self):
        super().setUp()
        self.student_responses = self._generate_responses()
        self.student_grades = self._calculate_expected_grades(self.student_responses)

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

    def _create_new_responses_and_grades(self):
        responses = self._generate_responses()
        grades = self._calculate_expected_grades(responses)
        return responses, grades

    def _grade_student_response(self, student_responses: List[str]) -> int:
        score = 0
        for i, response in enumerate(student_responses):
            if (
                self.questions[i]["id"] not in self.skipped_questions
                and response == self.questions[i]["correct_answer"]
            ):
                score += 1
        return score

    async def _create_student_records(self):
        student_records = []
        for student in self.students:
            student_record = await sync_to_async(QuizSessionStudent.objects.create)(
                username=student["username"],
                quiz_session=self.session,
            )
            student_records.append(student_record)
        return student_records

    async def _create_quiz_session_questions(self):
        for question in self.question_records:
            await sync_to_async(QuizSessionQuestion.objects.create)(
                question=question,
                quiz_session=self.session,
            )

    async def _submit_responses(self, student_records, responses):
        for question_index in range(self.question_count):
            for student_index in range(self.student_count):
                student = student_records[student_index]
                question = self.question_records[question_index]
                selected_answer = responses[student_index][question_index]
                is_correct = selected_answer == self.questions[question_index]["correct_answer"]

                await sync_to_async(UserResponse.objects.update_or_create)(
                    student=student,
                    question=question,
                    quiz_session=self.session,
                    defaults={"selected_answer": selected_answer, "is_correct": is_correct},
                )

    async def _skip_question(self, question_id):
        question = await sync_to_async(QuizSessionQuestion.objects.get)(id=question_id)
        question.skipped = True
        await sync_to_async(question.save)()
        self.skipped_questions.add(question_id)

    @pytest.mark.asyncio
    async def test_score_session(self):
        student_records = await self._create_student_records()
        await self._create_quiz_session_questions()
        # submit default responses
        await self._submit_responses(student_records, self.student_responses)

        # call the service
        await sync_to_async(score_session)(self.session.id)

        # check if the scores are correctly calculated
        updated_student_records = await sync_to_async(list)(
            QuizSessionStudent.objects.filter(quiz_session=self.session)
        )
        for i, student in enumerate(updated_student_records):
            self.assertEqual(student.score, self.student_grades[i])

    @pytest.mark.asyncio
    async def test_score_session_with_skip(self):
        student_records = await self._create_student_records()
        await self._create_quiz_session_questions()

        # skip a question
        question_to_skip = random.choice(self.question_records).id
        await self._skip_question(question_to_skip)

        # recalculate student grades
        self.student_grades = [
            self._grade_student_response(responses) for responses in self.student_responses
        ]

        await self._submit_responses(student_records, self.student_responses)
        await sync_to_async(score_session)(self.session.id)

        # check if the scores are correctly calculated
        updated_student_records = await sync_to_async(list)(
            QuizSessionStudent.objects.filter(quiz_session=self.session)
        )
        for i, student in enumerate(updated_student_records):
            self.assertEqual(student.score, self.student_grades[i])

    @pytest.mark.asyncio
    async def test_score_session_no_responses(self):
        await self._create_student_records()
        await self._create_quiz_session_questions()

        # call the service
        await sync_to_async(score_session)(self.session.id)

        # check if the scores are correctly calculated
        updated_student_records = await sync_to_async(list)(
            QuizSessionStudent.objects.filter(quiz_session=self.session)
        )
        for student in updated_student_records:
            self.assertEqual(student.score, 0)

    @pytest.mark.asyncio
    async def test_score_session_no_questions(self):
        await self._create_student_records()

        with pytest.raises(ValueError):
            await sync_to_async(score_session)(self.session.id)

    @pytest.mark.asyncio
    async def test_score_session_with_two_responses_per_student(self):
        student_records = await self._create_student_records()
        await self._create_quiz_session_questions()

        # submit default responses
        await self._submit_responses(student_records, self.student_responses)

        # submit new responses
        new_student_responses, new_student_grades = self._create_new_responses_and_grades()
        await self._submit_responses(student_records, new_student_responses)
        await sync_to_async(score_session)(self.session.id)

        # check if the scores are correctly calculated
        updated_student_records = await sync_to_async(list)(
            QuizSessionStudent.objects.filter(quiz_session=self.session)
        )

        for i, student in enumerate(updated_student_records):
            self.assertEqual(student.score, new_student_grades[i])

    @pytest.mark.asyncio
    async def test_score_session_with_no_invocation(self):
        student_records = await self._create_student_records()
        await self._create_quiz_session_questions()

        await self._submit_responses(student_records, self.student_responses)

        updated_student_records = await sync_to_async(list)(
            QuizSessionStudent.objects.filter(quiz_session=self.session)
        )
        for student in updated_student_records:
            self.assertEqual(student.score, -1)  # score should be the default value of -1
