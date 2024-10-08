# Generated by Django 4.2.6 on 2024-10-07 23:08

from django.db import migrations


def transfer_served_questions(apps, schema_editor):
    QuizSession = apps.get_model("api", "QuizSession")
    QuizSessionQuestion = apps.get_model("api", "QuizSessionQuestion")

    # Iterate through all QuizSessions
    for session in QuizSession.objects.all():
        # Get all served questions from the old M2M field
        questions = session.served_questions.all()
        for question in questions:
            # Create a new QuizSessionQuestion entry with skipped=False
            QuizSessionQuestion.objects.create(
                quiz_session=session,
                question=question,
                skipped=False,  # Default value; adjust if necessary
            )


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0043_alter_quizsessionquestion_table"),
    ]

    operations = [
        migrations.RunPython(transfer_served_questions),
    ]
