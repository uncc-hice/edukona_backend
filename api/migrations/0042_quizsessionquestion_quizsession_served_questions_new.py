# Generated by Django 4.2.6 on 2024-10-07 23:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0041_questionmultiplechoice_duration_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="QuizSessionQuestion",
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
                ("skipped", models.BooleanField(default=False)),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="quiz_session_questions",
                        to="api.questionmultiplechoice",
                    ),
                ),
                (
                    "quiz_session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="quiz_session_questions",
                        to="api.quizsession",
                    ),
                ),
            ],
            options={
                "db_table": "api_quizsession_question",
                "unique_together": {("quiz_session", "question")},
            },
        ),
        migrations.AddField(
            model_name="quizsession",
            name="served_questions_new",
            field=models.ManyToManyField(
                blank=True,
                related_name="served_in_sessions_new",
                through="api.QuizSessionQuestion",
                to="api.questionmultiplechoice",
            ),
        ),
    ]
