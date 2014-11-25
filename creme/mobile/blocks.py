# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014  Hybird
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

from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.gui.block import QuerysetBlock

from creme.persons.models import Contact, Organisation

from .models import MobileFavorite


class FavoritePersonsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('mobile', 'favorite_persons')
    dependencies  = (MobileFavorite,)
    verbose_name  = _(u'Favorite Contacts & Organisations (for mobile)')
    template_name = 'mobile/templatetags/block_favorite.html'
    target_ctypes = (Contact, Organisation)

    def detailview_display(self, context):
        person = context['object']
        btc = self.get_block_template_context(
                                context,
                                User.objects.filter(mobile_favorite__entity=person.id),
                                update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, person.id),
                                is_contact=isinstance(person, Contact),
                                is_orga=isinstance(person, Organisation),
                               )

        page = btc['page']
        current_user = context['user']

        current_user_fav = any(current_user == user for user in page.object_list)

        if not current_user_fav and page.paginator.num_pages > 1:
            current_user_fav = MobileFavorite.objects.filter(entity=person.id, user=current_user).exists()

        btc['current_user_fav'] = current_user_fav

        return self._render(btc)


favorite_persons_block = FavoritePersonsBlock()
