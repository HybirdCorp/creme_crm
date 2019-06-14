# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2019  Hybird
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

from fnmatch import fnmatch
import logging

from django import forms
from django.db.migrations.serializer import serializer_factory
from django.utils.translation import gettext_lazy as _, gettext, ngettext_lazy

from creme.creme_core.creme_jobs import deletor_type
from creme.creme_core.core import deletion
from creme.creme_core.forms.base import CremeModelForm, FieldBlockManager
from creme.creme_core.forms.widgets import Label
from creme.creme_core.models import Job, FieldsConfig, DeletionCommand
from creme.creme_core.utils.translation import get_model_verbose_name

logger = logging.getLogger(__name__)


class ReplacingHandler:
    """Manages how to replace a deleted instance used by a ForeignKey by another
    instance.
    The handler provides a form-field to allow the user to chose which
    replacement to perform, & can build the corresponding instance of
    <creme_core.core.deletion.Replacer>.

    Attributes:
        - field: the ForeignKey we want to update.
        - field_is_hidden: is the ForeignKey hidden (ie: Creme's FieldsConfig feature).
        - instance_to_delete
        - blocking: True means "the deletion cannot be performed".
        - key: a string identifying the handler (tips: used as form-field name).
        - count: Number of instances which are referencing "instance_to_delete"
                 through the ForeignKey.
    """
    def __init__(self, *, model_field, model_field_hidden, instance_to_delete, key_prefix=''):
        """Constructor.
        @param model_field: Instance of <django.db.models.ForeignKey>.
        @param model_field_hidden: Boolean indicating if "model_field" is hidden
               (see creme_core.models.FieldsConfig).
        @param instance_to_delete: Instance of <django.db.models.Model> the user
               wants to delete. Its type must correspond to "model_field".
        @param key_prefix: string used as prefix for the handler's key.
        """
        self.field = model_field
        self.field_is_hidden = model_field_hidden
        self.instance_to_delete = instance_to_delete
        self.blocking = False

        model = model_field.model
        self.key = '{prefix}{app}__{model}_{field}'.format(
            prefix=key_prefix,
            app=model._meta.app_label,
            model=model.__name__.lower(),
            field=model_field.name,
        )

        self.count = self._count_related_instances()

    def _build_formfield_label(self):
        field = self.field
        return '{} - {}'.format(field.model._meta.verbose_name,
                                field.verbose_name,
                               )

    def _count_related_instances(self):
        field = self.field

        return field.model \
                    ._default_manager \
                    .filter(**{field.name: self.instance_to_delete}) \
                    .count()

    def get_form_field(self):
        "@return A <django.forms.Field> instance, or <None>."
        raise NotImplementedError

    def replacer(self, new_value):
        "@return A <creme_core.core.deletion.Replacer> instance, or <None>."
        return deletion.FixedValueReplacer(
            model_field=self.field,
            value=new_value,
        )


class LabelReplacingHandler(ReplacingHandler):
    """Specialization of ReplacingHandler to display a message to the user
    (ie: no choice about the replacement).
    """
    empty_message = _('OK: no instance of «{model}».')
    instances_message = ngettext_lazy(
        'BEWARE: {count} instance of «{model}».',
        'BEWARE: {count} instances of «{model}».',
    )

    def _build_message_formfield(self, message):
        return forms.CharField(
            label=self._build_formfield_label(),
            widget=Label,
            initial=message,
            required=False,
        )

    def _get_message_context(self):
        count = self.count

        return {
            'count':    count,
            'model':    get_model_verbose_name(model=self.field.model, count=count),
            'instance': self.instance_to_delete,
        }

    def get_form_field(self):
        count = self.count
        fmt = (self.instances_message % count) if count else self.empty_message

        return self._build_message_formfield(
            message=fmt.format(**self._get_message_context()),
        )


