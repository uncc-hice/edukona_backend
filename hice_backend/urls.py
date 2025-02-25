from django.contrib import admin
from django.urls import path
from api.views.question_views import *
from api.views.quiz_views import *
from api.views.session_views import *
from api.views.user_views import *
from api.views.course_views import *
from api.views.recordings_views import *
from api.consumers import *
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
    TokenBlacklistView,
)

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("quiz/<int:quiz_id>/", QuizView.as_view(), name="quiz-detail"),
    path(
        "quiz/<int:quiz_id>/update-title/", UpdateQuizTitleView.as_view(), name="quiz-update-title"
    ),
    path(
        "course/<uuid:course_id>/get-quizzes/",
        QuizzesByCourseView.as_view(),
        name="quizzes-by-course",
    ),
    path("question/", QuestionView.as_view(), name="question-list"),
    path("question/<int:question_id>/", QuestionView.as_view(), name="question-detail"),
    path(
        "all-questions/<int:quiz_id>/",
        AllQuizQuestionsView.as_view(),
        name="all-questions",
    ),
    path(
        "create-multiple-questions/",
        CreateMultipleQuestionsView.as_view(),
        name="create-multiple-questions",
    ),
    path("instructor/", InstructorView.as_view(), name="instructor-detail"),
    path(
        "instructor/<int:instructor_id>/",
        InstructorView.as_view(),
        name="instructor-detail",
    ),
    path("instructor/quizzes/", InstructorQuizzesView.as_view(), name="instructor-quizzes"),
    # path('student/', StudentView.as_view(), name='student-list'),
    # path('student/<int:student_id>/', StudentView.as_view(), name='student-detail'),
    path("user-response/", UserResponseView.as_view(), name="user-response-list"),
    path(
        "user-response/<int:response_id>/",
        UserResponseView.as_view(),
        name="user-response-detail",
    ),
    path("sign-up-instructor/", SignUpInstructor.as_view(), name="sign-up-instructor"),
    path("jwt-sign-up-instructor/", JWTSignUpInstructor.as_view(), name="jwt-sign-up-instructor"),
    # path('sign-up-student/', SignUpStudent.as_view()),
    path("login/", Login.as_view(), name="login"),
    path("logout/", Logout.as_view(), name="logout"),
    path("quiz-session/", QuizSessionView.as_view(), name="quiz-session-list"),
    path(
        "quiz-session/add-log-entry/",
        QuizSessionLogView.as_view(),
        name="add-quiz-session-log",
    ),
    path(
        "quiz-session/<str:code>/",
        QuizSessionStudentView.as_view(),
        name="quiz-session-detail",
    ),
    path(
        "quiz-session-student/",
        QuizSessionStudentView.as_view(),
        name="quiz-session-student-list",
    ),
    path(
        "quiz-session-student/<str:code>/",
        QuizSessionStudentView.as_view(),
        name="quiz-session-student-detail",
    ),
    path(
        "quiz-session-student-instructor/<str:code>/",
        QuizSessionStudentInstructorView.as_view(),
        name="instructor-session-view",
    ),
    path(
        "instructor-quiz-view/<str:quiz_id>/",
        QuizSessionInstructorView.as_view(),
        name="instructor-quiz-view",
    ),
    path(
        "quiz-session/<str:session_code>/next-question/",
        NextQuestionAPIView.as_view(),
        name="next-question",
    ),
    path(
        "quiz/student/question/<str:session_code>/<int:question_id>/",
        StudentQuestion.as_view(),
        name="student" "-question",
    ),
    path(
        "quiz/student/question/<str:session_code>/",
        StudentQuestion.as_view(),
        name="student-question",
    ),
    path(
        "quiz-session/color/<str:session_code>/",
        StoreColorAPIView.as_view(),
        name="quiz-session-color",
    ),
    path(
        "quiz-session-results/<str:code>/",
        QuizSessionResults.as_view(),
        name="quiz-session-results",
    ),
    path(
        "quiz-sessions-list/",
        QuizSessionsByInstructorView.as_view(),
        name="quiz-sessions-list",
    ),
    path(
        "quiz/<int:quiz_id>/sessions",
        QuizSessionsByQuizView.as_view(),
        name="quiz-sessions",
    ),
    path(
        "quiz-session-delete/<str:code>/",
        DeleteQuizSession.as_view(),
        name="delete-quiz-session",
    ),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "quiz-session-responses-count/<str:code>/",
        StudentResponseCountView.as_view(),
        name="quiz-session-responses",
    ),
    path("quiz/create/", CreateQuizView.as_view(), name="create-quiz"),
    path(
        "schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("check-developer/", CheckDeveloperStatus.as_view(), name="check-developer"),
    path("recordings/upload-audio/", UploadAudioView.as_view(), name="upload-audio"),
    path(
        "recordings/<uuid:recording_id>/get-quizzes-and-summaries",
        GetQuizzesAndSummaries.as_view(),
        name="get-quizzes-and-summaries",
    ),
    path(
        "recordings/<uuid:recording_id>/update-transcript/",
        UpdateTranscriptView.as_view(),
        name="update-transcript",
    ),
    path(
        "recordings/<uuid:recording_id>/delete-recording",
        DeleteRecordingView.as_view(),
        name="delete-recording",
    ),
    path(
        "recordings/<uuid:recording_id>/update-duration/",
        UpdateRecordingDurationView.as_view(),
        name="update-recording-duration",
    ),
    path(
        "recordings/",
        RecordingsView.as_view(),
        name="instructor-recording",
    ),
    path(
        "recordings/<uuid:recording_id>/get-transcript/",
        GetTranscriptView.as_view(),
        name="get-transcript",
    ),
    path(
        "recordings/<uuid:recording_id>/update-title/",
        UpdateRecordingTitleView.as_view(),
        name="recording-update-title",
    ),
    path("auth/google/", GoogleLogin.as_view()),  # Route for Google login
    path("contact-us/", ContactPageView.as_view(), name="contact-us"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("delete-user/", DeleteUserView.as_view(), name="delete-user"),
    path(
        "generate-temporary-credentials/",
        GenerateTemporaryCredentialsView.as_view(),
        name="generate-temporary-credentials",
    ),
    path(
        "recordings/create-recording/",
        CreateRecordingView.as_view(),
        name="create-recording",
    ),
    path(
        "recordings/<uuid:recording_id>/quizzes/",
        QuizByRecordingView.as_view(),
        name="quizzes-by-recording",
    ),
    path(
        "recordings/<uuid:recording_id>/summary/",
        LectureSummaryView.as_view(),
        name="lecture_summary",
    ),
    path(
        "summary/<uuid:summary_id>/get-summary/",
        LectureSummaryByIdView.as_view(),
        name="get-summary",
    ),
    path(
        "summary/<uuid:summary_id>/update-summary/",
        UpdateLectureSummaryView.as_view(),
        name="update-summary",
    ),
    path(
        "course/<uuid:course_id>/get-recordings/",
        GetRecordingsByCourse.as_view(),
        name="get-course-recordings",
    ),
    path(
        "instructor/get-courses/",
        GetCoursesByInstructor.as_view(),
        name="get-instructor-courses",
    ),
    path(
        "instructor/course/<uuid:course_id>/get-summaries/",
        GetSummariesByCourse.as_view(),
        name="get-instructor-course-summaries",
    ),
    path(
        "course/<uuid:course_id>/get-students/",
        GetStudentsByCourse.as_view(),
        name="get-course-students",
    ),
    path("instructor/create-course/", CreateCourse.as_view(), name="create-course"),
    path("student/get-courses/", GetCoursesByStudent.as_view(), name="get-courses-by-student"),
    path(
        "student/course/<course_id>/get-summaries/",
        view=FetchPublishedSummariesView.as_view(),
        name="get-published-summaries",
    ),
    path(
        "token/verify/",
        TokenVerificationView.as_view(),
        name="verify-token",
    ),
    path("jwt-token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("jwt-token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("jwt-token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("jwt-token/blacklist/", TokenBlacklistView.as_view(), name="token_blacklist"),
    path("jwt-login/", JWTLoginView.as_view(), name="jwt-login"),
    path("jwt-logout/", JWTLogoutView.as_view(), name="jwt-logout"),
    path("auth/jwt-google/", JWTGoogleLogin.as_view(), name="jwt-google"),
    path(
        "sessions/<int:session_id>/get-score/<int:student_id>/",
        GetStudentScoreForSession.as_view(),
        name="get-score",
    ),
    path(
        "sessions/<int:session_id>/update-scores/", UpdateScoresView.as_view(), name="update-scores"
    ),
    path(
        "recordings/<uuid:recording_id>/update-course/",
        UpdateRecordingCourse.as_view(),
        name="update-recording-course",
    ),
]
