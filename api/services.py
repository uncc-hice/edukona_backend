from collections import defaultdict
from .models import UserResponse, QuizSession, Quiz, QuizSessionStudent


def score_session(session_id) -> dict:
    try:
        session = QuizSession.objects.get(id=session_id)
    except QuizSession.DoesNotExist:
        raise ValueError(f"No session with id {session_id}")

    try:
        quiz = Quiz.objects.get(id=session.quiz_id)
    except Quiz.DoesNotExist:
        raise ValueError(f"No quiz with id {session.quiz_id}")

    question_count = quiz.questions.count()
    if question_count == 0:
        raise ValueError(f"No questions in quiz {session.quiz_id}")

    responses = UserResponse.objects.filter(quiz_session_id=session_id)
    student_to_responses = defaultdict(list)

    for response in responses:
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

    for student_id, score in student_id_to_score.items():
        student = QuizSessionStudent.objects.get(id=student_id)
        student.score = score
        student.save()

    return student_id_to_score
