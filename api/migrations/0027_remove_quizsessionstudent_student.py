# Generated by Django 4.2.6 on 2024-06-24 19:13

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0026_quizsessionstudent_student"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="quizsessionstudent",
            name="student",
        ),
    ]
