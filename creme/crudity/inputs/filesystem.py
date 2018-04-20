# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017-2018  Hybird
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

import ConfigParser
import logging
from os import remove as remove_file

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

from ..backends.models import CrudityBackend
from ..models import WaitingAction
from .base import CrudityInput


logger = logging.getLogger(__name__)


class IniFileInput(CrudityInput):
    name = u'ini'
    method = 'create'
    verbose_name = _(u'File - INI')
    verbose_method = _(u'Create')  # TODO: factorise + retrieve with 'method'
    brickheader_action_templates = ('crudity/bricks/header-actions/inifile-creation-template.html',)

    # def __init__(self):
    #     super(IniFileInput, self).__init__()
    #
    #     # NB: we define an inner class + avoid using a template file in order to reduce the API (will break soon).
    #     from django.urls import reverse
    #     from django.utils.safestring import mark_safe
    #     from django.utils.translation import ugettext
    #
    #     from creme.creme_core.gui.button_menu import Button
    #     from creme.creme_core.templatetags.creme_core_tags import creme_media_url
    #
    #     class IniTemplateCreateButton(Button):
    #         id_ = Button.generate_id('crudity', 'ini_create_form')
    #         verbose_name = u''
    #
    #         def render(self, context):
    #             backend = context['backend']
    #
    #             return mark_safe(u'<a class="download" href="{url}">'
    #                                 u'<img src="{src}" border="0" title="{title}" alt="{title}" />{label}'
    #                              u'</a>'.format(
    #                                  url=reverse('crudity__dl_fs_ini_template', args=(backend.subject,)),
    #                                  title=ugettext(u'Download'),
    #                                  src=creme_media_url(context, 'images/download_22.png'),
    #                                  label=ugettext(u'File .ini template for «%s»') % backend.model._meta.verbose_name,
    #                                 )
    #                             )
    #
    #     self.register_buttons(IniTemplateCreateButton())

    def create(self, file_path):
        backend = None
        config = ConfigParser.RawConfigParser()
        ok = False

        try:
            ok = config.read(file_path)
        except Exception as e:
            logger.warn('IniFileInput.create(): invalid ini file (%s): %s', file_path, e)

        if not ok:
            logger.warn('IniFileInput.create(): invalid ini file (%s)', file_path)
        else:
            try:
                subject = config.get('head', 'action')
            except (ConfigParser.NoSectionError, ConfigParser.NoOptionError) as e:
                logger.warn('IniFileInput.create(): invalid file content for %s (%s)', file_path, e)
            else:
                backend = self.get_backend(CrudityBackend.normalize_subject(subject))

                if backend:
                    # Build data dict
                    data = dict(backend.body_map)

                    for field_name in data.keys():
                        try:
                            data[field_name] = config.get('body', field_name)
                        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError) as e:
                            logger.warn('IniFileInput.create(): invalid data in .ini file (%s): %s', file_path, e)

                    # Get owner
                    owner = None
                    CremeUser = get_user_model()
                    if backend.is_sandbox_by_user:
                        try:
                            username = config.get('head', 'username')
                        except ConfigParser.NoOptionError as e:
                            logger.warn('IniFileInput.create(): no "username" in [head] section of %s', file_path, e)
                        else:
                            query_data = {CremeUser.USERNAME_FIELD: username}

                            try:
                                owner = CremeUser.objects.get(**query_data)
                            except CremeUser.DoesNotExist:
                                logger.warn('IniFileInput.create(): no user ([head] section) corresponds to %s (%s)',
                                            query_data, file_path,
                                           )

                    if owner is None:
                        owner = CremeUser.objects.get_admin()

                    # Create instances
                    if backend.in_sandbox:
                        # TODO: factorise with other inputs
                        action = WaitingAction(action=self.method,
                                               ct=ContentType.objects.get_for_model(backend.model),
                                               source='%s - %s' % (backend.fetcher_name, self.name),
                                               subject=backend.subject,
                                               user=owner,
                                              )
                        # action.data = action.set_data(data)
                        action.set_data(data)
                        action.save()
                    else:
                        # TODO: should be a public method
                        backend._create_instance_n_history(data,
                                                           user=owner,
                                                           source='{} - {}'.format(backend.fetcher_name, self.name),
                                                          )

                    # Cleaning
                    remove_file(file_path)

        return backend
