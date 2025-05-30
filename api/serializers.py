from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.validators import EmailValidator
from rest_framework import serializers

from .constants import ROLES
from .models import (
    ContactMessage,
    Course,
    Instructor,
    InstructorRecordings,
    LectureSummary,
    QuestionMultipleChoice,
    Quiz,
    QuizSession,
    QuizSessionLog,
    QuizSessionStudent,
    Student,
    UserResponse,
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = "__all__"


class InstructorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instructor
        fields = "__all__"


class IncorrectAnswerSerializer(serializers.Serializer):
    answer = serializers.CharField()
    feedback = serializers.CharField()


class QuestionMultipleChoiceSerializer(serializers.ModelSerializer):
    quiz_id = serializers.PrimaryKeyRelatedField(queryset=Quiz.objects.all(), source="quiz")
    duration = serializers.IntegerField(required=False, default=20)
    incorrect_answer_list = IncorrectAnswerSerializer(many=True)

    class Meta:
        model = QuestionMultipleChoice
        fields = [
            "id",
            "question_text",
            "incorrect_answer_list",
            "correct_answer",
            "points",
            "quiz_id",
            "duration",
        ]


class UserResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserResponse
        fields = "__all__"


class QuizSessionStudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizSessionStudent
        fields = "__all__"


class InstructorRecordingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstructorRecordings
        fields = "__all__"
        read_only_fields = ["id", "uploaded_at", "transcript"]

        instructor = serializers.PrimaryKeyRelatedField(read_only=True)


class RecordingUpdateSerializer(serializers.Serializer):
    title = serializers.CharField()
    duration = serializers.IntegerField()
    course = serializers.UUIDField()
    published = serializers.BooleanField()

    def update(self, instance, validated_data):
        instance.title = validated_data.get("title", instance.title)
        instance.duration = validated_data.get("duration", instance.duration)
        if validated_data.get("course"):
            instance.course = Course.objects.get(id=validated_data["course"])
        instance.published = validated_data.get("published", instance.published)
        instance.save()
        return instance


class UpdateTranscriptSerializer(serializers.Serializer):
    transcript = serializers.CharField()


class GetTranscriptResponseSerializer(serializers.Serializer):
    transcript = serializers.CharField()


class GoogleLoginResponseSerializer(serializers.Serializer):
    token = serializers.CharField()


class GoogleLoginRequestSerializer(serializers.Serializer):
    token = serializers.CharField()


class QuizSerializer(serializers.ModelSerializer):
    instructor_recording = serializers.PrimaryKeyRelatedField(
        queryset=InstructorRecordings.objects.all(), required=False, allow_null=True
    )
    num_questions = serializers.SerializerMethodField()
    num_sessions = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "start_time",
            "end_time",
            "timer",
            "instructor_recording",
            "created_at",
            "num_questions",
            "num_sessions",
        ]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        instructor = self.context["request"].user.instructor
        quiz = Quiz.objects.create(instructor=instructor, **validated_data)
        return quiz

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)

    def get_num_questions(self, obj):
        return QuestionMultipleChoice.objects.filter(quiz__id=obj.id).count()

    def get_num_sessions(self, obj):
        return QuizSession.objects.filter(quiz__id=obj.id).count()


class CreateQuizFromTranscriptRequestSerializer(serializers.Serializer):
    number_of_questions = serializers.IntegerField()
    question_duration = serializers.IntegerField()


class QuizListSerializer(serializers.Serializer):
    quizzes = QuizSerializer(many=True)


class QuizTitleUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(required=True, allow_blank=False)


class AddQuizSessionLogSerializer(serializers.Serializer):
    quiz_session_code = serializers.CharField(required=True, allow_blank=False)
    quiz_session_student_id = serializers.IntegerField(required=True, min_value=0)
    question_multiple_choice_id = serializers.UUIDField(required=False)
    action = serializers.CharField(required=True)

    id = serializers.UUIDField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    quiz_session = serializers.PrimaryKeyRelatedField(read_only=True)
    quiz_session_student = serializers.PrimaryKeyRelatedField(read_only=True)
    question_multiple_choice = serializers.PrimaryKeyRelatedField(read_only=True)

    def validate_action(self, value):
        allowed_actions = ["connected", "disconnected", "reconnected"]
        if value not in allowed_actions:
            raise serializers.ValidationError("Invalid action")
        return value

    def validate(self, data):
        # resolve objects
        try:
            data["quiz_session"] = QuizSession.objects.get(code=data["quiz_session_code"])
        except QuizSession.DoesNotExist:
            raise serializers.ValidationError({"quiz_session_code": "Quiz session not found."})

        try:
            data["quiz_session_student"] = QuizSessionStudent.objects.get(
                id=data["quiz_session_student_id"]
            )
        except QuizSessionStudent.DoesNotExist:
            raise serializers.ValidationError({"quiz_session_student_id": "Student not found."})

        question_multiple_choice_id = data.get("question_multiple_choice_id")
        if question_multiple_choice_id:
            try:
                data["question_multiple_choice"] = QuestionMultipleChoice.objects.get(
                    id=question_multiple_choice_id
                )
            except QuestionMultipleChoice.DoesNotExist:
                raise serializers.ValidationError(
                    {"question_multiple_choice_id": "Question not found."}
                )
        else:
            data["question_multiple_choice"] = None

        return data

    def create(self, validated_data):
        validated_data.pop("quiz_session_student_id")
        validated_data.pop("question_multiple_choice_id", None)

        return QuizSessionLog.objects.create(**validated_data)


