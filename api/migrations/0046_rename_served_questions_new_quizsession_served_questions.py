# Generated by Django 4.2.6 on 2024-10-07 23:14

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0045_remove_quizsession_served_questions"),
    ]

    operations = [
        migrations.RenameField(
            model_name="quizsession",
            old_name="served_questions_new",
            new_name="served_questions",
        ),
    ]