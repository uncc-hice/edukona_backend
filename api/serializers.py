from django.contrib.auth.password_validation import validate_password
from django.core.validators import EmailValidator
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Student,
    Instructor,
    Quiz,
    QuestionMultipleChoice,
    UserResponse,
    QuizSession,
    QuizSessionStudent,
    InstructorRecordings,
    Settings,
    ContactMessage,
    LectureSummary,
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


class QuestionMultipleChoiceSerializer(serializers.ModelSerializer):
    quiz_id = serializers.PrimaryKeyRelatedField(queryset=Quiz.objects.all(), source="quiz")
    duration = serializers.IntegerField(required=False, default=20)

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
        fields = ["id", "s3_path", "uploaded_at", "instructor", "transcript", "title"]
        read_only_fields = ["id", "uploaded_at", "transcript"]

        instructor = serializers.PrimaryKeyRelatedField(read_only=True)


class UpdateTranscriptSerializer(serializers.Serializer):
    transcript = serializers.CharField()


class GetTranscriptResponseSerializer(serializers.Serializer):
    transcript = serializers.CharField()


class GoogleLoginResponseSerializer(serializers.Serializer):
    token = serializers.CharField()


class GoogleLoginRequestSerializer(serializers.Serializer):
    token = serializers.CharField()


class SettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settings
        fields = "__all__"


class QuizSerializer(serializers.ModelSerializer):
    settings = SettingsSerializer(required=False, allow_null=True)
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
            "settings",
            "instructor_recording",
            "created_at",
            "num_questions",
            "num_sessions",
        ]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        settings_data = validated_data.pop("settings", {})
        settings = Settings.objects.create(**settings_data)
        instructor = self.context["request"].user.instructor
        quiz = Quiz.objects.create(instructor=instructor, settings=settings, **validated_data)
        return quiz

    def update(self, instance, validated_data):
        settings_data = validated_data.pop("settings", None)
        if settings_data:
            SettingsSerializer().update(instance.settings, settings_data)
        return super().update(instance, validated_data)

    def get_num_questions(self, obj):
        return QuestionMultipleChoice.objects.filter(quiz__id=obj.id).count()

    def get_num_sessions(self, obj):
        return QuizSession.objects.filter(quiz__id=obj.id).count()


class QuizListSerializer(serializers.Serializer):
    quizzes = QuizSerializer(many=True)


class QuizTitleUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(required=True, allow_blank=False)


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
