import uuid

from django.db import transaction
from rest_framework.response import Response
from rest_framework.views import APIView
from api.models import *
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework import status

from api.permissions import IsRecordingOwner
from api.serializers import QuizSessionStudentSerializer, LectureSummarySerializer
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes


class StudentResponseCountView(APIView):
    def get(self, request, code):
        quiz_session = get_object_or_404(QuizSession, code=code)
        responses = quiz_session.responses.filter(question_id=quiz_session.current_question)

        counts = {}
        for response in responses:
            # Increment the count for the selected answer or initialize it to 0 if not found
            counts[response.selected_answer] = counts.get(response.selected_answer, 0) + 1

        return Response(counts, status=200)


class StoreColorAPIView(APIView):
    def post(self, request, session_code):
        session = get_object_or_404(QuizSession, code=session_code)
        question_id = request.data.get("question_id")
        order = request.data.get("order")

        # Ensure that session.question_colors is a dictionary

        # Add the new key-value pair
        session.question_colors[question_id] = order

        # Save the updated session
        session.save()

        return Response({"message": "Colors stored successfully."}, status=200)


class QuizSessionView(APIView):
    def post(self, request):
        try:
            quiz_id = request.data.get("quiz_id")
            quiz = get_object_or_404(Quiz, id=quiz_id)
            new_quiz_session = QuizSession.objects.create(quiz=quiz)
            new_quiz_session.code = QuizSession.generate_unique_code(new_quiz_session)
            new_quiz_session.save()

            return Response(
                {
                    "message": "Quiz session created successfully",
                    "quiz_session_id": new_quiz_session.id,
                    "code": new_quiz_session.code,
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QuizSessionStudentView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, code):
        quiz_session = get_object_or_404(QuizSession, code=code)
        quiz_session_dict = {
            "id": quiz_session.id,
            "quiz_id": quiz_session.quiz.id,
            "code": quiz_session.code,
            "start_time": quiz_session.start_time,
            "end_time": quiz_session.end_time,
        }
        return JsonResponse({"quiz_session": quiz_session_dict})

    def post(self, request, code):
        quiz_session = get_object_or_404(QuizSession, code=code)
        new_quiz_session_student = QuizSessionStudent.objects.create(
            **request.data, quiz_session=quiz_session
        )
        return JsonResponse(
            {
                "message": "Quiz session student created successfully",
                "quiz_session_id": new_quiz_session_student.quiz_session.id,
                "quiz_session_student_id": new_quiz_session_student.id,
            }
        )


class QuizSessionStudentInstructorView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, code):
        quiz_session = get_object_or_404(QuizSession, code=code)
        all_students = quiz_session.students.all()
        serializer = QuizSessionStudentSerializer(all_students, many=True)
        return JsonResponse({"students": serializer.data})


# create a new class QuizWithQuestionsAPIView
# just add a get function


class QuizSessionInstructorView(APIView):
    def get(self, request, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id)
        questions = QuestionMultipleChoice.objects.filter(quiz=quiz)
        questions_data = []
        for question in questions:
            data = question.to_json()
            questions_data.append(data)
        quiz_dict = {"quiz": quiz.to_json(), "questions": questions_data}

        return Response(quiz_dict, status=200)


class QuizSessionResults(APIView):
    def get(self, request, code):
        quiz_session = get_object_or_404(QuizSession, code=code)
        students = QuizSessionStudent.objects.filter(quiz_session=quiz_session)

        results = []
        for student in students:
            total_questions = UserResponse.objects.filter(student=student).count()
            correct_answers = UserResponse.objects.filter(student=student, is_correct=True).count()

            results.append(
                {
                    "student_username": student.username,
                    "correct_answers": correct_answers,
                    "total_questions": total_questions,
                }
            )

        return JsonResponse({"results": results})


class QuizSessionsByInstructorView(APIView):
    def get(self, request):
        instructor = request.user.instructor

        quiz_sessions = QuizSession.objects.filter(quiz__instructor=instructor).order_by(
            "quiz_id", "start_time"
        )

        quiz_sessions_data = [
            {
                "quiz_session_id": session.id,
                "quiz_id": session.quiz.id,
                "quiz_name": session.quiz.title,
                "start_time": (session.start_time.isoformat() if session.start_time else None),
                "end_time": session.end_time.isoformat() if session.end_time else None,
                "code": session.code,
            }
            for session in quiz_sessions
        ]

        return JsonResponse({"quiz_sessions": quiz_sessions_data})


