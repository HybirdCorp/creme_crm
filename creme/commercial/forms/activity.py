################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2022  Hybird
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

from functools import partial

from django.forms import BooleanField
from django.utils.translation import gettext_lazy as _

import creme.activities.forms.activity as act_forms
from creme.creme_core.gui.custom_form import CustomFormExtraSubCell

from ..models import CommercialApproach


class IsCommercialApproachSubCell(CustomFormExtraSubCell):
    sub_type_id = 'commercial_is_commercial_approach'
    verbose_name = _('Is a commercial approach?')
    is_required = False

    def formfield(self, instance, user, **kwargs):
        return BooleanField(
            label=self.verbose_name,
            help_text=_(
                'All participants (excepted users), subjects and linked entities '
                'will be linked to a commercial approach.'
            ),
            initial=True,
            required=False,
        )

    def post_save_instance(self, *, instance, value, form):
        if value:
            get_data = form.cleaned_data.get
            get_key = form.subcell_key
            subjects = [
                *get_data(get_key(act_forms.OtherParticipantsSubCell), ()),
                *get_data(get_key(act_forms.ActivitySubjectsSubCell), ()),
                *get_data(get_key(act_forms.LinkedEntitiesSubCell), ()),
            ]

            if subjects:
                create_comapp = partial(
                    CommercialApproach.objects.create,
                    title=instance.title,
                    description=instance.description,
                    related_activity=instance,
                )

                for subject in subjects:
                    create_comapp(creme_entity=subject)

        return False  # Do not save the Activity again (not modified)
