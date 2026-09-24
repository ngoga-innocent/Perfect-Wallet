from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User
from .models import UserSecurity


@receiver(post_save, sender=User)
def create_user_security(sender, instance, created, **kwargs):

    if created:
        UserSecurity.objects.create(
            user=instance
        )