class QuizSessionsByQuizView(APIView):
    @extend_schema(
        operation_id="quiz-sessions",
        description="Returns all sessions of the quiz with the specified id",
        responses={
            200: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
        },
    )
    def get(self, request, quiz_id):
        instructor = request.user.instructor
        quiz = get_object_or_404(Quiz, id=quiz_id)
        if instructor != quiz.instructor:
            return JsonResponse(
                {"message": "You do not have permission to access this resource"},
                status=403,
            )
        sessions = QuizSession.objects.filter(quiz=quiz).order_by("start_time")
        quiz_sessions_data = [
            {
                "quiz_session_id": session.id,
                "quiz_id": session.quiz.id,
                "quiz_name": session.quiz.title,
                "start_time": (session.start_time.isoformat() if session.start_time else None),
                "end_time": (session.start_time.isoformat() if session.end_time else None),
                "code": session.code,
                "num_of_participants": session.students.count(),
            }
            for session in sessions
        ]

        return JsonResponse({"quiz_sessions": quiz_sessions_data})


class NextQuestionAPIView(APIView):
    def get(self, request, session_code):
        try:
            session = QuizSession.objects.get(code=session_code)
            served_questions_ids = session.served_questions.all().values_list("id", flat=True)
            next_question = (
                QuestionMultipleChoice.objects.exclude(id__in=served_questions_ids)
                .filter(quiz=session.quiz)
                .first()
            )

            if next_question:
                # Mark the question as served
                session.served_questions.add(next_question)
                session.current_question = next_question
                session.save()
                return Response(next_question.to_json(), status=200)
            else:
                return Response({"message": "No more questions."}, status=204)
        except QuizSession.DoesNotExist:
            return Response({"message": "Invalid session code."}, status=404)


class StudentQuestion(APIView):
    permission_classes = [AllowAny]

    def get(self, request, session_code, question_id=0):
        session = get_object_or_404(QuizSession, code=session_code)
        current_question = session.current_question
        if question_id == 0:
            if current_question:
                order = session.question_colors.get(str(current_question.id))
                return Response(
                    {"question": current_question.to_json(), "order": order}, status=200
                )
            else:
                return Response({"message": "No more questions."}, status=204)
        else:
            if current_question.id != question_id:
                if current_question:
                    return Response(current_question.to_json(), status=200)
                else:
                    return Response({"message": "No more questions."}, status=204)
            else:
                return Response({"message": "Bad Request"}, status=404)


class DeleteQuizSession(APIView):
    def delete(self, request, code):
        try:
            session = QuizSession.objects.get(code=code)
            if request.user.instructor == session.quiz.instructor:
                session.delete()
                return Response(
                    {"message": "Quiz session deleted successfully."},
                    status=status.HTTP_204_NO_CONTENT,
                )
            else:
                return Response(
                    {"message": "You cannot delete quiz sessions you did not create."},
                    status=403,
                )
        except QuizSession.DoesNotExist:
            return Response({"message": "Invalid session code."}, status=404)
        except Exception as e:
            return Response({"message": f"{str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LectureSummaryView(APIView):
    permission_classes = [IsRecordingOwner]

    @extend_schema(
        operation_id="create_lecture_summary",
        summary="Create a lecture summary",
        description="Creates a summary for a specific recording using the recording ID.",
        request=LectureSummarySerializer,
        responses={
            201: OpenApiTypes.OBJECT,  # Successful creation response
            400: OpenApiTypes.OBJECT,  # Error response for bad request
            404: OpenApiTypes.OBJECT,  # Error response when recording is not found
            500: OpenApiTypes.OBJECT,  # Error response for server error
        },
    )
    def post(self, request, recording_id):
        summary = request.data.get("summary")

        # Validate required fields
        if not summary or not recording_id:
            return Response(
                {"error": "Summary and recording_id are required fields."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Wrap in atomic transaction to ensure consistency
        try:
            with transaction.atomic():
                recording = InstructorRecordings.objects.get(id=recording_id)
                lecture_summary = LectureSummary.objects.create(
                    summary=summary, recording_id=recording
                )
                return Response(
                    {
                        "id": lecture_summary.id,
                        "recording_id": lecture_summary.recording_id.id,
                        "created_at": lecture_summary.created_at,
                    },
                    status=status.HTTP_201_CREATED,
                )
        except InstructorRecordings.DoesNotExist:
            return Response({"error": "Recording not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        operation_id="get_lecture_summary",
        summary="Get a lecture summary",
        description="Get a summary for a specific recording using the recording ID.",
        request=LectureSummarySerializer,
        responses={
            200: OpenApiTypes.OBJECT,  # Successful retrieval of data.
            404: OpenApiTypes.OBJECT,  # Response when the lecture summary is not found.
            500: OpenApiTypes.OBJECT,  # Response when there is an error from the server side.
        },
    )
    def get(self, request, recording_id):
        try:
            lecture_summary = LectureSummary.objects.filter(recording_id_id=recording_id)
            serializer = LectureSummarySerializer(lecture_summary, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except LectureSummary.DoesNotExist:
            return Response(
                {"error": "The lecture summary was not found."}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
