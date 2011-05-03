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

from functools import partial
from itertools import chain, ifilter
from logging import info

from django.db.models import Q, ManyToManyField
from django.db.models.fields import FieldDoesNotExist
from django.forms.models import modelform_factory
from django.forms import Field, BooleanField, ModelChoiceField, ModelMultipleChoiceField, ValidationError, IntegerField
from django.forms.widgets import SelectMultiple, HiddenInput
from django.forms.util import flatatt
from django.utils.translation import ugettext_lazy as _, ugettext
from django.utils.safestring import mark_safe
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User

from creme_core.models import CremePropertyType, CremeProperty, RelationType, Relation, CremeEntity, EntityCredentials
from creme_core.gui.csv_import import csv_form_registry
from creme_core.utils.unicode_csv import UnicodeReader #TODO: use csv.Sniffer class to guess csv format ??
from creme_core.views.entity import EXCLUDED_FIELDS
from base import CremeForm, CremeModelForm, FieldBlockManager
from fields import MultiRelationEntityField, CremeEntityField
from widgets import UnorderedMultipleChoiceWidget, ChainedInput, SelectorList #, DynamicSelect
from validators import validate_linkable_entities

from documents.models import Document


class CSVUploadForm(CremeForm):
    csv_step       = IntegerField(widget=HiddenInput)
    csv_document   = CremeEntityField(label=_(u'CSV file'), model=Document,
                                      help_text=_(u"""A file that contains the fields values of an entity on each line, """
                                                   """separated by commas and each one ca be surrounded by quotation marks " """
                                                   """(to protect a value containing a comma for example)."""
                                                 )
                                     )
    csv_has_header = BooleanField(label=_(u'Header present ?'), required=False,
                                  help_text=_(u"""Does the first line of the line contain the header of the columns (eg: "Last name","First name") ?"""))

    def __init__(self, *args, **kwargs):
        super(CSVUploadForm, self).__init__(*args, **kwargs)
        self._csv_header = None

    @property
    def csv_header(self):
        return self._csv_header

    def clean(self):
        cleaned_data = self.cleaned_data

        if not self._errors:
            csv_document = cleaned_data['csv_document']

            if not self.user.has_perm('creme_core.view_entity', csv_document):
                raise ValidationError(ugettext("You have not the credentials to read this document."))

            if cleaned_data['csv_has_header']:
                filedata = csv_document.filedata

                try:
                    filedata.open()
                    self._csv_header = UnicodeReader(filedata).next()
                except Exception, e:
                    raise ValidationError(ugettext("Error reading document: %s.") % e)
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


#Extractors (and related field/widget) for regular model's fields---------------

