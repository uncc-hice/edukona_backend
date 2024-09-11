# Generated by Django 4.2.6 on 2024-08-30 20:18

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0033_delete_instructorrecordings"),
    ]

    operations = [
        migrations.CreateModel(
            name="InstructorRecordings",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("file", models.FileField(upload_to="audio_files/")),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "instructor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="api.instructor"
                    ),
                ),
            ],
            options={
                "db_table": "api_instructor_recordings",
            },
        ),
    ]
