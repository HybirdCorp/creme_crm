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

from itertools import chain
from logging import info

from django.db.models import Q, ManyToManyField
from django.forms.models import modelform_factory
from django.forms import Field, BooleanField, ModelChoiceField, ModelMultipleChoiceField, ValidationError, IntegerField
from django.forms.widgets import SelectMultiple, HiddenInput
from django.forms.util import flatatt
from django.utils.translation import ugettext_lazy as _, ugettext
from django.utils.safestring import mark_safe
from django.utils.encoding import smart_unicode
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User

from creme_core.models import CremePropertyType, CremeProperty, RelationType, Relation, CremeEntity
from creme_core.entities_access.functions_for_permissions import read_object_or_die
from base import CremeForm, CremeModelForm, FieldBlockManager
from fields import RelatedEntitiesField, CremeEntityField
from widgets import OrderedMultipleChoiceWidget

from documents.models import Document


def _csv_to_list(line_str):
    return [word.strip('"').strip() for word in smart_unicode(line_str).split(',')]


class CSVUploadForm(CremeForm):
    csv_step       = IntegerField(widget=HiddenInput)
    csv_document   = CremeEntityField(label=_(u'Fichier CSV'), model=Document,
                                      help_text=_(u"""Un fichier contenant les valeurs des champs d'une fiche, séparées par des virgules et chacune entourée par des guillemets "."""))
    csv_has_header = BooleanField(label=_(u'Entête présent ?'), required=False,
                                  help_text=_(u"""La 1ère ligne du fichier contient-il l'entête des colonnes de valeurs (ex: "Nom","Prénom") ?"""))


    def __init__(self, request, *args, **kwargs):
        super(CSVUploadForm, self).__init__(*args, **kwargs)
        self._request    = request
        self._csv_header = None

    @property
    def csv_header(self):
        return self._csv_header

    def clean(self):
        cleaned_data = self.cleaned_data
        csv_document = cleaned_data['csv_document']

        die_status = read_object_or_die(self._request, csv_document)
        if die_status:
            raise ValidationError(_("Vous n'avez pas les droits pour lire ce document.")) #TODO: constant

        if cleaned_data['csv_has_header']:
            try:
                filedata = csv_document.filedata
                filedata.open()
                self._csv_header = _csv_to_list(filedata.readline())
            except Exception, e:
                raise ValidationError(_("Erreur lors de la lecture du document: %s.") % e)
            finally:
                filedata.close()

        return cleaned_data


class LimitedList(object):
    def __init__(self, max_size):
        self._max_size = max_size
        self._size = 0
        self._data = []

    def append(self, obj):
        if self._size < self._max_size:
            self._data.append(obj)
        self._size += 1

    @property
    def max_size(self):
        return self._max_size

    def __len__(self):
        return self._size

    def __nonzero__(self):
        return bool(self._size)

    def __iter__(self):
        return iter(self._data)


class CSVExtractor(object):
    def __init__(self, column_index, default_value, value_castor):
        self._column_index  = column_index
        self._default_value = default_value
        self._value_castor  = value_castor
        self._subfield_search = None
        self._fk_model = None
        self._m2m = None

    def set_subfield_search(self, subfield_search, subfield_model, multiple):
        self._subfield_search = str(subfield_search)
        self._fk_model  = subfield_model
        self._m2m = multiple

    def extract_value(self, line):
        if self._column_index: #0 -> not in csv
            value = line[self._column_index - 1]

            if self._subfield_search:
                try:
                    retriever = self._fk_model.objects.filter if self._m2m else self._fk_model.objects.get
                    return retriever(**{self._subfield_search: value})
                except Exception, e: #TODO: improve exception
                    info('Exception while extracting value: %s', e) #TODO: log error in errors list shown to user ??
                    value = None

            if not value:
                value = self._default_value
        else:
            value = self._default_value

        return self._value_castor(value)


