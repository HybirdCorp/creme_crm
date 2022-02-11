from django.urls import include, re_path

from creme.creme_api.api.routes import router
from creme.creme_api.views import (
    ApplicationCreation,
    ApplicationEdition,
    ConfigurationView,
    DocumentationView,
    SchemaView,
)

urlpatterns = [
    re_path(r'^openapi[/]?$', SchemaView.as_view(), name='creme_api__openapi_schema'),
    re_path(r'^documentation[/]?$', DocumentationView.as_view(), name='creme_api__documentation'),
    re_path(r'^configuration[/]?$', ConfigurationView.as_view(), name='creme_api__configuration'),
    re_path(
        r'^configuration/applications/',
        include([
            re_path(
                r'^add[/]?$',
                ApplicationCreation.as_view(),
                name='creme_api__create_application',
            ),
            re_path(
                r'^edit/(?P<application_id>\d+)[/]?$',
                ApplicationEdition.as_view(),
                name='creme_api__edit_application',
            ),
        ]),
    ),
] + router.urls
