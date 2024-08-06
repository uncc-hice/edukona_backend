import json
import logging
import random

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from api.models import QuizSession, QuizSessionStudent, UserResponse

logger = logging.getLogger(__name__)

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import QuizSession, QuestionMultipleChoice, Student


class QuizSessionInstructorConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.code = self.scope['url_route']['kwargs']['code']
        self.group_name = f'quiz_session_instructor_{self.code}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.accept()

        settings = await self.get_settings(self.code)

        uc = await self.fetch_user_count()

        await self.send(text_data=json.dumps({
            'type': 'settings',
            'settings': settings,
            'user_count': uc
        }))

    @database_sync_to_async
    def fetch_user_count(self):
        session = QuizSession.objects.get(code=self.code)
        return session.students.count()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        if 'type' in data:
            if data['type'] == 'next_question':
                await self.send_next_question()
            elif data['type'] == 'update_order':
                await self.send_student_question_and_order(data)
            elif data['type'] == 'start':
                await self.start_quiz()
            elif data['type'] == 'end_quiz':
                await self.end_quiz()
            elif data['type'] == 'current_question':
                await self.send_current_question()
            elif data['type'] == 'delete_student':
                await self.delete_student(data['username'])

    async def send_student_question_and_order(self, data):
        order = data.get('order')
        if order:
            await self.channel_layer.group_send(f'quiz_session_{self.code}', {
                'type': 'next_question',
                'question': await self.fetch_current_question(),
                'quiz_session': await self.fetch_quiz_session(),
                'order': order
            })

    async def delete_student(self, username):
        try:
            response = await self.delete_student_from_db(username)
            if response.get('status') == 'success':
                await self.send(text_data=json.dumps({
                    'type': 'student_deleted',
                    'message': 'Student deleted successfully',
                    'username': username
                }))
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Failed to delete student.',
                    'username': username
                }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'An error occurred: ' + str(e),
                'username': username
            }))

    @database_sync_to_async
    def delete_student_from_db(self, username):
        session = QuizSession.objects.get(code=self.code)
        student = QuizSessionStudent.objects.get(quiz_session=session, username=username)
        student.delete()
        return {'status': 'success', 'username': username}
    @database_sync_to_async
    def get_settings(self, code):
        session = QuizSession.objects.get(code=code)
        if session.quiz.settings:
            return session.quiz.settings.to_json()
        else:
            return {
                "timer": False,
                "timer_duration": 0,
                "live_bar_chart": False
            }

    async def send_current_question(self):
        question_data = await self.fetch_current_question()
        if question_data:
            await self.send(text_data=json.dumps({
                'type': 'current_question',
                'question': question_data
            }))

    @database_sync_to_async
    def fetch_current_question(self):
        session = QuizSession.objects.get(code=self.code)
        if session.current_question:
            return session.current_question.to_json()
        return None

    @database_sync_to_async
    def fetch_next_question(self):
        session = QuizSession.objects.get(code=self.code)
        served_questions_ids = session.served_questions.values_list('id', flat=True)
        next_question = QuestionMultipleChoice.objects.exclude(id__in=served_questions_ids).filter(
            quiz=session.quiz).first()
        if next_question:
            session.served_questions.add(next_question)
            session.current_question = next_question
            session.save()
            return next_question.to_json()
        return None

    async def send_next_question(self):
        question_data = await self.fetch_next_question()
        if question_data:
            await self.send(text_data=json.dumps({
                'type': 'next_question',
                'question': question_data
            }))
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
            await self.send(text_data=json.dumps({
                'type': 'quiz_ended'
            }))
        else:
            print("Failed to end the quiz; session not found.")

    async def start_quiz(self):
        await self.channel_layer.group_send(f'quiz_session_{self.code}', {
            'type': 'quiz_started'
        })

        await self.send(text_data=json.dumps({
            'type': 'quiz_started',
            'message': 'Quiz has started!'
        }))

    async def student_joined(self, event):
        event_message = json.loads(event['text'])
        await self.send(text_data=json.dumps({
            'type': 'student_joined',
            'username': event_message['username'],
            'message': f"Student {event_message['username']} joined the session."
        }))

    @database_sync_to_async
    def fetch_quiz_session(self):
        session = QuizSession.objects.get(code=self.code)
        return session.to_json()

    async def user_response(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_response',
            'response': event['response']
        }))


class StudentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.code = self.scope['url_route']['kwargs'].get('code')
        self.group_name = f'quiz_session_{self.code}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        if 'type' in data and data['type'] == 'join':
            await self.process_student_join(data)
        elif 'type' in data and data['type'] == 'response':
            await self.submit_response(data)
        elif 'type' in data and data['type'] == 'skip_question':
            await self.skip_question(data)

    async def submit_response(self, data):
        response = await self.create_user_response(data)
        await self.channel_layer.group_send(
            f'quiz_session_instructor_{self.code}',
            {
                'type': 'user_response',
                'response': data.get('data').get('selected_answer'),
            }
        )
        await self.send(text_data=json.dumps(response))

        print(data)
        await self.check_and_grant_skip_power_up(data['data']['student']['id'])

    @database_sync_to_async
    def create_user_response(self, data):
        data = data['data']
        student_data = data.get('student', {})
        student_id = student_data.get('id')
        print(student_id)
        student = QuizSessionStudent.objects.get(id=student_id)
        question = QuestionMultipleChoice.objects.get(id=data['question_id'])
        selected_answer = data.get('selected_answer')
        quiz_session = QuizSession.objects.get(code=data['quiz_session_code'])

        is_correct = selected_answer == question.correct_answer
        new_user_response = UserResponse.objects.create(
            student=student,
            is_correct=is_correct,
            quiz_session=quiz_session,
            question=question,
            selected_answer=selected_answer
        )

        return {'message': 'User response created successfully', 'response_id': new_user_response.id,
                'is_correct': is_correct}

    @database_sync_to_async
    def create_student_session_entry(self, username, code):
        try:
            session = QuizSession.objects.get(code=code)
            #studentUser = Student.objects.get(user_id=user_id)
            student = QuizSessionStudent.objects.create(username=username, quiz_session=session)
            return {'status': 'success', 'message': 'Student created successfully', 'student_id': student.id}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    async def process_student_join(self, data):
        username = data.get('username')
        #user_id = data.get('user_id')
        response = await self.create_student_session_entry(username, self.code)

        if response['status'] == 'success':
            await self.send(text_data=json.dumps({
                'type': 'success',
                'message': 'Student joined successfully',
                'student_id': response['student_id']
            }))

            await self.channel_layer.group_send(
                f'quiz_session_instructor_{self.code}',
                {
                    'type': 'student.joined',
                    'text': json.dumps({'username': username})
                }
            )

    async def next_question(self, event):
        await self.send(text_data=json.dumps({
            'type': 'next_question',
            'question': event['question'],
            'quiz_session': event['quiz_session'],
            'order': event['order']
        }))

    async def quiz_started(self, event):
        await self.send(text_data=json.dumps({
            'type': 'quiz_started'
        }))

    @database_sync_to_async
    def get_student(self, student_id):
        return QuizSessionStudent.objects.get(id=student_id)

    async def check_and_grant_skip_power_up(self, student_id):
        session_settings = await self.get_session_settings()
        correct_responses = await self.get_correct_responses(student_id)
        student = await self.get_student(student_id)
        if session_settings.get('skip_question'):
            if session_settings.get('skip_question_logic') == 'streak':
                if student.skip_count < session_settings.get(
                        'skip_count_per_student') and correct_responses % session_settings.get(
                        'skip_question_streak_count') == 0:
                    grant_response = await self.grant_skip_power_up(student_id)
                    if grant_response.get('status') == 'success':
                        await self.send(text_data=json.dumps({
                            'type': 'skip_power_up_granted',
                            'skip_count': grant_response.get('skip_count')
                        }))
            elif session_settings.get('skip_question_logic') == 'random':
                skip_percentage = session_settings.get('skip_question_percentage', 0.2)  # Default to 50% if not set
                if student.skip_count < session_settings.get('skip_count_per_student') and \
                        random.random() < skip_percentage:
                    grant_response = await self.grant_skip_power_up(student_id)
                    if grant_response.get('status') == 'success':
                        await self.send(text_data=json.dumps({
                            'type': 'skip_power_up_granted',
                            'skip_count': grant_response.get('skip_count')
                        }))

    @database_sync_to_async
    def grant_skip_power_up(self, student_id):
        student = QuizSessionStudent.objects.get(id=student_id)
        student.skip_count += 1
        student.save()
        return {'status': 'success', 'skip_count': student.skip_count}

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
        student = data.get('data').get('student')

        skip_count = await self.get_skip_count(student.get('id'))
        session_settings = await self.get_session_settings()

        if skip_count < session_settings.get('skip_count_per_student'):
            question_marked = await self.mark_question_as_skipped_and_correct(data)
            print(question_marked)
            if question_marked:
                await self.increment_skip_count(student.get('id'))
                await self.send(text_data=json.dumps({
                    'type': 'skip_power_up_used',
                    'message': 'Question skipped successfully.'
                }))
        else:
            await self.send(text_data=json.dumps({
                'type': 'skip_power_up_error',
                'message': 'You have already used all your skip power ups for this session.'
            }))

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
            data = data['data']
            student_data = data.pop('student', {})
            student_id = student_data.get('id')
            student = QuizSessionStudent.objects.get(id=student_id)
            question = QuestionMultipleChoice.objects.get(id=data['question_id'])
            quiz_session = QuizSession.objects.get(code=data['quiz_session_code'])

            UserResponse.objects.create(
                student=student,
                is_correct=True,
                quiz_session=quiz_session,
                question=question,
                selected_answer='skipped',
                skipped_question=True
            )

            return True
        except Exception as e:
            print(e)
            return False
