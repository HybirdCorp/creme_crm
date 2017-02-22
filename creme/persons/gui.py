# -*- coding: utf-8 -*-

from creme.creme_core.gui.menu import ViewableItem


class UserContactURLItem(ViewableItem):
    def __init__(self, id, icon=None, icon_label=''):
        super(UserContactURLItem, self).__init__(id=id, icon=icon, icon_label=icon_label)

    def render(self, context, level=0):
        user = context['user']
        contact = user.linked_contact
        img = self.render_icon(context)

        return u'<a href="%s">%s%s</a>' % (
                    contact.get_absolute_url(), img, user,
                ) if user.has_perm_to_view(contact) else \
               u'<span class="forbidden">%s%s</span>' % (img, user)
