from django.conf import settings
from django.urls import include, re_path
from django.views.decorators.cache import cache_page

from creme.creme_api.api.routes import router
from creme.creme_api.api.tokens.views import TokenView
from creme.creme_api.views import (
    ApplicationCreation,
    ApplicationEdition,
    ConfigurationView,
    DocumentationView,
    SchemaView,
)

schema_view = SchemaView.as_view()
if not settings.DEBUG:
    schema_view = cache_page(60 * 15)(schema_view)
urlpatterns = [
    re_path(r'^openapi[/]?$', schema_view, name='creme_api__openapi_schema'),
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
] + [
    re_path(r"^tokens/$", TokenView.as_view(), name="creme_api__tokens"),
    # re_path(r"^revoke_token/$", oauth_views.RevokeTokenView.as_view(), name="revoke-token"),
    # re_path(r"^introspect/$", oauth_views.IntrospectTokenView.as_view(), name="introspect"),
] + router.urls
