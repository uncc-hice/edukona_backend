# Generated by Django 4.2.6 on 2024-11-12 07:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0055_merge_0054_auto_20241111_2121_0054_lecturesummary"),
    ]

    operations = [
        migrations.RenameField(
            model_name="lecturesummary",
            old_name="recording_id",
            new_name="recording",
        ),
    ]
