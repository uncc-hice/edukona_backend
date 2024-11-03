# Generated by Django 4.2.6 on 2024-11-01 19:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0051_contactmessage"),
    ]

    operations = [
        migrations.AddField(
            model_name="quiz",
            name="live_bar_chart",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="quiz",
            name="skip_count_per_student",
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name="quiz",
            name="skip_question",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="quiz",
            name="skip_question_logic",
            field=models.TextField(default="random"),
        ),
        migrations.AddField(
            model_name="quiz",
            name="skip_question_percentage",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="quiz",
            name="skip_question_streak_count",
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name="quiz",
            name="timer",
            field=models.BooleanField(default=False),
        ),
    ]
