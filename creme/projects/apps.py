# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class ProjectsConfig(CremeAppConfig):
    name = 'creme.projects'
    verbose_name = _(u'Projects')
    dependencies = ['creme.persons', 'creme.activities']
