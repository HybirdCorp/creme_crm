from django.conf import settings
from django.utils.functional import lazy
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.setting_key import SettingKey

payment_info_key = SettingKey(
    id='billing-display_payment_info_only_creme_orga',
    description=lazy(
        lambda: gettext(
            'Display payment information block only on the '
            'detailview of organisations managed by {software}'
        ).format(software=settings.SOFTWARE_LABEL),
        str
    )(),
    app_label='billing', type=SettingKey.BOOL,
)
button_redirection_key = SettingKey(
    id='billing-button_redirection',
    description=_(
        'Go the detailview of the billing document created '
        'with the button (of the button bar) after the creation? '
        '(ie: «No» means «remain on the Contact/Organisation detailview»)'
    ),
    app_label='billing', type=SettingKey.BOOL,
)
