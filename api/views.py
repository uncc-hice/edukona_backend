from django.conf import settings
from django.db import transaction

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from api.models import *
from django.shortcuts import get_object_or_404
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from rest_framework.permissions import AllowAny
from rest_framework import status
from api.serializers import (
    QuizSessionStudentSerializer,
    QuestionMultipleChoiceSerializer,
    InstructorRecordingsSerializer,
    UpdateTranscriptSerializer,
)
from rest_framework import serializers
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from django.http import JsonResponse

import boto3
import json


class SignUpInstructor(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        new_user = request.data.pop("user", {})
        instructor = Instructor.objects.create(
            user=User.objects.create(**new_user), **request.data
        )
        user = get_object_or_404(User, id=instructor.user_id)
        user.set_password(new_user["password"])
        user.save()
        token = Token.objects.create(user=user)
        return JsonResponse(
            {"token": token.key, "user": user.id, "instructor": instructor.id}
        )


# class SignUpStudent(APIView):
#     permission_classes = [AllowAny]
#
#     def post(self, request):
#         new_user = request.data.pop('user', {})
#         student = Student.objects.create(user=User.objects.create(**new_user), **request.data)
#         user = get_object_or_404(User, id=student.user_id)
#         user.set_password(new_user['password'])
#         user.save()
#         token = Token.objects.create(user=user)
#         return JsonResponse({"token": token.key, "user": user.id, "student": student.id})


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, style={"input_type": "password"})


class CheckDeveloperStatus(APIView):

    def get(self, request):
        user = request.user
        if user.is_staff:
            return Response({"isDeveloper": True})
        else:
            return Response({"isDeveloper": False}, status=403)


