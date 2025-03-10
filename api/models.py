import random
import string
import uuid

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Student(models.Model):
    # The migrations have been migrated for this model.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, related_name="student")


class Instructor(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, null=True, related_name="instructor"
    )


class Course(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE)
    title = models.CharField(blank=False, max_length=60)
    description = models.TextField(blank=True)
    code = models.CharField(blank=False, unique=True, max_length=75)
    created_at = models.DateTimeField(auto_now_add=True)
    allow_joining_until = models.DateTimeField(default=timezone.now)
    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)

    class Meta:
        db_table = "api_course"

    def generate_code(self):
        hex_chars = string.digits + "abcdef"
        ins_initial = self.instructor.user.first_name[:1]
        ins_last_name = self.instructor.user.last_name
        code = f"{ins_initial}{ins_last_name[:10]}{self.title.replace(' ', '-')}"
        fin_code = code
        while Course.objects.filter(code=fin_code).exists():
            fin_code = f"{code}-{''.join(random.choices(hex_chars, k=2))}"
        return fin_code

    def save(self, *args, **kwargs):
        self.code = self.generate_code()
        super().save(*args, **kwargs)


class InstructorRecordings(models.Model):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )  # UUID as the primary key
    s3_path = models.CharField(max_length=200, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE)
    transcript = models.TextField(default="")
    title = models.CharField(max_length=250, default="")
    duration = models.PositiveIntegerField(default=0)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True)
    published = models.BooleanField(default=False)

    class Meta:
        db_table = "api_instructor_recordings"


class Quiz(models.Model):
    title = models.CharField(max_length=200)
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    # Settings starts here
    timer = models.BooleanField(default=False)
    live_bar_chart = models.BooleanField(default=True)
    # End of settings
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True)
    published = models.BooleanField(default=False)
    instructor_recording = models.ForeignKey(
        InstructorRecordings, on_delete=models.CASCADE, null=True
    )

    class Meta:
        ordering = ["-created_at"]

    def to_json(self):
        return {
            "id": self.id,
            "title": self.title,
            "instructor_id": self.instructor.id if self.instructor else None,
            "created_at": self.created_at,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "instructor_recording_id": (
                self.instructor_recording.id if self.instructor_recording else None
            ),
            "num_sessions": self.sessions.count(),
            "num_questions": self.questions.count(),
            # Settings attributes
            "timer": self.timer,
            "live_bar_chart": self.live_bar_chart,
        }


class QuestionMultipleChoice(models.Model):
    question_text = models.TextField(null=True, blank=True)
    incorrect_answer_list = models.JSONField()
    correct_answer = models.CharField(max_length=500)
    points = models.IntegerField(default=1)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    duration = models.IntegerField(default=20)

    class Meta:
        db_table = "api_question_multiple_choice"

    def to_json(self):
        return {
            "id": self.id,
            "question_text": self.question_text,
            "incorrect_answer_list": self.incorrect_answer_list,
            "correct_answer": self.correct_answer,
            "points": self.points,
            "quiz_id": self.quiz.id,
            "duration": self.duration,
        }


class QuizSession(models.Model):
    code = models.CharField(max_length=6, unique=True)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="sessions", null=True)
    question_colors = models.JSONField(null=True, blank=True, default=dict)

    served_questions = models.ManyToManyField(
        QuestionMultipleChoice,
        related_name="served_in_sessions",
        blank=True,
        through="QuizSessionQuestion",
    )

    current_question = models.ForeignKey(
        QuestionMultipleChoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_in_sessions",
    )

    def generate_unique_code(self):
        length = 5
        allowed_characters = "".join(
            [
                c
                for c in string.ascii_uppercase + string.digits
                if c not in {"I", "o", "O", "l", "0"}
            ]
        )

        while True:
            code = "".join(random.choices(allowed_characters, k=length))
            if not QuizSession.objects.filter(code=code).exists():
                return code

    def to_json(self):
        return {
            "code": self.code,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "quiz_id": self.quiz.id if self.quiz else None,
            "question_colors": self.question_colors,
            "current_question": (self.current_question.id if self.current_question else None),
        }

    class Meta:
        db_table = "api_quiz_session"


class QuizSessionStudent(models.Model):
    username = models.CharField(max_length=200)
    joined_at = models.DateTimeField(default=timezone.now)
    quiz_session = models.ForeignKey(QuizSession, on_delete=models.CASCADE, related_name="students")
    score = models.IntegerField(default=-1)

    class Meta:
        db_table = "api_quiz_session_student"


class QuizSessionLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz_session_code = models.CharField(max_length=6, unique=True)
    quiz_session = models.ForeignKey(QuizSession, on_delete=models.CASCADE)
    quiz_session_student = models.ForeignKey(QuizSessionStudent, on_delete=models.CASCADE)
    question_multiple_choice = models.ForeignKey(
        QuestionMultipleChoice, on_delete=models.CASCADE, null=True, blank=True
    )
    action = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "api_quiz_session_log"
        ordering = ["-created_at"]


class UserResponse(models.Model):
    student = models.ForeignKey(
        QuizSessionStudent, on_delete=models.CASCADE, related_name="responses"
    )
    question = models.ForeignKey(
        QuestionMultipleChoice, on_delete=models.CASCADE, related_name="responses"
    )
    selected_answer = models.CharField(max_length=500)
    is_correct = models.BooleanField(null=True, blank=True)
    quiz_session = models.ForeignKey(
        "QuizSession", on_delete=models.CASCADE, related_name="responses", null=True
    )

    class Meta:
        db_table = "api_user_response"


class QuizSessionQuestion(models.Model):
    quiz_session = models.ForeignKey(
        QuizSession, on_delete=models.CASCADE, related_name="quiz_session_questions"
    )
    question = models.ForeignKey(
        QuestionMultipleChoice,
        on_delete=models.CASCADE,
        related_name="quiz_session_questions",
    )
    skipped = models.BooleanField(default=False)
    unlocked = models.BooleanField(default=True)
    opened_at = models.DateTimeField(null=True, auto_now_add=True)
    extension = models.IntegerField(default=0)

    class Meta:
        db_table = "api_quiz_session_question"
        unique_together = ("quiz_session", "question")


class ContactMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=200)
    # Make last name optional and default it to ""
    last_name = models.CharField(max_length=200, default="", blank=True)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "api_contact_message"


class LectureSummary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recording = models.ForeignKey(
        InstructorRecordings, on_delete=models.CASCADE, related_name="summaries"
    )
    summary = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True)
    published = models.BooleanField(default=False)

    class Meta:
        db_table = "api_lecture_summary"
        ordering = ["-created_at"]


class CourseStudent(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=False)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=False)
    joined_at = models.DateTimeField(auto_now_add=True, null=False)

    class Meta:
        db_table = "api_course_student"
