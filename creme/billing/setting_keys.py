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
            'detailed view of organisations managed by {software}'
        ).format(software=settings.SOFTWARE_LABEL),
        str
    )(),
    app_label='billing', type=SettingKey.BOOL,
)
button_redirection_key = SettingKey(
    id='billing-button_redirection',
    description=_(
        'Go the detailed view of the billing document created '
        'with the button (of the button bar) after the creation? '
        '(i.e. «No» means «remain on the Contact/Organisation detailed view»)'
    ),
    app_label='billing', type=SettingKey.BOOL,
)
emitter_edition_key = SettingKey(
    id='billing-emitter_edition',
    description=_(
        'If a Invoice/Credit Note has a number, can the source Organisation be modified?'
    ),
    app_label='billing', type=SettingKey.BOOL,
)
