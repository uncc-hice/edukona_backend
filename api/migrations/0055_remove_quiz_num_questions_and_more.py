# Generated by Django 4.2.6 on 2024-11-10 01:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0054_quiz_num_questions_quiz_question_duration"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="quiz",
            name="num_questions",
        ),
        migrations.RemoveField(
            model_name="quiz",
            name="question_duration",
        ),
    ]
