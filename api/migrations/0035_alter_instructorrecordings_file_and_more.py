# Generated by Django 4.2.6 on 2024-08-30 20:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0034_instructorrecordings"),
    ]

    operations = [
        migrations.AlterField(
            model_name="instructorrecordings",
            name="file",
            field=models.FileField(upload_to="get_audio_upload_path"),
        ),
        migrations.AlterModelTable(
            name="instructorrecordings",
            table=None,
        ),
    ]