class Login(APIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):

        # use a try catch block to catch the error, and return a 401 status code
        try:
            user = User.objects.get(username=request.data["username"])
        except User.DoesNotExist:
            return JsonResponse(
                {"detail": "User Not Found!"}, status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.check_password(request.data["password"]):
            return JsonResponse(
                {"detail": "User Not Found!"}, status=status.HTTP_400_BAD_REQUEST
            )
        token = Token.objects.get_or_create(user=user)
        if hasattr(user, "instructor"):
            return JsonResponse(
                {
                    "token": token[0].key,
                    "user": user.id,
                    "instructor": user.instructor.id,
                }
            )
        # else:
        #     return JsonResponse({"token": token[0].key, "user": user.id, "student": user.student.id})


class Logout(APIView):
    def post(self, request):
        token = request.user.auth_token
        token.delete()
        token.save()
        return JsonResponse({"message": "User logged out successfully"})


class QuizView(APIView):
    def post(self, request):
        settings = request.data.pop("settings", {})
        instructor = get_object_or_404(Instructor, user=request.user)
        new_quiz = Quiz.objects.create(instructor=instructor, **request.data)
        new_quiz.settings = Settings.objects.create(**settings)
        new_quiz.save()
        return JsonResponse(
            {"message": "Quiz created successfully", "quiz_id": new_quiz.id}
        )

    def get(self, request, quiz_id=None):
        if quiz_id:
            quiz = get_object_or_404(Quiz, id=quiz_id)
            return JsonResponse({"quiz": quiz.to_json()})
        else:
            instructor = get_object_or_404(Instructor, user=request.user)
            all_quizzes = Quiz.objects.filter(instructor=instructor)
            quiz_response = [quiz.to_json() for quiz in all_quizzes]
            return JsonResponse({"quizzes": quiz_response})

    def put(self, request, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id)
        quiz.__dict__.update(request.data)
        quiz.save()
        return JsonResponse({"message": "Quiz updated successfully"})

    def delete(self, request, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id)
        quiz.delete()
        return JsonResponse({"message": "Quiz deleted successfully"})


class QuestionView(APIView):
    def post(self, request):
        # Expecting request.data to be a list of questions
        if not isinstance(request.data, list):
            return JsonResponse(
                {"error": "Expected a list of questions"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_questions = []
        errors = []

        with transaction.atomic():  # Use a transaction to ensure all or nothing is created
            for question_data in request.data:
                try:
                    new_question = QuestionMultipleChoice.objects.create(
                        **question_data
                    )
                    created_questions.append(
                        {
                            "question_id": new_question.id,
                            "message": "Question created successfully",
                        }
                    )
                except (
                    Exception
                ) as e:  # Catch exceptions from invalid data or database errors
                    errors.append({"question_data": question_data, "error": str(e)})

        if errors:
            return JsonResponse(
                {"created_questions": created_questions, "errors": errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return JsonResponse(
            {
                "created_questions": created_questions,
                "message": "All questions created successfully",
            },
            status=status.HTTP_201_CREATED,
        )

    # Get method to question by id
    def get(self, request, question_id):
        question = get_object_or_404(QuestionMultipleChoice, id=question_id)
        question_dict = {
            "id": question.id,
            "question_text": question.question_text,
            "incorrect_answer_list": question.incorrect_answer_list,
            "correct_answer": question.correct_answer,
            "points": question.points,
            "quiz_id": question.quiz.id,
        }
        return JsonResponse({"questions": question_dict})

    # Put method to update text of a question by taking in an id
    def put(self, request, question_id):
        question = get_object_or_404(QuestionMultipleChoice, id=question_id)
        question.__dict__.update(request.data)
        question.save()
        return JsonResponse({"message": "Question updated successfully"})

    # delete method to delete question by id
    def delete(self, request, question_id):
        question = get_object_or_404(QuestionMultipleChoice, id=question_id)
        question.delete()
        return JsonResponse({"message": "Question deleted successfully"})


class AllQuizQuestionsView(APIView):
    def get(self, request, quiz_id):
        questions = QuestionMultipleChoice.objects.filter(quiz_id=quiz_id)
        serializer = QuestionMultipleChoiceSerializer(questions, many=True)
        return JsonResponse({"questions": serializer.data})


class InstructorView(APIView):

    def post(self, request):
        user_data = request.data.pop("user", {})
        new_instructor = Instructor.objects.create(
            user=User.objects.create(**user_data), **request.data
        )
        return JsonResponse(
            {
                "message": "Instructor created successfully",
                "instructor_id": new_instructor.id,
            }
        )

    def get(self, request, instructor_id):
        instructor = get_object_or_404(Instructor, id=instructor_id)
        instructor_dict = {
            "id": instructor.id,
            "user_id": instructor.user.id,
            "created_at": instructor.user.date_joined if instructor.user else None,
        }
        return JsonResponse({"instructor": instructor_dict})

    def put(self, request, instructor_id):
        instructor = get_object_or_404(Instructor, id=instructor_id)
        instructor.__dict__.update(request.data.get("instructor", {}))
        instructor.save()
        user = get_object_or_404(User, id=instructor.user_id)
        user.__dict__.update(request.data.get("user", {}))
        user.save()
        return JsonResponse({"message": "Instructor updated successfully"})

    def delete(self, request, instructor_id):
        instructor = get_object_or_404(Instructor, id=instructor_id)
        instructor.user.delete()
        instructor.delete()
        return JsonResponse({"message": "Instructor deleted successfully"})


# class StudentView(APIView):

# def post(self, request):
#     user_data = request.data.pop('user', {})
#     new_student = Student.objects.create(user=User.objects.create(**user_data), **request.data)
#     return JsonResponse({'message': 'Student created successfully', 'student_id': new_student.id})
#
# def get(self, request, student_id):
#     student = get_object_or_404(Student, id=student_id)
#     student_dict = {'id': student.id, 'user_id': student.user.id,
#                     'created_at': student.user.date_joined if student.user else None}
#     return JsonResponse({'student': student_dict})
#
# def put(self, request, student_id):
#     student = get_object_or_404(Student, id=student_id)
#     student.__dict__.update(request.data.get('student', {}))
#     student.save()
#     user = get_object_or_404(User, id=student.user_id)
#     user.__dict__.update(request.data.get('user', {}))
#     user.save()
#     return JsonResponse({'message': 'Student updated successfully'})
#
# def delete(self, request, student_id):
#     student = get_object_or_404(Student, id=student_id)
#     student.user.delete()
#     student.delete()
#     return JsonResponse({'message': 'Student deleted successfully'})


class UserResponseView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        student_data = request.data.pop("student", {})
        student = get_object_or_404(QuizSessionStudent, id=student_data["id"])
        question = get_object_or_404(
            QuestionMultipleChoice, id=request.data["question_id"]
        )
        selected_answer = request.data["selected_answer"]
        quiz_session = get_object_or_404(
            QuizSession, code=request.data["quiz_session_code"]
        )

        is_correct = selected_answer == question.correct_answer
        new_user_response = UserResponse.objects.create(
            student=student,
            is_correct=is_correct,
            quiz_session=quiz_session,
            question=question,
            selected_answer=selected_answer,
        )
        return JsonResponse(
            {
                "message": "User response created successfully",
                "response_id": new_user_response.id,
                "is_correct": is_correct,
            }
        )

    # def get(self, request, response_id):
    #     user_response = get_object_or_404(UserResponse, id=response_id)
    #
    #     response_dict = {
    #         'id': user_response.id, 'student_id': user_response.student.id, 'question_id': user_response.question.id,
    #         'selected_answer': user_response.selected_answer, 'is_correct': user_response.is_correct,
    #     }
    #     return JsonResponse({'response': response_dict})

    def put(self, request, response_id):
        user_response = get_object_or_404(
            UserResponse, id=response_id, student_id=request.data["student_id"]
        )

        is_correct = (
            request.data.get("selected_answer") == user_response.question.correct_answer
        )
        user_response.__dict__.update({"is_correct": is_correct, **request.data})
        user_response.save()

        return JsonResponse(
            {"message": "User response updated successfully", "is_correct": is_correct}
        )

    # def delete(self, request, response_id):
    #     user_response = get_object_or_404(UserResponse, id=response_id)
    #
    #     user_response.delete()
    #     return JsonResponse({'message': 'User response deleted successfully'})


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
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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


class StudentResponseCountView(APIView):
    def get(self, request, code):
        quiz_session = get_object_or_404(QuizSession, code=code)
        responses = quiz_session.responses.filter(
            question_id=quiz_session.current_question
        )

        counts = {}
        for response in responses:
            # Increment the count for the selected answer or initialize it to 0 if not found
            counts[response.selected_answer] = (
                counts.get(response.selected_answer, 0) + 1
            )

        return Response(counts, status=200)


class NextQuestionAPIView(APIView):
    def get(self, request, session_code):
        try:
            session = QuizSession.objects.get(code=session_code)
            served_questions_ids = session.served_questions.all().values_list(
                "id", flat=True
            )
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


class QuizSessionResults(APIView):
    def get(self, request, code):
        quiz_session = get_object_or_404(QuizSession, code=code)
        students = QuizSessionStudent.objects.filter(quiz_session=quiz_session)

        results = []
        for student in students:
            total_questions = UserResponse.objects.filter(student=student).count()
            correct_answers = UserResponse.objects.filter(
                student=student, is_correct=True
            ).count()

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

        quiz_sessions = QuizSession.objects.filter(
            quiz__instructor=instructor
        ).order_by("quiz_id", "start_time")

        quiz_sessions_data = [
            {
                "quiz_session_id": session.id,
                "quiz_id": session.quiz.id,
                "quiz_name": session.quiz.title,
                "start_time": (
                    session.start_time.isoformat() if session.start_time else None
                ),
                "end_time": session.end_time.isoformat() if session.end_time else None,
                "code": session.code,
            }
            for session in quiz_sessions
        ]

        return JsonResponse({"quiz_sessions": quiz_sessions_data})


class SettingsView(APIView):
    def get(self, request, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id)
        if not hasattr(quiz, "settings"):
            return JsonResponse({"error": "Quiz has no settings"}, status=404)
        return JsonResponse({"settings": quiz.settings.to_json()})

    def post(self, request, quiz_id):
        print(request.data)
        settings = request.data.pop("settings", {})
        new_settings = Settings.objects.create(**settings)
        quiz = get_object_or_404(Quiz, id=quiz_id)
        quiz.settings = new_settings
        quiz.save()
        return JsonResponse(
            {"message": "Settings created successfully", "settings_id": new_settings.id}
        )

    def patch(self, request, quiz_id):
        print(request.data)
        settings_data = request.data.get("settings", {})
        quiz = get_object_or_404(Quiz, id=quiz_id)

        if not hasattr(quiz, "settings"):
            return JsonResponse({"error": "Quiz has no settings to update"}, status=400)

        settings = quiz.settings

        for field, value in settings_data.items():
            setattr(settings, field, value)

        settings.save()
        return JsonResponse({"message": "Settings updated successfully"})


class UploadAudioView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        operation_id="upload_audio",
        summary="Upload an audio file",
        description="Uploads an audio file and saves it to the server.",
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {"file": {"type": "string", "format": "binary"}},
                "required": ["file"],
            }
        },
        responses={
            201: InstructorRecordingsSerializer,
            400: OpenApiTypes.OBJECT,  # Typically, a 400 would return an error object
        },
    )
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        instructor = get_object_or_404(Instructor, user=request.user)

        # Create the recording instance first to get the ID
        new_recording = InstructorRecordings.objects.create(instructor=instructor)

        # Sanitize and get the file details
        file = request.data["file"]
        file_name = self._sanitize_filename(file.name)
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME

        # Generate the S3 key (path)
        key = f"{str(instructor.id).zfill(5)}/{str(new_recording.id)}/{file_name}"

        try:
            # Upload to S3
            boto3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
            boto3_client.upload_fileobj(file, bucket_name, key)

            # Save the S3 path to the model instance
            new_recording.s3_path = key
            new_recording.save()

            # invoke a Lambda function and send the key as a parameter, make the invokation asynchronous
            lambda_client = boto3.client(
                "lambda",
                aws_access_key_id=settings.AWS_LAMBDA_INVOKER_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_LAMBDA_INVOKER_SECRET_ACCESS_KEY,
                region_name=settings.AWS_LAMBDA_INVOKER_REGION_NAME,
            )

            token = request.META.get("HTTP_AUTHORIZATION").split(" ")[1]
            lambda_client.invoke(
                FunctionName="TranscribeAudio",
                InvocationType="Event",
                Payload=json.dumps(
                    {
                        "s3_key": key,
                        "token": token,
                        "recording_id": str(new_recording.id),
                    }
                ),
            )

            return JsonResponse(
                InstructorRecordingsSerializer(new_recording).data, status=201
            )

        except Exception as e:
            transaction.set_rollback(True)
            return JsonResponse({"error": str(e)}, status=500)

    @staticmethod
    def _sanitize_filename(filename):
        """
        Sanitize the filename by removing special characters that may not be safe in S3 keys.
        """
        return "".join(
            char for char in filename if char.isalnum() or char in (" ", ".", "_")
        ).strip()


class UpdateTranscriptView(APIView):

    @extend_schema(
        operation_id="update_transcript",
        summary="Update the transcript of a recording",
        description="Updates the transcript of a recording with the given ID.",
        request=UpdateTranscriptSerializer,
        responses={
            200: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
    )
    def patch(self, request, recording_id):
        # Retrieve the InstructorRecordings instance by its ID
        recording = get_object_or_404(InstructorRecordings, id=recording_id)

        # Extract the transcript from the request data
        transcript = request.data.get("transcript", "")

        # Update the transcript field of the recording
        recording.transcript = transcript
        recording.save()

        # Return a success response with the updated data
        return JsonResponse(
            {
                "message": "Transcript updated successfully",
                "recording_id": recording.id,
            },
            status=status.HTTP_200_OK,
        )


class RecordingsView(APIView):

    @extend_schema(
        operation_id="get_recordings",
        summary="Get all recordings",
        description="Returns all recordings uploaded by the instructor.",
        responses={
            200: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        },
    )
    def get(self, request):
        instructor = request.user.instructor
        recordings = InstructorRecordings.objects.filter(
            instructor=instructor
        ).order_by("-uploaded_at")

        # Filter so that the serializer only returns the s3_path, uploaded_at, id

        serializer = InstructorRecordingsSerializer(
            recordings, many=True, fields=["id", "s3_path", "uploaded_at", "transcript"]
        )

        data = serializer.data

        for recording in data:
            if not recording.get("transcript"):
                recording["transcript"] = "pending"
            else:
                recording["transcript"] = "completed"

        return JsonResponse({"recordings": serializer.data})
