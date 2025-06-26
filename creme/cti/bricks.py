################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017-2025  Hybird
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

from collections.abc import Sequence
from functools import reduce
from operator import or_

from django.db.models.query_utils import Q
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme import activities, persons
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.gui.bricks import PaginatedBrick
from creme.creme_core.models import (
    CremeEntity,
    EntityCredentials,
    FieldsConfig,
)
from creme.creme_core.models.fields import PhoneField

Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()
Activity = activities.get_activity_model()


class CallersBrick(PaginatedBrick):
    id = PaginatedBrick.generate_id('cti', 'callers')
    verbose_name = _('Potential callers')
    template_name = 'cti/bricks/callers.html'
    configurable = False
    page_size = 128

    caller_models: Sequence[type[CremeEntity]] = (
        Contact,
        Organisation,
    )

    def detailview_display(self, context):
        # Ensure that it will crash if we try to load it from a classic load view
        number = context['number']

        user = context['user']
        filter_viewable = EntityCredentials.filter
        fconfigs = FieldsConfig.objects.get_for_models(self.caller_models)
        all_fields_hidden = True
        callers = []

        for model in self.caller_models:
            is_hidden = fconfigs[model].is_field_hidden
            queries = [
                Q(**{field.name: number})
                for field in model._meta.fields
                if isinstance(field, PhoneField) and not is_hidden(field)
            ]

            if queries:
                all_fields_hidden = False
                callers.extend(filter_viewable(
                    user,
                    model.objects.exclude(is_deleted=True).filter(reduce(or_, queries)),
                ))

        if all_fields_hidden:
            raise ConflictError(
                gettext('All phone fields are hidden; please contact your administrator.')
            )

        can_create = user.has_perm_to_create

        return self._render(self.get_template_context(
            context,
            objects=callers,
            can_create_contact=can_create(Contact),
            contact_creation_label=Contact.creation_label,
            can_create_orga=can_create(Organisation),
            orga_creation_label=Organisation.creation_label,
            can_create_activity=can_create(Activity),
        ))
