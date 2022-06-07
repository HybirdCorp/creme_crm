from django.utils.translation import gettext_lazy as _

from creme.creme_core.gui import menu


class CremeApiEntry(menu.FixedURLEntry):
    permissions = "creme_api"
    id = "creme_api-documentation"
    label = _("Api")
    url_name = "creme_api__documentation"
