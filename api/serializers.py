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


class QuizSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
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


class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    """
    A ModelSerializer that takes an additional `fields` argument that
    controls which fields should be displayed.
    """

    def __init__(self, *args, **kwargs):
        # Don't pass the 'fields' arg up to the superclass
        fields = kwargs.pop('fields', None)

        # Instantiate the superclass normally
        super(DynamicFieldsModelSerializer, self).__init__(*args, **kwargs)

        if fields is not None:
            # Drop any fields that are not specified in the `fields` argument.
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


class InstructorRecordingsSerializer(DynamicFieldsModelSerializer):
    class Meta:
        model = InstructorRecordings
        fields = ["id", "s3_path", "uploaded_at", "instructor", "transcript"]


class UpdateTranscriptSerializer(serializers.Serializer):
    transcript = serializers.CharField()
