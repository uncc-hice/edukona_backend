import json
import logging
import random
import datetime

from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser
from urllib.parse import parse_qs
from rest_framework.authtoken.models import Token


from api.models import (
    QuizSession,
    QuizSessionStudent,
    UserResponse,
    QuestionMultipleChoice,
    QuizSessionQuestion,
)

logger = logging.getLogger(__name__)

from channels.db import database_sync_to_async


class QuizSessionInstructorConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.code = self.scope["url_route"]["kwargs"]["code"]
        self.group_name = f"quiz_session_instructor_{self.code}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.accept()

        settings = await self.get_settings(self.code)

        uc = await self.fetch_user_count()

        await self.send(
            text_data=json.dumps(
                {"type": "settings", "settings": settings, "user_count": uc}
            )
        )

    @database_sync_to_async
    def fetch_user_count(self):
        session = QuizSession.objects.get(code=self.code)
        return session.students.count()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        if "type" in data:
            if data["type"] == "next_question":
                await self.send_next_question()
            elif data["type"] == "update_order":
                await self.send_student_question_and_order(data)
            elif data["type"] == "start":
                await self.start_quiz()
            elif data["type"] == "end_quiz":
                await self.end_quiz()
            elif data["type"] == "current_question":
                await self.send_current_question()
            elif data["type"] == "delete_student":
                await self.delete_student(data["username"])
            elif data["type"] == "increase_duration":
                await self.add_to_duration(data["question_id"], data["extension"])

    async def send_student_question_and_order(self, data):
        order = data.get("order")
        if order:
            await self.channel_layer.group_send(
                f"quiz_session_{self.code}",
                {
                    "type": "next_question",
                    "question": await self.fetch_current_question(),
                    "quiz_session": await self.fetch_quiz_session(),
                    "order": order,
                },
            )

    async def delete_student(self, username):
        try:
            response = await self.delete_student_from_db(username)
            if response.get("status") == "success":
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "student_deleted",
                            "message": "Student deleted successfully",
                            "username": username,
                        }
                    )
                )
            else:
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "error",
                            "message": "Failed to delete student.",
                            "username": username,
                        }
                    )
                )
        except Exception as e:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "error",
                        "message": "An error occurred: " + str(e),
                        "username": username,
                    }
                )
            )

    @database_sync_to_async
    def delete_student_from_db(self, username):
        session = QuizSession.objects.get(code=self.code)
        student = QuizSessionStudent.objects.get(
            quiz_session=session, username=username
        )
        student.delete()
        return {"status": "success", "username": username}

    @database_sync_to_async
    def get_settings(self, code):
        session = QuizSession.objects.get(code=code)
        if session.quiz.settings:
            return session.quiz.settings.to_json()
        else:
            return {"timer": False, "timer_duration": 0, "live_bar_chart": False}

    async def send_current_question(self):
        question_data = await self.fetch_current_question()
        if question_data:
            await self.send(
                text_data=json.dumps(
                    {"type": "current_question", "question": question_data}
                )
            )

    @database_sync_to_async
    def fetch_current_question(self):
        session = QuizSession.objects.get(code=self.code)
        if session.current_question:
            return session.current_question.to_json()
        return None

    @database_sync_to_async
    def fetch_next_question(self):
        session = QuizSession.objects.get(code=self.code)
        served_questions_ids = session.served_questions.values_list("id", flat=True)
        next_question = (
            QuestionMultipleChoice.objects.exclude(id__in=served_questions_ids)
            .filter(quiz=session.quiz)
            .first()
        )
        if next_question:
            session.served_questions.add(next_question)
            session.current_question = next_question
            session.save()
            return next_question.to_json()
        return None

    async def send_next_question(self):
        question_data = await self.fetch_next_question()
        if question_data:
            await self.send(
                text_data=json.dumps(
                    {"type": "next_question", "question": question_data}
                )
            )
        else:
            print("Ending Quiz")
            await self.end_quiz()

    @database_sync_to_async
    def update_quiz_end_time(self):
        print("Updating end time for quiz with code", self.code)
        try:
            session = QuizSession.objects.get(code=self.code)
            session.end_time = timezone.now()
            session.save()
            return True
        except QuizSession.DoesNotExist:
            print("No quiz session found with the code:", self.code)
            return False

    async def end_quiz(self):
        if await self.update_quiz_end_time():
            grades = await self.fetch_grades()
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "quiz_ended",
                        "grades": grades,
                    }
                )
            )
        else:
            print("Failed to end the quiz; session not found.")

    @database_sync_to_async
    def fetch_grades(self):
        try:
            session = QuizSession.objects.get(code=self.code)
        except QuizSession.DoesNotExist:
            return {}

        students = session.students.all()
        grade_buckets = {"100": [], "80": [], "60": [], "40": [], "20": [], "0": []}

        for student in students:
            responses = student.responses.all()
            total_responses = responses.count()
            correct_responses = responses.filter(is_correct=True).count()

            # Calculate percentage
            if total_responses > 0:
                percentage = (correct_responses / total_responses) * 100
            else:
                percentage = 0

            # Determine grade bucket
            if percentage >= 90:
                grade = "100"
            elif percentage >= 70:
                grade = "80"
            elif percentage >= 50:
                grade = "60"
            elif percentage >= 30:
                grade = "40"
            elif percentage >= 10:
                grade = "20"
            else:
                grade = "0"

            # Append student name to the appropriate bucket
            grade_buckets[grade].append(student.username)

        return grade_buckets

    async def start_quiz(self):
        await self.channel_layer.group_send(
            f"quiz_session_{self.code}", {"type": "quiz_started"}
        )

        await self.send(
            text_data=json.dumps(
                {"type": "quiz_started", "message": "Quiz has started!"}
            )
        )

    async def student_joined(self, event):
        event_message = json.loads(event["text"])
        await self.send(
            text_data=json.dumps(
                {
                    "type": "student_joined",
                    "username": event_message["username"],
                    "message": f"Student {event_message['username']} joined the session.",
                }
            )
        )

    @database_sync_to_async
    def fetch_quiz_session(self):
        session = QuizSession.objects.get(code=self.code)
        return session.to_json()

    async def user_response(self, event):
        await self.send(
            text_data=json.dumps(
                {"type": "user_response", "response": event["response"]}
            )
        )

    @database_sync_to_async
    def fetch_question_results(self, question_id):
        responses = UserResponse.objects.all().filter(
            quiz_session__code=self.code, question_id=question_id
        )
        answers = responses.distinct("selected_answer")
        answer_counts = {}

        for response in answers:
            answer_counts[response.selected_answer] = responses.filter(
                selected_answer=response.selected_answer
            ).count()

        return {"total_responses": responses.count(), "answers": answer_counts}

    async def update_answers(self, event):
        results = await self.fetch_question_results(event["question_id"])
        await self.send(
            text_data=json.dumps({"type": "update_answers", "data": results})
        )

    @database_sync_to_async
    def add_to_duration_db(self, question_id, extension: int):
        quiz_session_question = QuizSessionQuestion.objects.get(
            quiz_session__code=self.code, question__id=question_id
        )
        quiz_session_question.extension += extension
        quiz_session_question.save()
        return quiz_session_question

    async def add_to_duration(self, question_id, extension: int):
        quiz_session_question = await self.add_to_duration_db(question_id, extension)
        response = {
            "type": "time_extended",
            "question_opened_at": quiz_session_question.opened_at.isoformat(),
            "extension": quiz_session_question.extension,
        }
        await self.send(text_data=json.dumps(response))


class StudentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.code = self.scope["url_route"]["kwargs"].get("code")
        self.group_name = f"quiz_session_{self.code}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        if "type" in data and data["type"] == "join":
            await self.process_student_join(data)
        elif "type" in data and data["type"] == "response":
            await self.submit_response(data)
        elif "type" in data and data["type"] == "skip_question":
            await self.skip_question(data)

    async def submit_response(self, data):
        response = await self.create_user_response(data)

        if response["status"] == "success":
            await self.channel_layer.group_send(
                f"quiz_session_instructor_{self.code}",
                {
                    "type": "update_answers",
                    "question_id": response["question_id"],
                },
            )
            await self.channel_layer.group_send(
                f"quiz_session_instructor_{self.code}",
                {
                    "type": "user_response",
                    "response": data.get("data").get("selected_answer"),
                },
            )

            await self.check_and_grant_skip_power_up(data["data"]["student"]["id"])
        await self.send(text_data=json.dumps(response))

    def is_question_open(self, question: QuestionMultipleChoice):
        try:
            quiz_session_question = QuizSessionQuestion.objects.get(
                question=question, quiz_session__code=self.code
            )
        except QuizSessionQuestion.DoesNotExist:
            logger.warn(
                f"Attempt to check if non existant question is open. question_id={question.id} session_code={self.code}"
            )
            return False
        except QuizSessionQuestion.MultipleObjectsReturned:
            logger.error(
                f"Multiple QuizSessionQuestion objects returned for unique combination. \
                question_id={question.id} session_code={self.code}"
            )
            return False

        extension = datetime.timedelta(seconds=quiz_session_question.extension)
        adjusted_open_time = quiz_session_question.opened_at + extension
        return (timezone.now() - adjusted_open_time).seconds < question.duration

    @database_sync_to_async
    def create_user_response(self, data):
        data = data["data"]
        student_data = data.get("student", {})
        student_id = student_data.get("id")
        student = QuizSessionStudent.objects.get(id=student_id)
        question = QuestionMultipleChoice.objects.get(id=data["question_id"])
        selected_answer = data.get("selected_answer")
        quiz_session = QuizSession.objects.get(code=data["quiz_session_code"])

        if not self.is_question_open(question):
            return {
                "status": "failed",
                "type": "question_locked",
                "question_id": question.id,
            }

        is_correct = selected_answer == question.correct_answer
        user_response, created = UserResponse.objects.get_or_create(
            student=student,
            quiz_session=quiz_session,
            question=question,
        )
        user_response.selected_answer = selected_answer
        user_response.is_correct = is_correct

        user_response.save()

        return {
            "status": "success",
            "message": "User response created successfully",
            "response_id": user_response.id,
            "question_id": data["question_id"],
            "is_correct": is_correct,
        }

    @database_sync_to_async
    def create_student_session_entry(self, username, code):
        try:
            session = QuizSession.objects.get(code=code)
            # studentUser = Student.objects.get(user_id=user_id)
            student = QuizSessionStudent.objects.create(
                username=username, quiz_session=session
            )
            return {
                "status": "success",
                "message": "Student created successfully",
                "student_id": student.id,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def process_student_join(self, data):
        username = data.get("username")
        # user_id = data.get('user_id')
        response = await self.create_student_session_entry(username, self.code)

        if response["status"] == "success":
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "success",
                        "message": "Student joined successfully",
                        "student_id": response["student_id"],
                    }
                )
            )

            await self.channel_layer.group_send(
                f"quiz_session_instructor_{self.code}",
                {"type": "student.joined", "text": json.dumps({"username": username})},
            )

    async def next_question(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "next_question",
                    "question": event["question"],
                    "quiz_session": event["quiz_session"],
                    "order": event["order"],
                }
            )
        )

    async def quiz_started(self, event):
        await self.send(text_data=json.dumps({"type": "quiz_started"}))

    async def time_extended(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def get_student(self, student_id):
        return QuizSessionStudent.objects.get(id=student_id)

    async def check_and_grant_skip_power_up(self, student_id):
        session_settings = await self.get_session_settings()
        correct_responses = await self.get_correct_responses(student_id)
        student = await self.get_student(student_id)
        if session_settings.get("skip_question"):
            if session_settings.get("skip_question_logic") == "streak":
                if (
                    student.skip_count < session_settings.get("skip_count_per_student")
                    and correct_responses
                    % session_settings.get("skip_question_streak_count")
                    == 0
                ):
                    grant_response = await self.grant_skip_power_up(student_id)
                    if grant_response.get("status") == "success":
                        await self.send(
                            text_data=json.dumps(
                                {
                                    "type": "skip_power_up_granted",
                                    "skip_count": grant_response.get("skip_count"),
                                }
                            )
                        )
            elif session_settings.get("skip_question_logic") == "random":
                skip_percentage = session_settings.get(
                    "skip_question_percentage", 0.2
                )  # Default to 50% if not set
                if (
                    student.skip_count < session_settings.get("skip_count_per_student")
                    and random.random() < skip_percentage
                ):
                    grant_response = await self.grant_skip_power_up(student_id)
                    if grant_response.get("status") == "success":
                        await self.send(
                            text_data=json.dumps(
                                {
                                    "type": "skip_power_up_granted",
                                    "skip_count": grant_response.get("skip_count"),
                                }
                            )
                        )

    @database_sync_to_async
    def grant_skip_power_up(self, student_id):
        student = QuizSessionStudent.objects.get(id=student_id)
        student.skip_count += 1
        student.save()
        return {"status": "success", "skip_count": student.skip_count}

    @database_sync_to_async
    def get_session_settings(self):
        session = QuizSession.objects.get(code=self.code)
        return session.quiz.settings.to_json()

    @database_sync_to_async
    def get_correct_responses(self, student_id):
        student = QuizSessionStudent.objects.get(id=student_id)
        responses = student.responses.all()
        return responses.filter(is_correct=True, skipped_question=False).count()

    async def skip_question(self, data):
        student = data.get("data").get("student")

        skip_count = await self.get_skip_count(student.get("id"))
        session_settings = await self.get_session_settings()

        if skip_count < session_settings.get("skip_count_per_student"):
            question_marked = await self.mark_question_as_skipped_and_correct(data)
            print(question_marked)
            if question_marked:
                await self.increment_skip_count(student.get("id"))
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "skip_power_up_used",
                            "message": "Question skipped successfully.",
                        }
                    )
                )
        else:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "skip_power_up_error",
                        "message": "You have already used all your skip power ups for this session.",
                    }
                )
            )

    @database_sync_to_async
    def get_skip_count(self, student_id):
        student = QuizSessionStudent.objects.get(id=student_id)
        return student.skip_count

    @database_sync_to_async
    def increment_skip_count(self, student_id):
        student = QuizSessionStudent.objects.get(id=student_id)
        student.skip_count += 1
        student.save()

    @database_sync_to_async
    def mark_question_as_skipped_and_correct(self, data):
        try:
            data = data["data"]
            student_data = data.pop("student", {})
            student_id = student_data.get("id")
            student = QuizSessionStudent.objects.get(id=student_id)
            question = QuestionMultipleChoice.objects.get(id=data["question_id"])
            quiz_session = QuizSession.objects.get(code=data["quiz_session_code"])

            UserResponse.objects.create(
                student=student,
                is_correct=True,
                quiz_session=quiz_session,
                question=question,
                selected_answer="skipped",
                skipped_question=True,
            )

            return True
        except Exception as e:
            print(e)
            return False