class CSVExtractor(object):
    def __init__(self, column_index, default_value, value_castor):
        self._column_index  = column_index
        self._default_value = default_value
        self._value_castor  = value_castor
        self._subfield_search = None
        self._fk_model = None
        self._m2m = None
        self._fk_form = None

    def set_subfield_search(self, subfield_search, subfield_model, multiple, create_if_unfound):
        self._subfield_search = str(subfield_search)
        self._fk_model  = subfield_model
        self._m2m = multiple

        if create_if_unfound:
            self._fk_form = modelform_factory(subfield_model)

    def extract_value(self, line, import_errors):
        if self._column_index: #0 -> not in csv
            value = line[self._column_index - 1]

            if self._subfield_search:
                data = {self._subfield_search: value}

                try:
                    retriever = self._fk_model.objects.filter if self._m2m else self._fk_model.objects.get
                    return retriever(**data) #TODO: improve self._value_castor avoid te direct 'return' ?
                except Exception, e:
                    fk_form = self._fk_form

                    if fk_form: #try to create the referenced instance
                        creator = fk_form(data=data)

                        if creator.is_valid():
                           creator.save()
                           return creator.instance #TODO: improve self._value_castor avoid te direct 'return' ?
                        else:
                            import_errors.append((line, ugettext(u'Error while extracting value [%(raw_error)s]: tried to retrieve and then build "%(value)s" on %(model)s') % {
                                                                'raw_error': e,
                                                                'value': value,
                                                                'model': self._fk_model._meta.verbose_name,
                                                            }
                                                ))
                    else:
                        import_errors.append((line, ugettext(u'Error while extracting value [%(raw_error)s]: tried to retrieve "%(value)s" on %(model)s') % {
                                                            'raw_error': e,
                                                            'value':     value,
                                                            'model':     self._fk_model._meta.verbose_name,
                                                        }
                                            ))

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
        self.propose_creation = False

    def _render_select(self, name, choices, sel_val, attrs=None):
        output = ['<select %s>' % flatatt(self.build_attrs(attrs, name=name))]

        output.extend(u"""<option value="%s" %s>%s</option>""" % (
                            opt_value, (u'selected="selected"' if sel_val == opt_value else u''), opt_label
                        ) for opt_value, opt_label in choices
                     )

        output.append('</select>')

        return u'\n'.join(output)

    def render(self, name, value, attrs=None, choices=()):
        value = value or {}
        attrs = self.build_attrs(attrs, name=name)
        output = [u'<table %s><tbody><tr><td>' % flatatt(attrs)]

        out_append = output.append
        rselect    = self._render_select

        out_append(rselect("%s_colselect" % name, choices=chain(self.choices, choices),
                           sel_val=int(value.get('selected_column', -1)),
                           attrs={'class': 'csv_col_select'}
                          )
                  )

        if self.subfield_select:
            out_append(u"""</td>
                           <td class="csv_subfields_select">%(label)s %(select)s %(check)s
                            <script type="text/javascript">
                                $(document).ready(function() {
                                    creme.forms.toCSVImportField('%(id)s');
                                });
                            </script>""" % {
                          'label':  ugettext(u'Search by:'),
                          'select': rselect("%s_subfield" % name, choices=self.subfield_select, sel_val=value.get('subfield_search')),
                          'check':  '' if not self.propose_creation else \
                                    '&nbsp;%s <input type="checkbox" name="%s_create" %s>' % (
                                           ugettext(u'Create if not found ?'),
                                           name,
                                           'checked' if value.get('subfield_create') else '',
                                        ),
                          'id':     attrs['id'],
                        })

        out_append(u"""</td><td>&nbsp;%s:%s</td></tr></tbody></table>""" % (
                        ugettext(u"Default value"),
                        self.default_value_widget.render("%s_defval" % name, value.get('default_value')),
                    )
                  )

        return mark_safe(u'\n'.join(output))

    def value_from_datadict(self, data, files, name):
        get = data.get
        return {
                'selected_column':  get("%s_colselect" % name),
                'subfield_search':  get("%s_subfield" % name),
                'subfield_create':  get("%s_create" % name, False),
                'default_value':    self.default_value_widget.value_from_datadict(data, files, "%s_defval" % name)
               }


class CSVExtractorField(Field):
    default_error_messages = {
    }

    def __init__(self, choices, modelfield, modelform_field, *args, **kwargs):
        super(CSVExtractorField, self).__init__(self, widget=CSVExtractorWidget, *args, **kwargs)
        self.required = modelform_field.required
        self._modelfield = modelfield
        self._can_create = False #if True and field is a FK/M2M -> the referenced model can be created

        widget = self.widget

        self._choices = choices
        widget.choices = choices

        self._original_field = modelform_field
        widget.default_value_widget = modelform_field.widget

        if modelfield.rel:
            klass = modelfield.rel.to
            is_entity = issubclass(klass, CremeEntity)
            ffilter = (lambda fieldname: fieldname not in EXCLUDED_FIELDS) if is_entity else \
                       lambda fieldname: fieldname != 'id'

            sf_choices = [(field.name, field.verbose_name) for field in klass._meta.fields if ffilter(field.name)]
            widget.subfield_select = sf_choices
            widget.propose_creation = self._can_create = (not is_entity) and (len(sf_choices) == 1) #TODO: creation creds too...

    def clean(self, value):
        col_index = int(value['selected_column'])
        def_value = value['default_value']

        if self.required and not col_index:
            if not def_value:
                raise ValidationError(self.error_messages['required'])

            self._original_field.clean(def_value) #to raise ValidationError if needed

        #TODO: check that col_index is in self._choices ???

        subfield_create = value['subfield_create']

        if not self._can_create and subfield_create:
            raise ValidationError("You can not create: %s" % self._modelfield)

        extractor = CSVExtractor(col_index, def_value, self._original_field.clean)

        subfield_search = value['subfield_search']
        if subfield_search:
            modelfield = self._modelfield
            extractor.set_subfield_search(subfield_search, modelfield.rel.to,
                                          multiple=isinstance(modelfield, ManyToManyField),
                                          create_if_unfound=subfield_create,
                                         )

        return extractor


#Extractors (and related field/widget) for relations----------------------------

