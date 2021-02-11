# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

# import warnings
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import CremeEntityForm
from creme.creme_core.forms.fields import EntityCTypeChoiceField
from creme.creme_core.gui.custom_form import CustomFormExtraSubCell

# from .. import get_rgenerator_model
from ..registry import recurrent_registry

# class RecurrentGeneratorEditForm(CremeEntityForm):
#     class Meta(CremeEntityForm.Meta):
#         model = get_rgenerator_model()
#
#     def __init__(self, *args, **kwargs):
#         warnings.warn('RecurrentGeneratorEditForm is deprecated.', DeprecationWarning)
#
#         super().__init__(*args, **kwargs)
#         if self.instance.last_generation:
#             del self.fields['first_generation']


# class RecurrentGeneratorCreateForm(RecurrentGeneratorEditForm):
#     ct = EntityCTypeChoiceField(label=_('Type of resource used as template'))
#
#     def __init__(self, *args, **kwargs):
#         warnings.warn('RecurrentGeneratorCreateForm is deprecated.', DeprecationWarning)
#
#         super().__init__(*args, **kwargs)
#
#         has_perm = self.user.has_perm_to_create
#         self.fields['ct'].ctypes = [
#             ctype for ctype in recurrent_registry.ctypes if has_perm(ctype.model_class())
#         ]
#
#     def save(self, *args, **kwargs):
#         self.instance.ct = self.cleaned_data['ct']
#
#         return super().save(*args, **kwargs)


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
            ctypes=[
                # ctype
                # for ctype in self.registry.ctypes
                # if has_perm(ctype.model_class())
                get_ct(model) for model in self.registry.models if has_perm(model)
            ],
        )

    def post_clean_instance(self, *, instance, value, form):
        if value:
            instance.ct = value


class BaseRecurrentGeneratorCustomForm(CremeEntityForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.last_generation:
            del self.fields['first_generation']
