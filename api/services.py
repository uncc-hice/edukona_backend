from collections import defaultdict
from typing import Dict
from .models import UserResponse, QuizSessionStudent, QuizSessionQuestion, QuizSession


def score_session(session_id) -> Dict[int, int]:
    try:
        questions = QuizSessionQuestion.objects.filter(quiz_session_id=session_id, unlocked=True)
    except QuizSession.DoesNotExist:
        return ValueError(f"Quiz session with id {session_id} does not exist")

    question_ids = set(q.question_id for q in questions)

    responses = UserResponse.objects.filter(quiz_session_id=session_id)
    student_to_responses = defaultdict(list)

    for response in responses:
        if response.question_id not in question_ids:
            continue  # Skip responses to questions that were skipped
        student_to_responses[response.student_id].append(response)

    # Among responses that have the same question_id, keep the one with the highest id
    def trim_responses(response_list):
        question_to_responses = defaultdict(list)
        for response in response_list:
            question_to_responses[response.question_id].append(response)
        trimmed_responses = [
            max(q_responses, key=lambda r: r.id) for q_responses in question_to_responses.values()
        ]
        return trimmed_responses

    for student_id, responses in student_to_responses.items():
        student_to_responses[student_id] = trim_responses(responses)

    def score_responses(responses):
        return sum(1 for response in responses if response.is_correct)

    student_id_to_score = {
        student_id: score_responses(responses)
        for student_id, responses in student_to_responses.items()
    }

    students_to_update = [
        QuizSessionStudent(id=student_id, score=score)
        for student_id, score in student_id_to_score.items()
    ]

    QuizSessionStudent.objects.bulk_update(students_to_update, ["score"])

    return student_id_to_score
