# Generated by Django 4.2.6 on 2023-12-22 18:21

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("api", "0011_alter_userresponse_table"),
    ]

    operations = [
        migrations.AlterField(
            model_name="student",
            name="user",
            field=models.OneToOneField(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="student",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
