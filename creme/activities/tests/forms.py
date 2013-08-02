# -*- coding: utf-8 -*-

try:
    #from functools import partial

    from django.utils.simplejson import dumps as jsondumps

    from creme.creme_core.tests.forms import FieldTestCase

    from ..models import ActivityType, ActivitySubType
    from ..forms.activity_type import ActivityTypeField
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('ActivityTypeFieldTestCase',)


class ActivityTypeFieldTestCase(FieldTestCase):
    @classmethod
    def setUpClass(cls):
        cls.atype = ActivityType.objects.create(id='meeting', name='Meeting',
                                                default_day_duration=0,
                                                default_hour_duration="01:00:00",
                                               )
        cls.subtype = ActivitySubType.objects.create(id='rendezvous',
                                                   name='Rendez-vous',
                                                   type=cls.atype,
                                                  )

    def _build_value(self, act_type_id, subtype_id=None):
        return jsondumps({'type': act_type_id, 'sub_type': subtype_id})

    def test_format_object(self):
        atype = self.atype
        subtype = self.subtype
        from_python = ActivityTypeField(types=ActivityType.objects.filter(pk=atype.id)).from_python
        args = (atype.id, subtype.id)
        self.assertEqual(self._build_value(*args), from_python(args))
        self.assertEqual(self._build_value(*args), from_python(subtype))

    def test_clean_empty_required(self):
        clean = ActivityTypeField(required=True).clean
        self.assertFieldValidationError(ActivityTypeField, 'required', clean, None)
        self.assertFieldValidationError(ActivityTypeField, 'required', clean, '{}')

    def test_clean_empty_not_required(self):
        clean = ActivityTypeField(required=False).clean

        with self.assertNoException():
            value = clean(None)

        self.assertIsNone(value)

        with self.assertNoException():
            value = clean('{}')

        self.assertIsNone(value)

    def test_clean_invalid_json(self):
        clean = ActivityTypeField(required=False).clean
        self.assertFieldValidationError(ActivityTypeField, 'invalidformat', clean,
                                        '{"type":"12", "sub_type":"1"'
                                       )

    def test_clean_invalid_data_type(self):
        clean = ActivityTypeField(required=False).clean
        self.assertFieldValidationError(ActivityTypeField, 'invalidtype', clean, '"this is a string"')
        self.assertFieldValidationError(ActivityTypeField, 'invalidtype', clean, "12")

    def test_clean_unknown_type(self):
        "Data injections"
        atype1 = self.atype
        atype2 = ActivityType.objects.create(id='phonecall', name='phone Call',
                                             default_day_duration=0,
                                             default_hour_duration=1,
                                            )
        subtype2 = ActivitySubType.objects.create(id='incoming', name='Incoming',
                                                  type=atype2,
                                                 )

        clean = ActivityTypeField(types=ActivityType.objects.filter(pk=atype1.id)).clean
        self.assertFieldValidationError(ActivityTypeField, 'typenotallowed', clean,
                                        self._build_value('unknown', self.subtype.id),
                                       )
        self.assertFieldValidationError(ActivityTypeField, 'subtyperequired', clean,
                                        self._build_value(atype1.id, 'unknown'),
                                       )
        self.assertFieldValidationError(ActivityTypeField, 'typenotallowed', clean,
                                        self._build_value(atype2.id, subtype2.id),
                                       )
        self.assertFieldValidationError(ActivityTypeField, 'subtyperequired', clean,
                                        self._build_value(atype1.id, subtype2.id),
                                       )

    def test_clean01(self):
        atype = self.atype
        subtype = self.subtype
        field = ActivityTypeField(types=ActivityType.objects.filter(pk=atype.id))
        self.assertEqual((atype, subtype),
                         field.clean(self._build_value(atype.id, subtype.id))
                        )

    def test_clean02(self):
        "Use 'types' setter"
        atype = self.atype
        subtype = self.subtype
        field = ActivityTypeField()
        field.types = ActivityType.objects.filter(pk=atype.id)
        self.assertEqual((atype, subtype),
                         field.clean(self._build_value(atype.id, subtype.id))
                        ) 

    def test_clean03(self):
        "Not required"
        atype = self.atype
        field = ActivityTypeField(types=ActivityType.objects.filter(pk=atype.id), required=False)
        self.assertEqual((atype, None),
                         field.clean(self._build_value(atype.id))
                        )

    def test_clean04(self):
        "No related ActivitySubType"
        atype2 = ActivityType.objects.create(id='custom', name='Custom',
                                             default_day_duration=0,
                                             default_hour_duration=1,
                                            )
        field = ActivityTypeField(types=ActivityType.objects.filter(pk__in=[self.atype.id, atype2.id]))
        self.assertEqual((atype2, None),
                         field.clean(self._build_value(atype2.id))
                        )
