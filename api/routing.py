from django.urls import re_path
from api import consumers

websocket_urlpatterns = [
    re_path(r'ws/quiz-session-instructor/(?P<code>\w+)/', consumers.QuizSessionInstructorConsumer.as_asgi()),
    re_path(r'ws/student/join/(?P<code>\w+)/', consumers.StudentConsumer.as_asgi()),
]
