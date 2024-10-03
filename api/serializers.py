from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Student,
    Instructor,
    Quiz,
    QuestionMultipleChoice,
    UserResponse,
    QuizSessionStudent,
    InstructorRecordings,
    Settings,
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
    class Meta:
        model = QuestionMultipleChoice
        fields = "__all__"


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
        fields = ["id", "s3_path", "uploaded_at", "instructor", "transcript"]


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