class CSVRelationExtractor(object):
    def __init__(self, column_index, rtype, subfield_search, related_model, create_if_unfound):
        self._column_index    = column_index
        self._rtype           = rtype
        self._subfield_search = str(subfield_search)
        self._related_model   = related_model
        self._related_form    = modelform_factory(related_model) if create_if_unfound else None

    related_model = property(lambda self: self._related_model)

    def create_if_unfound(self):
        return self._related_form is not None

    #TODO: link credentials
    #TODO: constraint on properties for relationtypes (wait for cache in RelationType)
    def extract_value(self, line, user, import_errors):
        value = line[self._column_index - 1]

        if not value:
            return

        data = {self._subfield_search: value}

        try:
            object_entities = EntityCredentials.filter(user, self._related_model.objects.filter(**data))[:1]
        except Exception, e:
            import_errors.append((line, ugettext('Error while extracting value (%(raw_error)s) to build a Relation: tried to retrieve %(field)s="%(value)s" on %(model)s') %{
                                                'raw_error': e,
                                                'field':     self._subfield_search,
                                                'value':     value,
                                                'model':     self._related_model._meta.verbose_name,
                                            }
                                ))
            return

        if object_entities:
            object_entity = object_entities[0]
        elif self._related_form: #try to create the referenced instance
            data['user'] = user.id
            creator = self._related_form(data=data)

            if not creator.is_valid():
                import_errors.append((line, ugettext('Error while extracting value: tried to build  %(model)s with data=%(data)s => errors=%(errors)s') %{
                                                    'model':  self._related_model._meta.verbose_name,
                                                    'data':   data,
                                                    'errors': creator.errors
                                                }
                                    ))
                return

            object_entity = creator.save()
        else:
            import_errors.append((line, ugettext('Error while extracting value to build a Relation: tried to retrieve %(field)s="%(value)s" on %(model)s') % {
                                                 'field': self._subfield_search,
                                                 'value': value,
                                                 'model': self._related_model._meta.verbose_name,
                                             }
                                ))
            return

        return (self._rtype, object_entity)


class CSVMultiRelationsExtractor(object):
    def __init__(self, extractors):
        self._extractors = extractors

    def extract_value(self, line, user, import_errors):
        return filter(None, (extractor.extract_value(line, user, import_errors) for extractor in self._extractors))

    def __iter__(self):
        return iter(self._extractors)


class RelationExtractorSelector(SelectorList):
    def __init__(self, columns, relation_types, attrs=None):
        chained_input = ChainedInput(attrs)
        #InputModel = ChainedInput.Model
        attrs = {'auto': False}

        chained_input.add_dselect("column", options=columns, attrs=attrs)
        chained_input.add_dselect("rtype", options=relation_types, attrs=attrs)
        chained_input.add_dselect("ctype", options='/creme_core/relation/predicate/${rtype}/content_types/json', attrs=attrs)
        chained_input.add_dselect("searchfield", options='/creme_core/entity/get_info_fields/${ctype}/json', attrs=attrs)

        # chained input API changes.
#        chained_input.set(column=InputModel(widget=DynamicSelect, attrs=attrs, options=columns),
#                          rtype=InputModel(widget=DynamicSelect, attrs=attrs, options=relation_types),
#                          ctype=InputModel(widget=DynamicSelect, attrs=attrs, url='/creme_core/relation/predicate/${rtype}/content_types/json'),
#                          searchfield=InputModel(widget=DynamicSelect, attrs=attrs, url='/creme_core/entity/get_info_fields/${ctype}/json'),
#                         )

        super(RelationExtractorSelector, self).__init__(chained_input)

    def render(self, name, value, attrs=None):
        value = value or {}

        return mark_safe("""<input type="checkbox" name="%(name)s_can_create" %(checked)s/>%(label)s"""
                         """%(super)s""" % {
                        'name':    name,
                        'checked': 'checked' if value.get('can_create') else '',
                        'label':   ugettext(u'Create entities if they are not found ? (only fields followed by [CREATION] allows you to create, if they exist)'),
                        'super':   super(RelationExtractorSelector, self).render(name, value.get('selectorlist'), attrs),
                    })

    def value_from_datadict(self, data, files, name):
        return {
                'selectorlist': super(RelationExtractorSelector, self).value_from_datadict(data, files, name),
                'can_create':   data.get('%s_can_create' % name, False),
            }


