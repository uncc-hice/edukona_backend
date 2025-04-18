# Generated by Django 4.2.6 on 2023-10-30 06:18

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("api", "0006_answer_quizinstance_userprofile_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Instructor",
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
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="QuestionMultipleChoice",
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
                ("question_text", models.TextField(blank=True, null=True)),
                ("incorrect_answer_list", models.JSONField()),
                ("correct_answer", models.CharField(max_length=500)),
                ("points", models.IntegerField(default=1)),
            ],
        ),
        migrations.RemoveField(
            model_name="leaderboard",
            name="quiz_instance",
        ),
        migrations.RemoveField(
            model_name="quizinstance",
            name="quiz",
        ),
        migrations.RemoveField(
            model_name="quizinstance",
            name="student",
        ),
        migrations.RemoveField(
            model_name="userprofile",
            name="user",
        ),
        migrations.RenameField(
            model_name="quiz",
            old_name="quiz_title",
            new_name="title",
        ),
        migrations.RemoveField(
            model_name="quiz",
            name="creator",
        ),
        migrations.RemoveField(
            model_name="student",
            name="name",
        ),
        migrations.RemoveField(
            model_name="student",
            name="quizzes",
        ),
        migrations.RemoveField(
            model_name="student",
            name="user_profile",
        ),
        migrations.RemoveField(
            model_name="userresponse",
            name="user_profile",
        ),
        migrations.AddField(
            model_name="quiz",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name="quiz",
            name="end_time",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="quiz",
            name="start_time",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="student",
            name="user",
            field=models.OneToOneField(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="userresponse",
            name="is_correct",
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="userresponse",
            name="student",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.CASCADE, to="api.student"
            ),
        ),
        migrations.AlterField(
            model_name="userresponse",
            name="selected_answer",
            field=models.CharField(max_length=500),
        ),
        migrations.DeleteModel(
            name="Answer",
        ),
        migrations.DeleteModel(
            name="Leaderboard",
        ),
        migrations.DeleteModel(
            name="QuizInstance",
        ),
        migrations.DeleteModel(
            name="UserProfile",
        ),
        migrations.AddField(
            model_name="questionmultiplechoice",
            name="quiz",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="api.quiz"),
        ),
        migrations.AddField(
            model_name="quiz",
            name="instructor",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="api.instructor",
            ),
        ),
        migrations.AlterField(
            model_name="userresponse",
            name="question",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="api.questionmultiplechoice",
            ),
        ),
        migrations.DeleteModel(
            name="Question",
        ),
    ]
