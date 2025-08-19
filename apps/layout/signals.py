from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.layout.models import Layout, LayoutFilterConfig
from apps.accounts.models.custom_user import CustomUser


@receiver(post_save, sender=Layout)
def create_default_layout_filter(sender, instance: Layout, created: bool, **kwargs):
    """On layout creation, create per-user 'None' layout filters.

    - Public layout: create for all existing users.
    - Private layout: create only for the owner.
    """
    if not created:
        return
    try:
        if instance.visibility == Layout.VISIBILITY_PUBLIC:
            users = CustomUser.objects.all()
        else:
            users = [instance.user]
        for user in users:
            qs = LayoutFilterConfig.objects.filter(layout=instance, user=user)
            if not qs.filter(name="None").exists():
                LayoutFilterConfig.objects.create(
                    layout=instance,
                    user=user,
                    name="None",
                    values={},
                    is_default=(not qs.exists()),
                )
    except Exception:
        # Be defensive during migrations/startup; it's safe to no-op here.
        pass

@receiver(post_save, sender=CustomUser)
def create_default_layout_filters_for_new_user(sender, instance: CustomUser, created: bool, **kwargs):
    """On new user creation, create 'None' filters for public layouts only."""
    if not created:
        return
    try:
        for layout in Layout.objects.filter(visibility=Layout.VISIBILITY_PUBLIC):
            qs = LayoutFilterConfig.objects.filter(layout=layout, user=instance)
            if not qs.filter(name="None").exists():
                LayoutFilterConfig.objects.create(
                    layout=layout,
                    user=instance,
                    name="None",
                    values={},
                    is_default=(not qs.exists()),
                )
    except Exception:
        pass


@receiver(pre_save, sender=Layout)
def _capture_old_visibility(sender, instance: Layout, **kwargs):
    """Capture previous visibility so post_save can detect changes."""
    if not instance.pk:
        instance._old_visibility = None
        return
    try:
        old = Layout.objects.get(pk=instance.pk)
        instance._old_visibility = old.visibility
    except Layout.DoesNotExist:
        instance._old_visibility = None


@receiver(post_save, sender=Layout)
def handle_visibility_change(sender, instance: Layout, created: bool, **kwargs):
    """React to visibility changes to maintain per-user filters.

    - private -> public: ensure 'None' filter exists for all users.
    - public -> private: delete all filters for non-owner users.
    """
    if created:
        return
    try:
        old_vis = getattr(instance, "_old_visibility", None)
        new_vis = instance.visibility
        if old_vis == new_vis or old_vis is None:
            return
        # Private -> Public
        if old_vis == Layout.VISIBILITY_PRIVATE and new_vis == Layout.VISIBILITY_PUBLIC:
            for user in CustomUser.objects.all():
                qs = LayoutFilterConfig.objects.filter(layout=instance, user=user)
                if not qs.filter(name="None").exists():
                    LayoutFilterConfig.objects.create(
                        layout=instance,
                        user=user,
                        name="None",
                        values={},
                        is_default=(not qs.exists()),
                    )
        # Public -> Private
        elif old_vis == Layout.VISIBILITY_PUBLIC and new_vis == Layout.VISIBILITY_PRIVATE:
            LayoutFilterConfig.objects.filter(layout=instance).exclude(user=instance.user).delete()
    except Exception:
        # Defensive no-op
        pass