class RelationExtractorField(MultiRelationEntityField):
    default_error_messages = {
        'fielddoesnotexist': _(u"This field doesn't exist in this ContentType."),
        'invalidcolunm':     _(u"This column is not a valid choice."),
    }

    def __init__(self, columns=(), *args, **kwargs):
        self._columns = columns
        super(RelationExtractorField, self).__init__(*args, **kwargs)

    def _create_widget(self):
        return RelationExtractorSelector(columns=self._columns,
                                         relation_types=self._get_options(self._get_allowed_rtypes_objects()),
                                        )

    def _set_columns(self, columns):
        self._columns = columns
        self._build_widget()

    columns = property(lambda self: self._columns, _set_columns); del _set_columns

    def clean(self, value):
        checked = value['can_create']
        selector_data = self.clean_json(value['selectorlist'])

        if not selector_data:
            if self.required:
                raise ValidationError(self.error_messages['required'])

            return CSVMultiRelationsExtractor([])

        if not isinstance(selector_data, list):
            raise ValidationError(self.error_messages['invalidformat'])

        clean_value = self.clean_value
        cleaned_entries = [(clean_value(entry, 'rtype',       str),
                            clean_value(entry, 'ctype',       int),
                            clean_value(entry, 'column',      int),
                            clean_value(entry, 'searchfield', str)
                           ) for entry in selector_data
                          ]

        extractors = []
        rtypes_cache = {}
        need_property_validation = False
        allowed_columns = frozenset(c[0] for c in self._columns)

        for rtype_pk, ctype_pk, column, searchfield in cleaned_entries:
            if column not in allowed_columns:
                raise ValidationError(self.error_messages['invalidcolunm'], params={'column': column})

            if rtype_pk not in self.allowed_rtypes:
                raise ValidationError(self.error_messages['rtypenotallowed'], params={'rtype': rtype_pk, 'ctype': ctype_pk})

            rtype, rtype_allowed_ctypes, rtype_allowed_properties = self._get_cache(rtypes_cache, rtype_pk, self._build_rtype_cache)

            if rtype_allowed_properties:
                need_property_validation = True

            if rtype_allowed_ctypes and ctype_pk not in rtype_allowed_ctypes:
                raise ValidationError(self.error_messages['ctypenotallowed'], params={'ctype': ctype_pk})

            try:
                ct = ContentType.objects.get_for_id(ctype_pk)
                model = ct.model_class()
                field = model._meta.get_field_by_name(searchfield)
            except ContentType.DoesNotExist:
                raise ValidationError(self.error_messages['ctypedoesnotexist'], params={'ctype': ctype_pk})
            except FieldDoesNotExist:
                raise ValidationError(self.error_messages['fielddoesnotexist'], params={'field': searchfield})

            extractors.append(CSVRelationExtractor(column_index=column,
                                                   rtype=rtype,
                                                   subfield_search=searchfield,
                                                   related_model=model,
                                                   create_if_unfound=checked,
                                                  )
                             )

        return CSVMultiRelationsExtractor(extractors)

#-------------------------------------------------------------------------------


class CSVImportForm(CremeModelForm):
    csv_step       = IntegerField(widget=HiddenInput)
    csv_document   = IntegerField(widget=HiddenInput)
    csv_has_header = BooleanField(widget=HiddenInput, required=False)

    blocks = FieldBlockManager(('general', _(u'Importing from a CSV file'), '*'))

    def __init__(self, *args, **kwargs):
        super(CSVImportForm, self).__init__(*args, **kwargs)
        self.import_errors = LimitedList(50)
        self.imported_objects_count = 0
        self.lines_count = 0

    #NB: hack to bypass the model validation (see form_factory() comment)
    def _post_clean(self):
        pass

    def clean_csv_document(self):
        document_id = self.cleaned_data['csv_document']

        try:
            csv_document = Document.objects.get(pk=document_id)
        except Document.DoesNotExist:
            raise ValidationError(ugettext("This document doesn't exist or doesn't exist any more."))

        if not self.user.has_perm('creme_core.view_entity', csv_document):
            raise ValidationError(ugettext("You have not the credentials to read this document."))

        return csv_document

    def _post_instance_creation(self, instance, line): #overload me
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

        lines = UnicodeReader(filedata)

        if get_cleaned('csv_has_header'):
            lines.next()

        for i, line in enumerate(ifilter(None, lines)):
            try:
                instance = model_class()

                for name, cleaned_field in regular_fields:
                    setattr(instance, name, cleaned_field)

                for name, cleaned_field in extractor_fields:
                    setattr(instance, name, cleaned_field.extract_value(line, self.import_errors))

                instance.save()
                self.imported_objects_count += 1

                self._post_instance_creation(instance, line)

                for m2m in self._meta.model._meta.many_to_many:
                    extractor = get_cleaned(m2m.name) #can be a regular_field ????
                    if extractor:
                        setattr(instance, m2m.name, extractor.extract_value(line, self.import_errors))
            except Exception, e:
                self.import_errors.append((line, str(e)))
                info('Exception in CSV importing: %s (%s)', e, type(e))
        else:
            self.lines_count = i + 1

        filedata.close()


