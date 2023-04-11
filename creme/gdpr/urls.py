from django.urls import re_path

from . import views

urlpatterns = [
    re_path(
        r'^soon_anonymized[/]?$',
        views.SoonAnonymizedEntities.as_view(),
        name='gdpr__list_soon_anonymized',
    ),
]
