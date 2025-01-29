from django.core.management.base import BaseCommand
from api.models import Quiz


class Command(BaseCommand):
    def handle(self, *args, **options):
        new_quizzes = []
        self.stdout.write("Copying settings...")
        quizzes = Quiz.objects.select_related("settings").all()
        for quiz in quizzes:
            settings = quiz.settings
            if settings is None:
                continue
            # self.stdout.write(str(settings.id))
            quiz.timer = settings.timer
            quiz.live_bar_chart = settings.live_bar_chart
            new_quizzes.append(quiz)
        Quiz.objects.bulk_update(
            new_quizzes,
            fields=[
                "timer",
                "live_bar_chart",
            ],
        )
