# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme_core.registry import creme_registry
from creme_core.gui.menu import creme_menu

from recurrents.models import RecurrentGenerator


creme_registry.register_app('recurrents', _(u'Recurrent document'), '/recurrents')
creme_registry.register_entity_models(RecurrentGenerator)

creme_menu.register_app('recurrents', '/recurrents/', 'Documents récurrents')
reg_menu = creme_menu.register_menu
reg_menu('recurrents', '/recurrents/',              _(u'Portal'))
reg_menu('recurrents', '/recurrents/generators',    _(u'All recurrent generators'))
reg_menu('recurrents', '/recurrents/generator/add', _(u'Add a generator'))