class ChoiceReplacingHandler(ReplacingHandler):
    """Specialization of ReplacingHandler to ask to the user which instance
    to use as replacement.
    """
    def _build_formfield_queryset(self):
        instance = self.instance_to_delete

        return type(instance)._default_manager.exclude(pk=instance.pk)

    def _get_choicefield_data(self):
        return {
            'queryset': self._build_formfield_queryset(),
            'label':    self._build_formfield_label(),
        }

    def get_form_field(self):
        return forms.ModelChoiceField(**self._get_choicefield_data())


class CascadeHandler(LabelReplacingHandler):
    empty_message = _('OK: no instance of «{model}» have to be deleted.')
    instances_message = ngettext_lazy(
        'BEWARE: {count} instance of «{model}» will be deleted.',
        'BEWARE: {count} instances of «{model}» will be deleted.',
    )

    def get_form_field(self):
        return None if self.field_is_hidden and not self.count else super().get_form_field()

    def replacer(self, new_value):
        return None


class ProtectHandler(LabelReplacingHandler):
    empty_message = _('OK: there is no related instance of «{model}», '
                      'the deletion can be done.'
                     )
    instances_message = ngettext_lazy(
        'ERROR: {count} instance of «{model}» uses «{instance}» '
        'so the deletion is not possible.',
        'ERROR: {count} instances of «{model}» use «{instance}» '
        'so the deletion is not possible.',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.blocking = bool(self.count)

    def get_form_field(self):
        return None if self.field_is_hidden and not self.count else super().get_form_field()

    def replacer(self, new_value):
        return None


class SetNullHandler(LabelReplacingHandler):
    empty_message = _('OK: no instance of «{model}» have to be updated.')
    instances_message = ngettext_lazy(
        'BEWARE: {count} instance of «{model}» uses «{instance}» & '
        'will be updated (the field will be emptied).',
        'BEWARE: {count} instances of «{model}» use «{instance}» & '
        'will be updated (the field will be emptied).',
    )

    def get_form_field(self):
        return None if self.field_is_hidden else super().get_form_field()


class SetDefaultHandler(LabelReplacingHandler):
    empty_message = _('OK: no instance of «{model}» have to be updated.')
    instances_message = ngettext_lazy(
        'BEWARE: {count} instance of «{model}» uses «{instance}» & '
        'will be updated (the field will be set to «{fallback}»).',
        'BEWARE: {count} instances of «{model}» use «{instance}» & '
        'will be updated (the field will be set to «{fallback}»).',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.field
        model = field.remote_field.model
        try:
            default_value = field.remote_field.model.objects.get(pk=field.get_default())
        except model.DoesNotExist:
            # TODO: test
            logger.exception('The default value for the field <%s> seems buggy.', field)

            default_value = False
            self.blocking = True

        self.default_value = default_value

    def _get_message_context(self):
        ctxt = super()._get_message_context()
        ctxt['fallback'] = self.default_value

        return ctxt

    def get_form_field(self):
        if self.blocking:
            field = self._build_message_formfield(
                _('ERROR: the default value is invalid. '
                  'Please contact your administrator.'
                 )
            )
        elif not self.field_is_hidden:
            field = super().get_form_field()
        else:
            field = None

        return field

    def replacer(self, new_value):
        # if self.blocking: TODO ?
        return super().replacer(new_value=self.default_value)


class SetHandler(LabelReplacingHandler):
    empty_message = _('OK: no instance of «{model}» have to be updated.')
    instances_message = ngettext_lazy(
        'BEWARE: {count} instance of «{model}» uses «{instance}» & '
        'will be updated (the field will be set to the fallback value).',
        'BEWARE: {count} instances of «{model}» use «{instance}» & '
        'will be updated (the field will be set to the fallback value).',
    )

    def get_form_field(self):
        return None if self.field_is_hidden else super().get_form_field()

    def replacer(self, new_value):
        return None if self.field_is_hidden else deletion.SETReplacer(model_field=self.field)


class CremeReplaceNullHandler(ChoiceReplacingHandler):
    def _get_choicefield_data(self):
        data = super()._get_choicefield_data()
        field = self.field
        data['required'] = (not field.blank or not field.null)  # TODO: test

        return data

    def get_form_field(self):
        return None if self.field_is_hidden else super().get_form_field()


class CremeReplaceHandler(ChoiceReplacingHandler):
    instances_message = ProtectHandler.instances_message

    def _get_choicefield_data(self):
        data = super()._get_choicefield_data()
        data['empty_label'] = None

        return data

    def get_form_field(self):
        return None if self.field_is_hidden and not self.count else super().get_form_field()

    def replacer(self, new_value):
        return None if self.field_is_hidden and not self.count else super().replacer(new_value)


class DeletionForm(CremeModelForm):
    blocks = FieldBlockManager(('general', _('Replacement'), '*'))

    # TODO: what about deletion.DO_NOTHING ?!
    handler_classes = {
        'django.db.models.deletion.CASCADE':     CascadeHandler,
        'django.db.models.deletion.PROTECT':     ProtectHandler,
        'django.db.models.deletion.SET_NULL':    SetNullHandler,
        'django.db.models.deletion.SET_DEFAULT': SetDefaultHandler,
        '*SET(*)':                               SetHandler,

        'creme.creme_core.models.deletion.CREME_REPLACE_NULL': CremeReplaceNullHandler,
        'creme.creme_core.models.deletion.CREME_REPLACE':      CremeReplaceHandler,
    }

    class Meta:
        model = DeletionCommand
        fields = ()

    def __init__(self, instance_to_delete, handler_classes=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.instance_to_delete = instance_to_delete
        self.handlers = []
        fields = self.fields

        get_model_conf = FieldsConfig.LocalCache().get_4_model
        handler_classes = handler_classes or self.handler_classes

        # TODO: M2M ??
        for field in type(instance_to_delete)._meta.get_fields(include_hidden=True):
            if field.one_to_many:
                related_field = field.field
                hidden = get_model_conf(related_field.model).is_field_hidden(related_field)
                # NB: we use the django's migration tool to get a string pattern of the attribute "on_delete".
                delete_signature = serializer_factory(
                    related_field.remote_field.on_delete
                ).serialize()[0]

                for handler_pattern, handler_cls in handler_classes.items():
                    if fnmatch(delete_signature, handler_pattern):
                        handler = handler_cls(
                            model_field=related_field,
                            model_field_hidden=hidden,
                            instance_to_delete=instance_to_delete,
                            key_prefix='replace_',
                        )
                        self.handlers.append(handler)

                        form_field = handler.get_form_field()
                        if form_field:
                            fields[handler.key] = form_field

                        break
                else:
                    raise ValueError(gettext(
                        'The field "{}.{}" cannot be deleted because its '
                        '"on_delete" constraint is not managed. '
                        'Please contact your administrator.'.format(
                            related_field.model.__name__,
                            related_field.name,
                        )
                    ))

    def clean(self):
        cdata = super().clean()

        if not self._errors:
            for handler in self.handlers:
                if handler.blocking:
                    self.add_error(handler.key, _('Deletion is not possible.'))

        return cdata

    def save(self, *args, **kwargs):
        instance = self.instance

        # TODO: improve CremeJSONEncoder to serialize iterators & remove list().
        get_data = self.cleaned_data.get
        instance.replacers = list(
            filter(None,
                   (handler.replacer(get_data(handler.key) or None)
                       for handler in self.handlers
                   )
                  )
        )
        instance.total_count = sum(handler.count for handler in self.handlers)
        instance.job = Job.objects.create(
            type_id=deletor_type.id,
            user=self.user,
        )

        # TODO: <instance_to_delete.is_deleted = True> if field exists

        return super().save(*args, **kwargs)