@database_sync_to_async
def get_user_from_token(token_key):
    try:
        token = Token.objects.get(key=token_key)
        return token.user
    except Token.DoesNotExist:
        return AnonymousUser()


class RecordingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        query_string = self.scope["query_string"].decode()
        params = parse_qs(query_string)
        token_key = params.get("token")

        if token_key:
            token_key = token_key[0]
            self.user = await get_user_from_token(token_key)
        else:
            self.user = AnonymousUser()

        if self.user.is_anonymous:
            await self.close()
            logger.warning("WebSocket connection rejected due to anonymous user.")
        else:
            self.group_name = f"recordings_{self.user.id}"
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            logger.info(
                f"WebSocket connection accepted for user {self.user.id}: {self.channel_name}"
            )

    async def disconnect(self, close_code):
        # Leave the transcripts group
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info(f"WebSocket disconnected: {self.channel_name}")

    async def receive(self, text_data):
        logger.debug(f"Received WebSocket message: {text_data}")
        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            if message_type == "transcript_completed":
                # Extract required fields
                recording_id = data.get("recording_id")
                transcript_status = data.get("transcript_status")

                if recording_id and transcript_status:
                    # Broadcast the event to all clients in the group (i.e. this will be sent to the front-end)
                    await self.channel_layer.group_send(
                        self.group_name,
                        {"type": "transcript_completed_event", "message": data},
                    )
                else:
                    # Send error if required fields are missing
                    error_message = (
                        "Invalid data: recording_id and transcript_url are required."
                    )
                    logger.error(error_message)
                    await self.send(text_data=json.dumps({"error": error_message}))
            elif message_type == "quiz_creation_completed":
                # Extract required fields
                recording_id = data.get("recording_id")
                quiz_creation_status = data.get("quiz_creation_status")

                if recording_id and quiz_creation_status:
                    # Broadcast the event to all clients in the group (i.e. this will be sent to the front-end)
                    await self.channel_layer.group_send(
                        self.group_name,
                        {"type": "quiz_creation_completed_event", "message": data},
                    )
                else:
                    # Send error if required fields are missing
                    error_message = "Invalid data: recording_id and quiz_creation_status are required."
                    logger.error(error_message)
                    await self.send(text_data=json.dumps({"error": error_message}))
            else:
                # Handle unknown message types
                error_message = f"Unknown message type: {message_type}"
                logger.error(error_message)
                await self.send(text_data=json.dumps({"error": error_message}))

        except json.JSONDecodeError:
            # Handle JSON parsing errors
            error_message = "Invalid JSON format."
            logger.error(error_message)
            await self.send(text_data=json.dumps({"error": error_message}))

        except Exception as e:
            # Log any other exceptions
            logger.exception("An error occurred in receive method.")
            await self.send(text_data=json.dumps({"error": str(e)}))

    async def transcript_completed_event(self, event):
        # Send the transcript_completed event to WebSocket clients (i.e. this will be sent to the front-end)
        message = event["message"]
        logger.info(f"Broadcasting transcript_completed event: {message}")
        await self.send(text_data=json.dumps(message))

    async def quiz_creation_completed_event(self, event):
        # Send the quiz_creation_completed event to WebSocket clients (i.e. this will be sent to the front-end)
        message = event["message"]
        logger.info(f"Broadcasting quiz_creation_completed event: {message}")
        await self.send(text_data=json.dumps(message))
