# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015  Hybird
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

from json import loads as jsonloads, dumps as jsondumps
import logging

from django.contrib.contenttypes.models import ContentType
from django.db.models import TextField, FieldDoesNotExist
from django.utils.translation import ugettext as _

from ..core.entity_cell import EntityCellRegularField
from .base import CremeModel
from .fields import CTypeForeignKey

logger = logging.getLogger(__name__)


class FieldsConfig(CremeModel):
    content_type     = CTypeForeignKey(editable=False, primary_key=True) #verbose_name=_(u'Related type') #TODO: OneToOne
    raw_descriptions = TextField(editable=False) # null=True  #TODO: JSONField ?

    HIDDEN = 'hidden'

    _excluded_fnames = None

    class Meta:
        app_label = 'creme_core'

    class InvalidAttribute(Exception):
        pass

    class LocalCache(object):
        __slots__ = ('_configs', )

        def __init__(self):
            self._configs = {}

        def get_4_model(self, model):
            configs = self._configs
            fconf = configs.get(model)

            if fconf is None:
                configs[model] = fconf = FieldsConfig.get_4_model(model)

            return fconf

    def __unicode__(self):
        return _('Configuration of %s') % self.content_type

    @staticmethod
    def _check_descriptions(model, descriptions):
        safe_descriptions = []
        errors = False
        get_field = model._meta.get_field
        HIDDEN = FieldsConfig.HIDDEN

        for field_name, field_conf in descriptions:
            try:
                field = get_field(field_name)
            except FieldDoesNotExist as e:
                logger.warn('FieldsConfig: problem with field "%s" ("%s")', field_name, e)
                errors = True
                continue

            if not field.get_tag('optional'):
                logger.warn('FieldsConfig: the field "%s" is not optional', field_name)
                errors = True
                continue

            for name, value in field_conf.iteritems():
                if name != HIDDEN:
                    raise FieldsConfig.InvalidAttribute('Invalid attribute name: "%s"' % name)

                if not isinstance(value, bool):
                    raise FieldsConfig.InvalidAttribute('Invalid attribute value: "%s"' % value)

            safe_descriptions.append((field_name, field_conf))

        return errors, safe_descriptions

    @staticmethod
    def create(model, descriptions=()): # TODO: in a manager ?
        return FieldsConfig.objects.create(content_type=ContentType.objects.get_for_model(model),
                                           descriptions=descriptions,
                                          )

    @property # TODO: cached_property ??
    def descriptions(self):
        """Getter.
        @returns Sequence of couples (field_name, attributes). 'attributes' is
                 a dictionary with keys are in {FieldsConfig.HIDDEN} (yes only
                 one at the moment), and values are Booleans.
                 eg:
                    [('phone',    {FieldsConfig.HIDDEN: True}),
                     ('birthday', {FieldsConfig.HIDDEN: True}),
                    ]
        """
        errors, desc = self._check_descriptions(self.content_type.model_class(),
                                                jsonloads(self.raw_descriptions),
                                               )

        if errors:
            logger.warn('FieldsConfig: we save the corrected descriptions.')
            self.descriptions = desc
            self.save()

        return desc

    @descriptions.setter
    def descriptions(self, value):
        self.raw_descriptions = jsondumps(
                self._check_descriptions(self.content_type.model_class(), value)[1]
            )

    @staticmethod
    def filter_cells(model, cells):
        fconf_cache = {}
        get_4_model = FieldsConfig.get_4_model

        def get_fconf(model):
            fconf = fconf_cache.get(model)

            if fconf is None:
                fconf_cache[model] = fconf = get_4_model(model)

            return fconf

        for cell in cells:
            if isinstance(cell, EntityCellRegularField):
                field_info = cell.field_info
                fconf = get_fconf(model) if len(field_info) == 1 else \
                        get_fconf(field_info[0].rel.to)

                if fconf is not None and fconf.is_field_hidden(field_info[-1]):
                    continue

            yield cell

    @staticmethod
    def get_4_model(model): # TODO: in a manager
        # TODO: cache
        ct = ContentType.objects.get_for_model(model)

        return FieldsConfig.objects.filter(content_type=ct).first() or \
               FieldsConfig(content_type=ct, descriptions=())

    @property
    def hidden_fields(self):
        get_field = self.content_type.model_class()._meta.get_field
        HIDDEN = self.HIDDEN

        for field_name, field_conf in self.descriptions:
            if field_conf.get(HIDDEN, False):
                yield get_field(field_name)

    def is_field_hidden(self, field):
        excluded = self._excluded_fnames

        if excluded is None:
            # TODO: factorise with hidden_fields() ?
            HIDDEN = self.HIDDEN
            self._excluded_fnames = excluded = {
                fname for fname, attrs in self.descriptions if attrs.get(HIDDEN, False)
            }

        return field.name in excluded

    @classmethod
    def update_form_fields(cls, instance, form_fields):
        fields_conf = FieldsConfig.get_4_model(instance.__class__)

        for field_name, field_conf in fields_conf.descriptions:
            if field_conf.get(cls.HIDDEN, False):
                form_fields.pop(field_name, None)
