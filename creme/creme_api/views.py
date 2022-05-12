from django.apps import apps
from django.contrib import messages
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from rest_framework.authentication import SessionAuthentication
from rest_framework.schemas import openapi
from rest_framework.schemas.views import SchemaView as DRFSchemaView

from creme.creme_api import VERSION
from creme.creme_api.api.authentication import TokenAuthentication
from creme.creme_api.api.permissions import CremeApiPermission
from creme.creme_core.views import generic
from creme.creme_core.views.generic import base

from .bricks import ApplicationsBrick
from .forms import ApplicationForm
from .models import Application


class SchemaView(DRFSchemaView):
    title = _("Creme CRM API")
    description_template = "creme_api/description.md"
    version = VERSION
    authentication_classes = [SessionAuthentication]
    permission_classes = [CremeApiPermission]
    public = True
    generator_class = openapi.SchemaGenerator

    def get_description(self, context=None, request=None):
        description = render_to_string(
            self.description_template, context=context, request=request
        )
        # Force django safestring into builtin string
        return description + ""

    def get_title(self):
        return str(self.title)

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        creme_api_app_config = apps.get_app_config("creme_api")
        creme_api_rool_url = self.request.build_absolute_uri(
            creme_api_app_config.url_root
        )
        context = {"creme_api_rool_url": creme_api_rool_url}
        title = self.get_title()
        description = self.get_description(context=context, request=request)
        self.schema_generator = self.generator_class(
            title=title,
            description=description,
            version=self.version,
        )


class _DocumentationBaseView(base.BricksView):
    title = _("Creme CRM API")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = self.title
        return context


class DocumentationView(_DocumentationBaseView):
    template_name = "creme_api/documentation.html"
    extra_context = {"schema_url": "creme_api__openapi_schema"}
    permissions = "creme_api"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["creme_api__tokens_url"] = self.request.build_absolute_uri(
            reverse("creme_api__tokens-list")
        )
        context["token_type"] = TokenAuthentication.keyword
        return context


class ConfigurationView(_DocumentationBaseView):
    template_name = "creme_api/configuration.html"
    permissions = "creme_api.can_admin"

    def get_brick_ids(self):
        return [ApplicationsBrick.id_]


class ApplicationCreation(generic.CremeModelCreationPopup):
    model = Application
    form_class = ApplicationForm
    title = _("New Application")
    success_message = _(
        "The application «{application_name}» has been created. "
        "Identifiers have been generated, here they are: \n\n"
        "Client ID : {client_id}\n"
        "Client Secret : {client_secret}\n\n"
        "This is the first and last time this secret displayed!"
    )
    permissions = "creme_api.can_admin"

    def get_success_message(self):
        return self.success_message.format(
            application_name=self.object.name,
            client_id=self.object.client_id,
            client_secret=self.object._client_secret,
        )

    def form_valid(self, form):
        response = super(ApplicationCreation, self).form_valid(form)
        message = self.get_success_message()
        messages.success(self.request, message)
        return response


class ApplicationEdition(generic.CremeModelEditionPopup):
    model = Application
    form_class = ApplicationForm
    pk_url_kwarg = "application_id"
    permissions = "creme_api.can_admin"


class ApplicationDeletion(generic.CremeModelDeletion):
    model = Application
    pk_url_kwarg = "application_id"
    permissions = "creme_api.can_admin"
