from django.contrib import admin
from django.urls import path
from api.views import *
from api.consumers import *

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('quiz/', QuizView.as_view(), name='quiz-list'),
    path('quiz/<int:quiz_id>/', QuizView.as_view(), name='quiz-detail'),
    path('question/', QuestionView.as_view(), name='question-list'),
    path('question/<int:question_id>/', QuestionView.as_view(), name='question-detail'),
    path('all-questions/<int:quiz_id>/', AllQuizQuestionsView.as_view(), name='all-questions'),
    path('instructor/', InstructorView.as_view(), name='instructor-detail'),
    path('instructor/<int:instructor_id>/', InstructorView.as_view(), name='instructor-detail'),
    # path('student/', StudentView.as_view(), name='student-list'),
    # path('student/<int:student_id>/', StudentView.as_view(), name='student-detail'),
    path('user-response/', UserResponseView.as_view(), name='user-response-list'),
    path('user-response/<int:response_id>/', UserResponseView.as_view(), name='user-response-detail'),
    path('sign-up-instructor/', SignUpInstructor.as_view()),
    # path('sign-up-student/', SignUpStudent.as_view()),
    path('login/', Login.as_view(), name='login'),
    path('logout/', Logout.as_view()),
    path('quiz-session/', QuizSessionView.as_view(), name='quiz-session-list'),
    path('quiz-session/<str:code>/', QuizSessionStudentView.as_view(), name='quiz-session-detail'),
    path('quiz-session-student/', QuizSessionStudentView.as_view(), name='quiz-session-student-list'),
    path('quiz-session-student/<str:code>/', QuizSessionStudentView.as_view(), name='quiz-session-student-detail'),
    path('quiz-session-student-instructor/<str:code>/',
         QuizSessionStudentInstructorView.as_view(), name='instructor-session-view'),
    path('instructor-quiz-view/<str:quiz_id>/', QuizSessionInstructorView.as_view(), name='instructor-quiz-view'),
    path('quiz-session/<str:session_code>/next-question/', NextQuestionAPIView.as_view(), name='next-question'),
    path('quiz/student/question/<str:session_code>/<int:question_id>/', StudentQuestion.as_view(), name='student'
                                                                                                        '-question'),
    path('quiz/student/question/<str:session_code>/', StudentQuestion.as_view(), name='student-question'),
    path('quiz-session/color/<str:session_code>/', StoreColorAPIView.as_view(), name='quiz-session-color'),
    path('quiz-session-results/<str:code>/', QuizSessionResults.as_view(), name='quiz-session-results'),
    path('quiz-sessions-list/', QuizSessionsByInstructorView.as_view(), name='quiz-sessions-list'),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('quiz-session-responses-count/<str:code>/', StudentResponseCountView.as_view(), name='quiz-session-responses'),
    path('quiz/<int:quiz_id>/settings', SettingsView.as_view(), name='quiz-settings'),
    path('schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('check-developer/', CheckDeveloperStatus.as_view(), name='check-developer'),

]
