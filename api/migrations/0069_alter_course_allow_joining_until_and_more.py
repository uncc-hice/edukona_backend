# Generated by Django 4.2.6 on 2025-01-12 19:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0068_instructorrecordings_course_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="course",
            name="allow_joining_until",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name="course",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
