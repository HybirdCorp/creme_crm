# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.forms import MultipleChoiceField
from django.utils.translation import ugettext_lazy as _

from creme_core.registry import creme_registry
from creme_core.models import PreferedMenuItem
from creme_core.forms import CremeForm
from creme_core.forms.widgets import OrderedMultipleChoiceWidget
from creme_core.gui.menu import creme_menu


class PreferedMenuForm(CremeForm):
    menu_entries = MultipleChoiceField(label=_(u'Menu entries'), required=False, widget=OrderedMultipleChoiceWidget)

    def __init__(self, user, *args, **kwargs):
        super(PreferedMenuForm, self).__init__(*args, **kwargs)
        self.user = user

        get_app  = creme_registry.get_app
        has_perm = user.has_perm if user else lambda perm_label: True

        apps = set((item.url, u'%s - %s' % (get_app(appitem.app_name).verbose_name, item.name))
                    for appitem in creme_menu
                        if has_perm(appitem.app_name)
                            for item in appitem.items
                                if has_perm(item.perm)
                  )

        menu_entries = self.fields['menu_entries']
        menu_entries.choices = apps
        menu_entries.choices.sort()

        menu_entries.initial = PreferedMenuItem.objects.filter(user=user).order_by('order').values_list('url', flat=True)

    def save(self):
        user = self.user

        PreferedMenuItem.objects.filter(user=user).delete()

        create_item   = PreferedMenuItem.objects.create
        get_item_name = creme_menu.get_item_name

        #NB: the default PreferedMenuItem items (user==None) will be before other ones.
        offset = 100 if user else 1

        for i, menu_url in enumerate(self.cleaned_data['menu_entries']):
            menu_name = unicode(get_item_name(menu_url))

            create_item(user=user, name=menu_name, label=menu_name, url=menu_url, order=i + offset)
