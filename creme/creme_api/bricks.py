from django.contrib.messages import get_messages
from django.utils.translation import gettext_lazy as _

from creme.creme_api.models import Application
from creme.creme_core.gui.bricks import QuerysetBrick


class ApplicationsBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id("creme_api", "applications")
    verbose_name = _("Applications")
    description = _(
        "Displays the list of the applications that are allowed "
        "to access Creme CRM web services.\n"
    )
    dependencies = (Application,)
    template_name = "creme_api/bricks/applications.html"
    order_by = "name"

    def detailview_display(self, context):
        messages = list(get_messages(context["request"]))
        secret_application_message = messages[0] if messages else None
        btc = self.get_template_context(
            context,
            Application.objects.all(),
            secret_application_message=secret_application_message,
        )
        return self._render(btc)
