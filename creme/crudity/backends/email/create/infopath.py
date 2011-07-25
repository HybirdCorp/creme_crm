# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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
import re, logging
from itertools import ifilter
from xml.etree import ElementTree as ET
from pyexpat import ExpatError

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.fields import FieldDoesNotExist
from django.db.models.fields.files import FileField, ImageField
from django.db.models.fields.related import ForeignKey, ManyToManyField
from django.template.context import Context

from creme_core.gui.button_menu import Button
from creme_core.views.file_handling import handle_uploaded_file

from crudity.backends.email.create.base import CreateFromEmailBackend
from crudity.utils import decode_b64binary
from media_managers.models.image import Image

remove_pattern = re.compile('[\t\n\r\f\v]')

class InfopathCreateFormButton(Button):
    id_           = Button.generate_id('crudity', 'infopath_create_form')
    verbose_name  = u""
    template_name = 'crudity/templatetags/button_infopath_create_form.html'

infopath_create_form_button = InfopathCreateFormButton()


class InfopathCreateFromEmail(CreateFromEmailBackend):
#    blocks = ()
    MIME_TYPES = ['application/x-microsoft-infopathform']

    def create(self, email, current_user=None):
        MIME_TYPES = self.MIME_TYPES

        attachments = filter(lambda x: x[1].content_type in MIME_TYPES, email.attachments)

        if attachments and self.authorize_senders(email.senders):
            body = (self.strip_html(email.body_html) or email.body).replace('\r', '')
            split_body = [line.replace('\t', '') for line in body.split('\n') if line.strip()]

            if self.is_allowed_password(split_body):
                for data in ifilter(lambda x: x is not None, [self.get_data_from_infopath_file(attachment) for attachment_name, attachment in attachments]):
                    self._create(data, email.senders[0])


    def get_data_from_infopath_file(self, xml_file):
        content = xml_file.read()
        data = {}
        content = re.sub(remove_pattern, '', content.strip(), re.U)
        content = re.sub('>[\s]*<', '><', content, re.U)
#        content = content.replace('\xa0', ' ')

        if not content:
            return None

        try:
            xml = ET.fromstring(content)
        except ExpatError, e:
            logging.error(e)
            return None

        data = self.body_map.copy()
        for node in xml:
            try:
                tag = re.search('[{].*[}](?P<tag>[-_\d\s\w]+)', node.tag).groupdict()['tag']
            except AttributeError:
                continue

            if data.has_key(tag):
                children = node.getchildren()
                if children:#Multi-line
                    data[tag] = "\n".join(child.text or '' for child in children)
                else:
                    data[tag] = node.text
        return data

    def get_buttons(self):
        return [infopath_create_form_button.render(Context({'backend': self})), ] if self.is_configured else []

    @property
    def verbose_filename(self):
        return str("CremeCRM_%s" % self.verbose_name.encode('utf8').replace(' ', '_'))

    def _create_instance_before_save(self, instance, data):
        model_get_field = self.model._meta.get_field

        for field_name, field_value in data.iteritems():
            try:
                field = model_get_field(field_name)
            except FieldDoesNotExist:
                continue

            if isinstance(field, ForeignKey) and issubclass(field.rel.to, Image):
                filename, blob = decode_b64binary(field_value)
                upload_path = field.rel.to._meta.get_field('image').upload_to.split('/')#TODO: 'image' bof bof...
                img_entity = Image()
                img_entity.image = handle_uploaded_file(ContentFile(blob), path=upload_path, name=filename)
                img_entity.user  = instance.user
                img_entity.save()
                setattr(instance, field_name, img_entity)

            elif issubclass(field.__class__, FileField):
                filename, blob = decode_b64binary(field_value)
                upload_path = field.upload_to.split('/')
                setattr(instance, field_name, handle_uploaded_file(ContentFile(blob), path=upload_path, name=filename))

    def _create_instance_after_save(self, instance, data):
        model_get_field = self.model._meta.get_field
        need_new_save = False

        for field_name, field_value in data.iteritems():
            try:
                field = model_get_field(field_name)
            except FieldDoesNotExist, e:
                continue

            if issubclass(field.__class__, ManyToManyField):
                setattr(instance, field_name, field.rel.to._default_manager.filter(pk__in=field_value.split()))

        return need_new_save
