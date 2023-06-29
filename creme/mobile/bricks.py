################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2023  Hybird
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

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from creme import persons
from creme.creme_core.gui.bricks import QuerysetBrick

from .models import MobileFavorite

Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()


class FavoritePersonsBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('mobile', 'favorite_persons')
    verbose_name = _('Favorite Contacts & Organisations (for mobile)')
    description = _(
        'Displays the users who marked the current entity as favorite in mobile views.\n'
        'App: Mobile'
    )
    dependencies = (MobileFavorite,)
    template_name = 'mobile/bricks/favorite.html'
    target_ctypes = (Contact, Organisation)

    def detailview_display(self, context):
        person = context['object']
        btc = self.get_template_context(
            context,
            get_user_model().objects.filter(mobile_favorite__entity=person.id),
            is_contact=isinstance(person, Contact),
            is_orga=isinstance(person, Organisation),
        )

        page = btc['page']
        current_user = context['user']

        current_user_fav = any(current_user == user for user in page.object_list)

        if not current_user_fav and page.paginator.num_pages > 1:
            # TODO: unit test
            current_user_fav = MobileFavorite.objects.filter(
                entity=person.id,
                user=current_user,
            ).exists()

        btc['current_user_fav'] = current_user_fav

        return self._render(btc)
