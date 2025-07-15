################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from django.db.models import ProtectedError
from django.db.transaction import atomic
from django.forms import ModelChoiceField
from django.forms.utils import ValidationError
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.core.workflow import run_workflow_engine
from creme.creme_core.forms import CremeForm, CremeModelForm
from creme.creme_core.models import CremeProperty, CremePropertyType, Mutex
from creme.creme_core.utils import replace_related_object
from creme.creme_core.utils.html import render_limited_list
from creme.creme_core.utils.translation import verbose_instances_groups

from ..models import MarketSegment


# TODO: save/check uniqueness only if name has changed
class MarketSegmentForm(CremeModelForm):
    error_messages = {
        'duplicated_name':     _('A segment with this name already exists'),
        'duplicated_property': _('A property with the name «%(name)s» already exists'),
    }

    class Meta:
        model = MarketSegment
        fields = '__all__'

    # TODO: move to MarketSegment.clean()? (beware tp <self.ptype_text>)
    def clean_name(self):
        name = self.cleaned_data['name']
        ptype_text = MarketSegment.generate_property_text(name)

        instance = self.instance
        segments = MarketSegment.objects.filter(name=name)
        ptypes = CremePropertyType.objects.filter(text=ptype_text)

        if instance.pk:
            segments = segments.exclude(pk=instance.pk)
            ptypes = ptypes.exclude(pk=instance.property_type_id)

        if segments.exists():
            raise ValidationError(
                self.error_messages['duplicated_name'],
                code='duplicated_name',
            )

        if ptypes.exists():
            raise ValidationError(
                self.error_messages['duplicated_property'],
                params={'name': ptype_text},
                code='duplicated_property',
            )

        self.ptype_text = ptype_text

        return name

    def save(self, *args, **kwargs):
        instance = self.instance

        # TODO: move to MarketSegment.save() ?
        if instance.pk:  # Edition
            ptype = instance.property_type

            if ptype:  # NB: there is _one_ segment with no related PropertyType
                ptype.text = self.ptype_text
                ptype.save()
        else:
            # is_custom=False ==> CremePropertyType won't be deletable
            instance.property_type = CremePropertyType.objects.create(
                text=self.ptype_text, is_custom=False, app_label='commercial',
            )

        return super().save(*args, **kwargs)


class SegmentReplacementForm(CremeForm):
    to_segment = ModelChoiceField(
        label=_('Choose a segment to replace by'),
        empty_label=None,
        queryset=MarketSegment.objects.none(),
    )

    def __init__(self, instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.segment_2_delete = instance
        self.fields['to_segment'].queryset = MarketSegment.objects.exclude(pk=instance.id)

    def save(self, *args, **kwargs):
        segment_2_delete = self.segment_2_delete
        replacing_segment = self.cleaned_data['to_segment']
        mutex = Mutex.get_n_lock('commercial-replace_segment')

        try:
            with atomic(), run_workflow_engine(user=self.user):
                replace_related_object(segment_2_delete, replacing_segment)
                segment_2_delete.delete()

                ptype_2_delete = segment_2_delete.property_type

                if replacing_segment.property_type is not None:
                    replace_related_object(ptype_2_delete, replacing_segment.property_type)

                CremeProperty.objects.filter(type=ptype_2_delete).delete()
                ptype_2_delete.delete()
        except ProtectedError as e:
            # TODO: should we prevent the deletion in some cases?
            # TODO: unit test
            raise ConflictError(
                _(
                    'The segment cannot be replaced because some elements '
                    'cannot be deleted: {dependencies}'
                ).format(dependencies=render_limited_list(
                    items=[*verbose_instances_groups(e.args[1])],
                    limit=3,  # TODO: constant/attribute?
                ))
            ) from e
        finally:
            mutex.release()
