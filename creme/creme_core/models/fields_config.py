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

        def is_fieldinfo_hidden(self, model, field_info):
            """
            @param model Class inheriting django.db.models.Model.
            @param field_info creme_core.utils.meta.FieldInfo instance.
            """
            if self.get_4_model(model).is_field_hidden(field_info[0]):
                return True

            if len(field_info) > 1:
                assert len(field_info) == 2 # TODO: manage deeper fields + unit tests

                if self.get_4_model(field_info[0].rel.to).is_field_hidden(field_info[1]):
                    return True

            return False

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

    @property
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

    def _get_hidden_field_names(self):
        excluded = self._excluded_fnames

        if excluded is None:
            HIDDEN = self.HIDDEN
            self._excluded_fnames = excluded = {
                fname for fname, attrs in self.descriptions if attrs.get(HIDDEN, False)
            }

        return excluded

    @classmethod
    def filter_cells(cls, model, cells):
        """Yields not hidden cells.
        @param model Class inheriting django.db.models.Model.
        @param cells Iterable of EntityCell instances.
        """
        fconfigs = cls.LocalCache()

        for cell in cells:
            if not isinstance(cell, EntityCellRegularField) or \
               not fconfigs.is_fieldinfo_hidden(model, cell.field_info):
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

        for field_name in self._get_hidden_field_names():
            yield get_field(field_name)

    def is_field_hidden(self, field):
        return field.name in self._get_hidden_field_names()

    def is_fieldname_hidden(self, field_name):
        "NB: if the field does not exist, it is considered as hidden."
        try:
            field = self.content_type.model_class()._meta.get_field(field_name)
        except FieldDoesNotExist:
            return True

        return self.is_field_hidden(field)

    def update_form_fields(self, form_fields):
        for field_name in self._get_hidden_field_names():
            form_fields.pop(field_name, None)
