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

from django.utils.encoding import smart_str,smart_unicode

from creme_core.registry import creme_registry

#TODO: merge the 2 menu api (idea: use tags ?)
#TODO: refactor code.....

######################### 1rst Menu API #########################################

class ItemMenu(object):
    __slots__ = ('menu_url', 'menu_name')

    def __init__ (self, menu_url, menu_name):
        self.menu_url = menu_url
        self.menu_name = menu_name


class AppMenu(object):
    def __init__(self, app_name, app_url, app_menu_name=None):
        self.app_name = app_name
        self.app_url = app_url
        self.app_menu_name = ""
        if app_menu_name is None :
            self.app_menu_name = app_name
        else:
            self.app_menu_name = app_menu_name
        self.items = []


class CremeMenu(object):
    def __init__(self, creme_registry):
        self.app_menu = {}
        self.__creme_registry = creme_registry

    def register_app(self, app_name, app_url, app_menu_name=None):
        if not self.app_menu.has_key(app_name):
            self.app_menu[app_name] = AppMenu(app_name, app_url, app_menu_name)

    def register_menu(self, app_name, menu_url, menu_name):
        if self.app_menu.has_key(app_name):
            self.app_menu[app_name].items.append(ItemMenu(menu_url, menu_name))

    def get_item_url(self, menu_name):
        for app, v in self.app_menu.items():
            for item in v.items:
                if smart_unicode(item.menu_name) == smart_unicode(menu_name):
                    return item.menu_url
        return ''

    def get_item_name(self, menu_url):
        for app, v in self.app_menu.items():
            for item in v.items:
                if smart_unicode(item.menu_url) == smart_unicode(menu_url):
                    return item.menu_name
        return ''


creme_menu = CremeMenu(creme_registry)


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

    def render (self):
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
