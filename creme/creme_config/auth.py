from django.utils.translation import gettext_lazy as _

from creme.creme_core.auth.special import SpecialPermission

user_config_perm = SpecialPermission(
    id='creme_config-user',
    verbose_name=_('User management'),
    description=_('Can create, edit & disable users, can change passwords'),
)
role_config_perm = SpecialPermission(
    id='creme_config-role',
    verbose_name=_('Role configuration'),
    description=_('Can create, edit & disable roles'),
)
