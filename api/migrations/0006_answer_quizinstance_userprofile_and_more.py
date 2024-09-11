# Generated by Django 4.2.6 on 2023-10-21 08:26

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("api", "0005_rename_quic_quiz"),
    ]

    operations = [
        migrations.CreateModel(
            name="Answer",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("answer_choice", models.CharField(max_length=300)),
                ("is_correct", models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name="QuizInstance",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.RemoveField(
            model_name="question",
            name="choice_1",
        ),
        migrations.RemoveField(
            model_name="question",
            name="choice_2",
        ),
        migrations.RemoveField(
            model_name="question",
            name="choice_3",
        ),
        migrations.RemoveField(
            model_name="question",
            name="choice_correct",
        ),
        migrations.RemoveField(
            model_name="question",
            name="question_text",
        ),
        migrations.RemoveField(
            model_name="quiz",
            name="quiz_duration_minutes",
        ),
        migrations.AddField(
            model_name="question",
            name="question",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="UserResponse",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="api.question"
                    ),
                ),
                (
                    "selected_answer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="api.answer"
                    ),
                ),
                (
                    "user_profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="api.userprofile",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Student",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                (
                    "quizzes",
                    models.ManyToManyField(through="api.QuizInstance", to="api.quiz"),
                ),
                (
                    "user_profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="api.userprofile",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="quizinstance",
            name="quiz",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="api.quiz"
            ),
        ),
        migrations.AddField(
            model_name="quizinstance",
            name="student",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="api.student"
            ),
        ),
        migrations.CreateModel(
            name="Leaderboard",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("scores", models.JSONField()),
                (
                    "quiz_instance",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="api.quizinstance",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="answer",
            name="question",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="api.question"
            ),
        ),
        migrations.AddField(
            model_name="quiz",
            name="creator",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="api.userprofile",
            ),
        ),
    ]