class CSVImportForm4CremeEntity(CSVImportForm):
    user            = ModelChoiceField(label=_('User'), queryset=User.objects.all(), empty_label=None)
    property_types  = ModelMultipleChoiceField(label=_(u'Properties'), required=False,
                                               queryset=CremePropertyType.objects.none(),
                                               widget=UnorderedMultipleChoiceWidget)
    fixed_relations = MultiRelationEntityField(label=_(u'Fixed relations'), required=False)
    dyn_relations   = RelationExtractorField(label=_(u'Relations from CSV'), required=False)

    blocks = FieldBlockManager(('general',    _(u'Generic information'),  '*'),
                               ('properties', _(u'Related properties'),   ('property_types',)),
                               ('relations',  _(u'Associated relations'), ('fixed_relations', 'dyn_relations')),
                              )

    columns4dynrelations = [(i, 'Colunmn %s' % i) for i in xrange(1, 21)]

    #class Meta:
        #exclude = ('is_deleted', 'is_actived')

    def __init__(self, *args, **kwargs):
        super(CSVImportForm4CremeEntity, self).__init__(*args, **kwargs)

        fields = self.fields
        ct     = ContentType.objects.get_for_model(self._meta.model)

        fields['property_types'].queryset = CremePropertyType.objects.filter(Q(subject_ctypes=ct) | Q(subject_ctypes__isnull=True))

        rtype_ids = list(RelationType.get_compatible_ones(ct).values_list('id', flat=True))
        fields['fixed_relations'].allowed_rtypes = rtype_ids

        fdyn_relations = fields['dyn_relations']
        fdyn_relations.allowed_rtypes = rtype_ids
        fdyn_relations.columns = self.columns4dynrelations

        fields['user'].initial = self.user.id

    def clean_fixed_relations(self):
        relations = self.cleaned_data['fixed_relations']
        user = self.user

        #TODO: self._check_duplicates(relations, user) #see RelationCreateForm
        validate_linkable_entities([entity for rt_id, entity in relations], user)

        return relations

    def clean_dyn_relations(self):
        extractors = self.cleaned_data['dyn_relations']
        can_create = self.user.has_perm_to_create

        for extractor in extractors:
            if extractor.create_if_unfound and not can_create(extractor.related_model):
                raise ValidationError(_('You are not allowed to create: %s') % extractor.related_model._meta.verbose_name)

        return extractors

    def _post_instance_creation(self, instance, line):
        cleaned_data = self.cleaned_data

        for prop_type in cleaned_data['property_types']:
            CremeProperty(type=prop_type, creme_entity=instance).save()

        create_relation = partial(Relation.objects.create, user=instance.user, subject_entity=instance)

        for relationtype, entity in cleaned_data['fixed_relations']:
            create_relation(type=relationtype, object_entity=entity)

        for relationtype, entity in cleaned_data['dyn_relations'].extract_value(line, cleaned_data['user'], self.import_errors):
            create_relation(type=relationtype, object_entity=entity)


def extractorfield_factory(modelfield, header_dict, choices):
    formfield = modelfield.formfield()

    if not formfield: #happens for crementity_ptr (OneToOneField)
        return None

    selected_column = header_dict.get(modelfield.verbose_name.lower())
    if selected_column is None:
        selected_column = header_dict.get(modelfield.name.lower(), 0)

    return CSVExtractorField(choices, modelfield, formfield,
                             label=modelfield.verbose_name,
                             initial={'selected_column': selected_column}
                            )


#NB: we use ModelForm to get the all the django machinery to build a form from a model
#    bit we need to avoid the model validation, because we are are not building a true
#    'self.instance', but a set of instances ; we just use the regular form validation.
def form_factory(ct, header):
    choices = [(0, _('Not in the CSV file'))]
    header_dict = {}

    if header:
        fstring = ugettext(u'Column %(index)s - %(name)s')

        for i, col_name in enumerate(header):
            i += 1
            choices.append((i, fstring % {'index': i, 'name': col_name}))
            header_dict[col_name.lower()] = i
    else:
        fstring = ugettext(u'Column %i')
        choices.extend((i, fstring % i) for i in xrange(1, 21))

    model_class = ct.model_class()
    customform_factory = csv_form_registry.get(ct)

    if customform_factory:
        base_form_class = customform_factory(header_dict, choices)
    elif issubclass(model_class, CremeEntity):
        base_form_class = CSVImportForm4CremeEntity
    else:
        base_form_class = CSVImportForm

    modelform = modelform_factory(model_class, form=base_form_class,
                                  formfield_callback=partial(extractorfield_factory, header_dict=header_dict, choices=choices)
                                 )
    modelform.columns4dynrelations = choices[1:]

    return modelform