class FetchCourseQuizzesSerializer(serializers.ModelSerializer):
    instructor_recording = serializers.PrimaryKeyRelatedField(
        queryset=InstructorRecordings.objects.all(), required=False, allow_null=True
    )
    num_questions = serializers.SerializerMethodField()
    num_sessions = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "start_time",
            "end_time",
            "timer",
            "live_bar_chart",
            "instructor_recording",
            "created_at",
            "num_questions",
            "num_sessions",
        ]
        read_only_fields = ["id", "created_at"]

    def get_num_questions(self, obj):
        return QuestionMultipleChoice.objects.filter(quiz__id=obj.id).count()

    def get_num_sessions(self, obj):
        return QuizSession.objects.filter(quiz__id=obj.id).count()


class RecordingTitleUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(required=True, allow_blank=False)


class RecordingDurationUpdateSerializer(serializers.Serializer):
    duration = serializers.IntegerField(required=True, min_value=0, help_text="Duration in seconds")


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["id", "first_name", "last_name", "email", "message", "created_at"]
        read_only_fields = ["id", "created_at"]

    # Make 'last_name' optional with default value ""
    last_name = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_email(self, value):
        """
        Validate that the email has a proper format.
        """
        if not value:
            raise serializers.ValidationError("Email is required.")
        return value

    def validate_first_name(self, value):
        """
        Ensure that 'first_name' is not just whitespace.
        """
        if not value.strip():
            raise serializers.ValidationError("First name cannot be blank.")
        return value

    def validate_message(self, value):
        """
        Ensure that 'message' is not just whitespace.
        """
        if not value.strip():
            raise serializers.ValidationError("Message cannot be blank.")
        return value


class SignUpInstructorSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField(
        max_length=254,
        validators=[EmailValidator()],
        help_text="This will be used as the username.",
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )

    def validate_email(self, value):
        """
        Ensure the email is unique and not already used as a username.
        """
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def create(self, validated_data):
        """
        Create a new User and Instructor instance.
        """
        first_name = validated_data.get("first_name")
        last_name = validated_data.get("last_name", "")
        email = validated_data.get("email")
        password = validated_data.get("password")

        # Create the User
        user = User.objects.create(
            username=email,  # Using email as username
            email=email,
            first_name=first_name,
            last_name=last_name,
        )
        user.set_password(password)
        user.save()

        # Create the Instructor
        instructor = Instructor.objects.create(user=user)

        return instructor


class LectureSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = LectureSummary
        fields = ["id", "summary", "recording_id", "created_at"]
        read_only_fields = ["id", "recording_id", "created_at"]


class LectureSummaryTypedSerializer(LectureSummarySerializer):
    type = serializers.CharField(required=True, allow_blank=False)

    class Meta:
        model = LectureSummary
        fields = "__all__"


class QuizTypedSerializer(QuizSerializer):
    type = serializers.CharField(required=True, allow_blank=False)

    class Meta:
        model = Quiz
        fields = "__all__"


class QuizAndSummarySerializer(serializers.Serializer):
    def to_representation(self, instance):
        if isinstance(instance, Quiz):
            return QuizTypedSerializer(instance).data
        elif isinstance(instance, LectureSummary):
            return LectureSummaryTypedSerializer(instance).data
        else:
            # TODO: Add a logging statement once logging is configured
            pass


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = [
            "id",
            "instructor",
            "title",
            "description",
            "code",
            "created_at",
            "allow_joining_until",
            "start_date",
            "end_date",
        ]
        read_only_fields = ["id", "code", "created_at"]


class CourseCreationSerializer(serializers.Serializer):
    title = serializers.CharField()
    description = serializers.CharField()
    allow_joining_until = serializers.DateTimeField(required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def create(self, validated_data):
        validated_data["instructor"] = self.context.get("instructor")
        return Course(**validated_data)


class CourseStudentSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    joined_at = serializers.DateTimeField()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=128)
    password = serializers.CharField(max_length=128, style={"input_type": "password"})


class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField(help_text="JWT access token")
    refresh = serializers.CharField(help_text="JWT refresh token")
    user = serializers.IntegerField()
    instructor = serializers.IntegerField(required=False)


class LoginErrorResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class ScoreQuizResponseSerializer(serializers.Serializer):
    message = serializers.CharField()


class GetScoreRequestSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    quiz_session_id = serializers.IntegerField()


class GetScoreResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizSessionStudent
        fields = ["score"]


class UpdateRecordingCourseSerializer(serializers.Serializer):
    course_id = serializers.UUIDField(required=True)

    def validate_course_id(self, value):
        try:
            self._course = Course.objects.get(id=value)
            return value
        except Course.DoesNotExist:
            raise serializers.ValidationError("Course not found.")

    def validate(self, data):
        recording = self.context.get("recording")

        if recording is None:
            raise serializers.ValidationError("Recording must be provided in the context.")

        if recording.instructor != self._course.instructor:
            raise serializers.ValidationError(
                "The instructor of the course does not match the instructor of the recording."
            )

        data["course"] = self._course
        return data

    def update(self, instance, validated_data):
        instance.course = validated_data["course"]
        instance.save()
        return instance


class GoogleSSORequestSerializer(serializers.Serializer):
    token = serializers.CharField()
    role = serializers.CharField(required=False)

    def validate_role(self, value):
        if value not in ROLES:
            raise serializers.ValidationError("Invalid role")
        return value


class GoogleSSOResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = serializers.IntegerField()
    instructor = serializers.IntegerField(required=False)
    student = serializers.UUIDField(required=False)
