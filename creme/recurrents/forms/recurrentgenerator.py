################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import CremeEntityForm
from creme.creme_core.forms.fields import EntityCTypeChoiceField
from creme.creme_core.gui.custom_form import CustomFormExtraSubCell

from ..registry import recurrent_registry


class GeneratorCTypeSubCell(CustomFormExtraSubCell):
    sub_type_id = 'recurrents_ctype'
    verbose_name = _('Type of resource used as template')

    registry = recurrent_registry

    def formfield(self, instance, user, **kwargs):
        has_perm = user.has_perm_to_create
        get_ct = ContentType.objects.get_for_model

        return EntityCTypeChoiceField(
            label=self.verbose_name,
            # TODO: accept models too ?
            ctypes=[get_ct(model) for model in self.registry.models if has_perm(model)],
        )

    def post_clean_instance(self, *, instance, value, form):
        if value:
            instance.ct = value


class BaseRecurrentGeneratorCustomForm(CremeEntityForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.last_generation:
            del self.fields['first_generation']
