from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Student, Instructor, Quiz, QuestionMultipleChoice, UserResponse, QuizSessionStudent


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
