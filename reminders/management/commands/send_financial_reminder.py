from django.core.management.base import BaseCommand

from reminders.services.notification import (
    send_todays_financial_reminders,
)


class Command(BaseCommand):

    help = (
        "Send today's financial reminder "
        "email and push notifications."
    )

    def handle(self, *args, **options):

        self.stdout.write(
            "Checking financial reminders..."
        )

        results = send_todays_financial_reminders()

        total = len(results)

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {total} reminder(s)."
            )
        )

        for result in results:

            self.stdout.write(
                f"Reminder #{result['reminder_id']} "
                f"- {result['name']}"
            )