class CSVExtractorWidget(SelectMultiple):
    def __init__(self, *args, **kwargs):
        super(CSVExtractorWidget, self).__init__(*args, **kwargs)
        self.default_value_widget = None
        self.subfield_select = None

    def _render_select(self, name, choices, sel_idx, attrs=None):
        output = ['<select %s>' % flatatt(self.build_attrs(attrs, name=name))]

        output.extend(u"""<option value="%s" %s>%s</option>""" %
                        (opt_value, (u'selected="selected"' if sel_idx == i else u''), opt_label)
                            for i, (opt_value, opt_label) in enumerate(choices))

        output.append('</select>')

        return u'\n'.join(output)

    def render(self, name, value, attrs=None, choices=()):
        attrs = self.build_attrs(attrs, name=name)
        output = [u'<table %s><tbody><tr><td>' % flatatt(attrs)]

        if not value:
            value = {}

        out_append = output.append
        rselect    = self._render_select

        out_append(rselect("%s_colselect" % name, choices=chain(self.choices, choices),
                           sel_idx=int(value.get('selected_column', -1)),
                           attrs={'class': 'csv_col_select'}))

        if self.subfield_select:
            out_append(u"""</td>
                           <td class="csv_subfields_select">%(label)s %(select)s
                            <script type="text/javascript">
                                $(document).ready(function() {
                                    creme.forms.toCSVImportField('%(id)s');
                                });
                            </script>""" % {
                          'label':  ugettext(u'Chercher selon:'),
                          'select': rselect("%s_subfield" % name, choices=self.subfield_select, sel_idx=None),
                          'id':     attrs['id'],
                        })


        out_append(u"""</td><td>&nbsp;%s:%s</td></tr></tbody></table>""" %
                        (_(u"Valeur par défaut"), self.default_value_widget.render("%s_defval" % name, value.get('default_value'))))

        return mark_safe(u'\n'.join(output))

    def value_from_datadict(self, data, files, name):
        get = data.get
        return {
                'selected_column':  get("%s_colselect" % name),
                'subfield_search':  get("%s_subfield" % name),
                'default_value':    self.default_value_widget.value_from_datadict(data, files, "%s_defval" % name)
               }


class CSVExtractorField(Field):
    default_error_messages = {
    }

    def __init__(self, choices, modelfield, modelform_field, *args, **kwargs):
        super(CSVExtractorField, self).__init__(self, widget=CSVExtractorWidget, *args, **kwargs)
        self.required = modelform_field.required
        self._modelfield = modelfield

        widget = self.widget

        self._choices = choices
        widget.choices = choices

        self._original_field = modelform_field
        widget.default_value_widget = modelform_field.widget

        if modelfield.rel:
            widget.subfield_select = [(field.name, field.verbose_name) for field in modelfield.rel.to._meta.fields]

    def clean(self, value):
        col_index = int(value['selected_column'])
        def_value = value['default_value']

        if self.required and not col_index:
            if not def_value:
                raise ValidationError(self.error_messages['required'])

            self._original_field.clean(def_value) #to raise ValidationError in needed

        extractor = CSVExtractor(col_index, def_value, self._original_field.clean)

        subfield_search = value['subfield_search']
        if subfield_search:
            modelfield = self._modelfield
            extractor.set_subfield_search(subfield_search, modelfield.rel.to, isinstance(modelfield, ManyToManyField))

        return extractor


