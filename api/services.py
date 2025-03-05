from typing import Dict

from django.db.models import Case, Count, IntegerField, Max, When

from .models import QuizSessionQuestion, QuizSessionStudent, UserResponse


def score_session(session_id) -> Dict[int, int]:
    question_ids = QuizSessionQuestion.objects.filter(
        quiz_session_id=session_id, skipped=False
    ).values_list("question_id", flat=True)
    if not question_ids:
        raise ValueError(f"Quiz session with id {session_id} does not exist")

    # Get the latest response for each question per student
    latest_responses = (
        UserResponse.objects.filter(quiz_session_id=session_id, question_id__in=question_ids)
        .values("student_id", "question_id")
        .annotate(max_id=Max("id"))
    )

    # Get the actual response objects for the latest responses
    responses = UserResponse.objects.filter(id__in=[res["max_id"] for res in latest_responses])

    # Calculate the score for each student
    student_scores = responses.values("student_id").annotate(
        score=Count(Case(When(is_correct=True, then=1), output_field=IntegerField()))
    )

    student_ids = QuizSessionStudent.objects.filter(quiz_session_id=session_id).values_list(
        "id", flat=True
    )
    student_id_to_score = {id: 0 for id in student_ids}
    student_id_to_score.update({entry["student_id"]: entry["score"] for entry in student_scores})

    students_to_update = [
        QuizSessionStudent(id=student_id, score=score)
        for student_id, score in student_id_to_score.items()
    ]

    QuizSessionStudent.objects.bulk_update(students_to_update, ["score"])

    return student_id_to_score
