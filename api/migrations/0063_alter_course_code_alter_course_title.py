# Generated by Django 4.2.6 on 2024-12-24 04:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0062_course"),
    ]

    operations = [
        migrations.AlterField(
            model_name="course",
            name="code",
            field=models.TextField(max_length=75, unique=True),
        ),
        migrations.AlterField(
            model_name="course",
            name="title",
            field=models.CharField(max_length=60),
        ),
    ]