class CSVImportForm(CremeModelForm):
    csv_step       = IntegerField(widget=HiddenInput)
    csv_document   = IntegerField(widget=HiddenInput)
    csv_has_header = BooleanField(widget=HiddenInput, required=False)

    blocks = FieldBlockManager(('general', _(u'Import depuis un fichier CSV'), '*'))

    def __init__(self, request, *args, **kwargs):
        super(CSVImportForm, self).__init__(*args, **kwargs)
        self._request = request
        self.import_errors = LimitedList(50)
        self.imported_objects_count = 0

    def clean_csv_document(self):
        document_id = self.cleaned_data['csv_document']

        try:
            csv_document = Document.objects.get(pk=document_id)
        except Document.DoesNotExist:
            raise ValidationError(_("Ce document n'existe pas/plus."))

        die_status = read_object_or_die(self._request, csv_document)
        if die_status:
            raise ValidationError(_("Vous n'avez pas les droits pour lire ce document."))

        return csv_document

    def _post_instance_creation(self, instance): #overload me
        pass

    def save(self):
        model_class = self._meta.model
        get_cleaned = self.cleaned_data.get

        exclude = frozenset(self._meta.exclude)
        regular_fields   = []
        extractor_fields = []

        for field in model_class._meta.fields:
            fname = field.name

            if fname in exclude:
                continue

            cleaned = get_cleaned(fname)
            if not cleaned:
                continue

            good_fields = extractor_fields if isinstance(cleaned, CSVExtractor) else regular_fields
            good_fields.append((fname, cleaned))

        filedata = self.cleaned_data['csv_document'].filedata
        filedata.open()
        lines = filedata.xreadlines()

        if get_cleaned('csv_has_header'):
            lines.next()

        for file_line in lines:
            try:
                line = _csv_to_list(file_line)

                instance = model_class()

                for name, cleaned_field in regular_fields:
                    setattr(instance, name, cleaned_field)

                for name, cleaned_field in extractor_fields:
                    setattr(instance, name, cleaned_field.extract_value(line))

                instance.save()
                self.imported_objects_count += 1

                self._post_instance_creation(instance)

                for m2m in self._meta.model._meta.many_to_many:
                    extractor = get_cleaned(m2m.name) #can be a regular_field ????
                    if extractor:
                        setattr(instance, m2m.name, extractor.extract_value(line))
            except Exception, e:
                self.import_errors.append((line, str(e)))
                info('Exception in CSV importing: %s (%s)', e, type(e))

        filedata.close()


class CSVImportForm4CremeEntity(CSVImportForm):
    user = ModelChoiceField(label=_('Utilisateur'), queryset=User.objects.all(), empty_label=None)

    blocks = FieldBlockManager(('general',    _(u'Infos génériques'),     '*'),
                               ('properties', _(u'Propriétés associées'), ('property_types',)),
                               ('relations',  _(u'Relations associées'),  ('relations',)),
                              )

    property_types = ModelMultipleChoiceField(label=_(u'Propriétés'), required=False,
                                              queryset=CremePropertyType.objects.none(),
                                              widget=OrderedMultipleChoiceWidget)
    relations      = RelatedEntitiesField(label=_(u'Relations'), required=False)

    class Meta:
        exclude = ('is_deleted', 'is_actived')

    def __init__(self, *args, **kwargs):
        super(CSVImportForm4CremeEntity, self).__init__(*args, **kwargs)

        fields = self.fields
        ct     = ContentType.objects.get_for_model(self._meta.model)

        fields['property_types'].queryset = CremePropertyType.objects.filter(Q(subject_ctypes=ct) | Q(subject_ctypes__isnull=True))
        fields['relations'].relation_types = RelationType.get_compatible_ones(ct)

    def _post_instance_creation(self, instance):
        cleaned_data = self.cleaned_data

        for prop_type in cleaned_data['property_types']:
            CremeProperty(type=prop_type, creme_entity=instance).save()

        user_id = instance.user.id

        for relationtype_id, entity in cleaned_data['relations']:
            relation = Relation()
            relation.user_id = user_id
            relation.type_id = relationtype_id
            relation.subject_entity = instance
            relation.object_entity_id = entity.id
            relation.save()


def form_factory(ct, header):
    choices = [(0, _('Pas dans le CSV'))]
    header_dict = {}

    if header:
        for i, col_name in enumerate(header):
            i += 1
            choices.append((i, _(u'Colonne %(index)s - %(name)s') % {'index': i, 'name': col_name}))
            header_dict[col_name.lower()] = i
    else:
        choices.extend((i, _(u'Colonne %i') % i) for i in xrange(1, 21))

    def formfield_factory(modelfield):
        formfield = modelfield.formfield()

        if not formfield: #happens for crementity_ptr (OneToOneField)
            return None

        selected_column = header_dict.get(modelfield.verbose_name.lower())
        if selected_column is None:
            selected_column = header_dict.get(modelfield.name.lower(), 0)

        return CSVExtractorField(choices, modelfield, formfield, label=modelfield.verbose_name,
                                 initial={'selected_column': selected_column})


    model_class = ct.model_class()
    base_form_class = CSVImportForm4CremeEntity if issubclass(model_class, CremeEntity) else CSVImportForm

    return modelform_factory(model_class, form=base_form_class, formfield_callback=formfield_factory)
