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

from django.utils.encoding import smart_str, smart_unicode

#from creme_core.registry import creme_registry

#TODO: merge the 2 menu api (idea: use tags ?)
#TODO: refactor code.....

######################### 1rst Menu API #########################################

class MenuItem(object):
    __slots__ = ('url', 'name', 'perm')

    def __init__(self, url, name, perm):
        self.url  = url
        self.name = name
        self.perm = perm

    def __unicode__(self):
        return u'<MenuItem: name:%s url:%s perm:%s>' % (self.url, self.name, self.perm)


class MenuAppItem(object):
    def __init__(self, app_name, app_url, verbose_name=None):
        self.app_name = app_name
        self.app_url = app_url
        self.name = verbose_name or app_name #TODO: retrieve 'verbose_name' from creme_registry...
        self.items = []

    def __unicode__(self):
        return u'<MenuAppItem: app:%s url:%s name:%s>' % (self.app_name, self.app_url, self.name)

    def __iter__(self):
        return iter(self.items)

    def add_item(self, url, name, perm):
        self.items.append(MenuItem(url, name, perm))


class CremeMenu(object):
    def __init__(self):
        self.app_items = {}

    def __iter__(self):
        return self.app_items.itervalues()

    def register_app(self, app_name, app_url, name=None):
        if not self.app_items.has_key(app_name):
            self.app_items[app_name] = MenuAppItem(app_name, app_url, name)

    def register_item(self, app_name, item_url, item_name, item_perm): #item_perm='persons.add_organisation'
        app_item = self.app_items.get(app_name)
        if app_item is not None:
            app_item.add_item(item_url, item_name, item_perm)

    def get_item_name(self, item_url):
        for app_item in self.app_items.itervalues():
            for item in app_item:
                if smart_unicode(item.url) == smart_unicode(item_url): #TODO: smartunicode useful ???
                    return item.name

        return '' #TODO: None ? exception ??


creme_menu = CremeMenu()


######################### 2nd Menu API #########################################

#NB: use for customers who don't want the regular per app menu.

class FolderMenu(object):
    def __init__(self, folder_name, folder_url, order, folder_menu_name=None):
        self.folder_name = folder_name
        self.folder_url = folder_url
        self.folder_menu_name = ""
        self.order = order
        if folder_menu_name is None :
            self.folder_menu_name = folder_name
        else:
            self.folder_menu_name = folder_menu_name
        self.items = []

    def render(self):
        if self.folder_url:
            html = """<li><a href="%s">%s</a>""" % (self.folder_url, self.folder_menu_name)
        else:
            html = """<li><a>%s</a>""" % (self.folder_menu_name,)

        if self.items:
            html += "<ul>"
            for item in self.items:
                html += item.render()
            html += "</ul>"
        html += """</li>"""
        return html

    def __repr__ (self):
        return smart_str(u"FolderMenu : %s" % (self.folder_name,))

    def __cmp__(self, other):
        return cmp(self.order, other.order)


class LeafMenu (object):
    __slots__ = ('menu_url', 'menu_name', 'order')

    def __init__ (self, menu_url, menu_name, order):
        self.menu_url = menu_url
        self.menu_name = menu_name
        self.order = order

    def render (self):
        if self.menu_name :
            return """<li><a href="%s">%s</a></li>""" % (self.menu_url, self.menu_name)

        return """<li><a href="%s">No Name</a></li>"""

    def __repr__ (self):
        return smart_str(u"LeafMenu : %s" % (self.menu_name,))

    def __cmp__(self, other):
        return cmp(self.order, other.order)


class CremeMenu2(object):
    def __init__(self):
        self.items = []

    def register_folder(self, folder_name, folder_url, order, parent=None, folder_menu_name=None):
        if not parent:
            parent = self 
        folder = FolderMenu(folder_name, folder_url, order, folder_menu_name)
        parent.items.append(folder)
        parent.items.sort()
        return folder

    def register_leaf(self, menu_name, menu_url, order, folder=None):
        if not folder:
            folder = self
        folder.items.append(LeafMenu(menu_url, menu_name, order))
        folder.items.sort()

new_creme_menu = CremeMenu2()
