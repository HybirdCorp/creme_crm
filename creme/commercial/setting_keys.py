from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.setting_key import SettingKey

orga_approaches_key = SettingKey(
    id='commercial-display_only_orga_demco_on_orga_detailview',
    description=_(
        "Display only organisations' commercial approaches on organisations' file."
        " (Otherwise, display organisations', managers', employees', "
        "related opportunities' commercial approaches)"
    ),
    app_label='commercial', type=SettingKey.BOOL,
)
