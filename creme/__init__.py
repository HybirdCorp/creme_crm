import django.dispatch

form_post_save = django.dispatch.Signal(providing_args=["sender", "instance", "created"])

