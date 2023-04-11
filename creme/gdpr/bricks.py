################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2023  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.gui.bricks import QuerysetBrick

from .models import SoonAnonymized


# TODO: "Contacts"
class SoonAnonymizedEntitiesBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('gdpr', 'soon_anonymized')
    verbose_name = _('Entities which will soon be anonymized')
    dependencies = (SoonAnonymized,)
    # order_by = 'name'
    order_by = 'id'  # TODO: entity.id? entity.modified?
    template_name = 'gdpr/bricks/soon-anonymized.html'
    configurable = False
    # NB: used by the view <creme_core.views.bricks.BricksReloading>
    # permissions = 'gdpr' TODO?

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context, SoonAnonymized.objects.all(),
        ))
