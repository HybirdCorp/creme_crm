/* global QUnitFormMixin */

(function($) {

QUnit.module("creme.form.Field", new QUnitMixin(QUnitEventMixin,
                                                QUnitFormMixin, {
    beforeEach: function() {
        this.qunitFixture().on({
            'field-change': this.mockListener('field-change'),
            'field-prop-change': this.mockListener('field-prop-change'),
            'field-reset': this.mockListener('field-reset'),
            'field-error': this.mockListener('field-error')
        });
    }
}));

QUnit.test('creme.form.Field (defaults)', function() {
    var input = $('<input name="field_a" type="text"/>');
    var field = new creme.form.Field(input);

    equal(field.name(), 'field_a');
    equal(field.readonly(), false);
    equal(field.disabled(), false);
    equal(field.dataType(), 'text');
    equal(field.htmlType(), 'text');

    equal(field.value(), '');
    equal(field.initial(), '');

    equal(field.isValidHtml(), true);
    equal(field.isValid(), true);
    equal(field.htmlErrorCode(), undefined);
    equal(field.errorMessage(), '');
    equal(field.errorCode(), undefined);

    equal(field.clean(), '');

    this.equalOuterHtml(input, field.element());
});

QUnit.parametrize('creme.form.Field (init exceptions)', [
    [undefined, 'DOM element "undefined" is not a string nor a jQuery element'],
    [12, 'DOM element "12" is not a string nor a jQuery element'],
    [$('#unknown'), 'A single DOM element is required'],
    [$(['<input/>', '<input/>']), 'A single DOM element is required']
], function(input, message) {
    this.assertRaises(function() {
        return new creme.form.Field(input);
    }, Error, 'Error: ${message}'.template({message: message}));
});

QUnit.parametrize('creme.form.Field (types)', [
    [$('<input />'), {}, 'text', 'text'],
    [$('<input />'), {dataType: 'number'}, 'text', 'number'],

    [$('<input type="text"/>'), {}, 'text', 'text'],
    [$('<input data-type="text"/>'), {}, 'text', 'text'],

    [$('<input type="number"/>'), {}, 'number', 'number'],
    [$('<input data-type="number"/>'), {}, 'text', 'number'],
    [$('<input type="number" data-type="integer"/>'), {}, 'number', 'integer'],
    [$('<input type="text" data-type="number"/>'), {dataType: 'integer'}, 'text', 'integer'],

    [$('<input type="radio"/>'), {}, 'radio', 'text'],
    [$('<input type="radio" data-type="number"/>'), {}, 'radio', 'number'],
    [$('<input type="checkbox"/>'), {}, 'checkbox', 'text'],
    [$('<input type="checkbox" data-type="number"/>'), {}, 'checkbox', 'number']
], function(input, options, htmlType, dataType) {
    var field = new creme.form.Field(input.appendTo(this.qunitFixture()), options);
    equal(field.htmlType(), htmlType, 'htmlType');
    equal(field.dataType(), dataType, 'dataType');
});

QUnit.parametrize('creme.form.Field (readonly)', [
    [$('<input type="text" readonly/>'), {}, true],
    [$('<input type="text"/>'), {readonly: true}, true],
    [$('<input type="text" readonly/>'), {readonly: false}, false],
    [$('<input type="text"/>'), {readonly: false}, false],
    [$('<input type="text"/>'), {}, false]
], function(input, options, expected, assert) {
    var field = new creme.form.Field(input.appendTo(this.qunitFixture()), options);

    equal(field.readonly(), expected, 'is readonly');
    equal(input.is('[readonly]'), expected);

    field.readonly(false);

    equal(field.readonly(), false);
    equal(input.is('[readonly]'), false);

    field.readonly(true);

    equal(field.readonly(), true);
    equal(input.is('[readonly]'), true);
});

QUnit.parametrize('creme.form.Field (field-prop-change, readonly, init)', [
    [$('<input type="text" readonly/>'), {}, true, function(field) {
        return [];
    }],
    [$('<input type="text"/>'), {readonly: true}, true, function(field) {
        return [['field-prop-change', [field, 'readonly', true]]];
    }],
    [$('<input type="text"/>'), {}, false, function(field) {
        return [];
    }],
    [$('<input type="text" readonly/>'), {readonly: false}, false, function(field) {
        return [['field-prop-change', [field, 'readonly', false]]];
    }]
], function(input, options, expected, events, assert) {
    var field = new creme.form.Field(input.appendTo(this.qunitFixture()), options);

    equal(field.readonly(), expected, 'is readonly');
    equal(input.is('[readonly]'), expected);
    deepEqual(events(field), this.mockListenerJQueryCalls('field-prop-change'));
});

QUnit.parametrize('creme.form.Field (disabled)', [
    [$('<input type="text" disabled/>'), {}, true],
    [$('<input type="text"/>'), {disabled: true}, true],
    [$('<input type="text" disabled/>'), {disabled: false}, false],
    [$('<input type="text"/>'), {disabled: false}, false],
    [$('<input type="text"/>'), {}, false]
], function(input, options, expected, assert) {
    var field = new creme.form.Field(input.appendTo(this.qunitFixture()), options);

    equal(field.disabled(), expected, 'is disabled');
    equal(input.is('[disabled]'), expected);

    field.disabled(false);

    equal(field.disabled(), false);
    equal(input.is('[disabled]'), false);

    field.disabled(true);

    equal(field.disabled(), true);
    equal(input.is('[disabled]'), true);
});

QUnit.parametrize('creme.form.Field (field-prop-change, disabled, init)', [
    [$('<input type="text" disabled/>'), {}, true, function(field) {
        return [];
    }],
    [$('<input type="text"/>'), {disabled: true}, true, function(field) {
        return [['field-prop-change', [field, 'disabled', true]]];
    }],
    [$('<input type="text"/>'), {}, false, function(field) {
        return [];
    }],
    [$('<input type="text" disabled/>'), {disabled: false}, false, function(field) {
        return [['field-prop-change', [field, 'disabled', false]]];
    }]
], function(input, options, expected, events, assert) {
    var field = new creme.form.Field(input.appendTo(this.qunitFixture()), options);

    equal(field.disabled(), expected, 'is disabled');
    equal(input.is('[disabled]'), expected);
    deepEqual(events(field), this.mockListenerJQueryCalls('field-prop-change'));
});

QUnit.parametrize('creme.form.Field (required)', [
    [$('<input type="text" required/>'), {}, true],
    [$('<input type="text"/>'), {required: true}, true],
    [$('<input type="text" required/>'), {required: false}, false],
    [$('<input type="text"/>'), {required: false}, false],
    [$('<input type="text"/>'), {}, false]
], function(input, options, expected, assert) {
    var field = new creme.form.Field(input.appendTo(this.qunitFixture()), options);

    equal(field.required(), expected, 'is required');
    equal(input.is('[required]'), expected);

    field.required(false);

    equal(field.required(), false);
    equal(input.is('[required]'), false);

    field.required(true);

    equal(field.required(), true);
    equal(input.is('[required]'), true);
});

QUnit.parametrize('creme.form.Field (field-prop-change, required, init)', [
    [$('<input type="text" required/>'), {}, true, function(field) {
        return [];
    }],
    [$('<input type="text"/>'), {required: true}, true, function(field) {
        return [['field-prop-change', [field, 'required', true]]];
    }],
    [$('<input type="text"/>'), {}, false, function(field) {
        return [];
    }],
    [$('<input type="text" required/>'), {required: false}, false, function(field) {
        return [['field-prop-change', [field, 'required', false]]];
    }]
], function(input, options, expected, events, assert) {
    var field = new creme.form.Field(input.appendTo(this.qunitFixture()), options);

    equal(field.required(), expected, 'is required');
    equal(input.is('[required]'), expected);
    deepEqual(events(field), this.mockListenerJQueryCalls('field-prop-change'));
});

QUnit.parametrize('creme.form.Field (multiple)', [
    [$('<select multiple></select>'), {}, true],
    [$('<select></select>'), {multiple: true}, true],
    [$('<select multiple></select>'), {multiple: false}, false],
    [$('<select></select>'), {multiple: false}, false],
    [$('<select></select>'), {}, false]
], function(input, options, expected, assert) {
    var field = new creme.form.Field(input.appendTo(this.qunitFixture()), options);

    equal(field.multiple(), expected, 'is multiple');
    equal(input.is('[multiple]'), expected);

    field.multiple(false);

    equal(field.multiple(), false);
    equal(input.is('[multiple]'), false);

    field.multiple(true);

    equal(field.multiple(), true);
    equal(input.is('[multiple]'), true);
});

QUnit.parametrize('creme.form.Field (checked)', [
    [$('<input type="checkbox" checked/>'), {}, true],
    [$('<input type="checkbox"/>'), {checked: true}, true],
    [$('<input type="checkbox" checked/>'), {checked: false}, false],
    [$('<input type="checkbox"/>'), {checked: false}, false],
    [$('<input type="checkbox"/>'), {}, false]
], function(input, options, expected, assert) {
    var field = new creme.form.Field(input.appendTo(this.qunitFixture()), options);

    equal(field.checked(), expected, 'is checked');
    equal(input.prop('checked'), expected);

    field.checked(false);

    equal(field.checked(), false);
    equal(input.prop('checked'), false);

    field.checked(true);

    equal(field.checked(), true);
    equal(input.prop('checked'), true);
});

QUnit.parametrize('creme.form.Field (value)', [
    [$('<input type="text"/>'), ''],
    [$('<input type="text" value="a" />'), 'a'],
    [$('<input type="text" value="a" disabled/>'), 'a'],
    [$('<select>' +
           '<option value="">---</option>' +
           '<option value="a">A</option>' +
           '<option value="b" selected>B</option>' +
           '<option value="c">C</option>' +
       '</select>'), 'b']
], function(input, expected, assert) {
    var field = new creme.form.Field(input.appendTo(this.qunitFixture()));

    equal(field.value(), expected);
    deepEqual([], this.mockListenerJQueryCalls('field-change'));

    field.value(null);
    equal(field.value(), '');
    deepEqual([
        ['field-change', [field, '', expected]]
    ], this.mockListenerJQueryCalls('field-change'));

    field.value('c');
    equal(field.value(), 'c');
    deepEqual([
        ['field-change', [field, '', expected]],
        ['field-change', [field, 'c', '']]
    ], this.mockListenerJQueryCalls('field-change'));

    // nothing change, no event
    field.value('c');
    equal(field.value(), 'c');
    deepEqual([
        ['field-change', [field, '', expected]],
        ['field-change', [field, 'c', '']]
    ], this.mockListenerJQueryCalls('field-change'));
});

QUnit.test('creme.form.Field (value, multiple)', function(assert) {
    var input = $(
        '<select multiple>' +
            '<option value="">---</option>' +
            '<option value="a">A</option>' +
            '<option value="b" selected>B</option>' +
            '<option value="c" selected>C</option>' +
        '</select>');
    var field = new creme.form.Field(input.appendTo(this.qunitFixture()));

    equal(field.multiple(), true);
    deepEqual(field.value(), ['b', 'c']);
    deepEqual([], this.mockListenerJQueryCalls('field-change'));

    field.value(null);
    deepEqual(field.value(), null);
    deepEqual([
        ['field-change', [field, null, ['b', 'c']]]
    ], this.mockListenerJQueryCalls('field-change'));

    field.value(['a', 'c']);
    deepEqual(field.value(), ['a', 'c']);
    deepEqual([
        ['field-change', [field, null, ['b', 'c']]],
        ['field-change', [field, ['a', 'c'], null]]
    ], this.mockListenerJQueryCalls('field-change'));

    // nothing change, no event
    field.value(['a', 'c']);
    deepEqual(field.value(), ['a', 'c']);
    deepEqual([
        ['field-change', [field, null, ['b', 'c']]],
        ['field-change', [field, ['a', 'c'], null]]
    ], this.mockListenerJQueryCalls('field-change'));

    field.value('b');
    deepEqual(field.value(), ['b']);
    deepEqual([
        ['field-change', [field, null, ['b', 'c']]],
        ['field-change', [field, ['a', 'c'], null]],
        ['field-change', [field, ['b'], ['a', 'c']]]
    ], this.mockListenerJQueryCalls('field-change'));
});

QUnit.test('creme.form.Field (value, datatype=date)', function(assert) {
    var input = $('<input type="text" data-type="date" value="2018-11-01"/>');
    var field = new creme.form.Field(input.appendTo(this.qunitFixture()));

    equal(field.value(), '2018-11-01');
    deepEqual([], this.mockListenerJQueryCalls('field-change'));

    field.value(null);
    equal(field.value(), '');
    deepEqual([
        ['field-change', [field, '', '2018-11-01']]
    ], this.mockListenerJQueryCalls('field-change'));

    field.value(moment([2018, 10, 8]));
    equal(field.value(), '2018-11-08');
    deepEqual([
        ['field-change', [field, '', '2018-11-01']],
        ['field-change', [field, '2018-11-08', '']]
    ], this.mockListenerJQueryCalls('field-change'));

    // nothing change, no event
    field.value(moment([2018, 10, 8]));
    equal(field.value(), '2018-11-08');
    deepEqual([
        ['field-change', [field, '', '2018-11-01']],
        ['field-change', [field, '2018-11-08', '']]
    ], this.mockListenerJQueryCalls('field-change'));
});

QUnit.test('creme.form.Field (value, multiple, datatype=date)', function(assert) {
    var input = $(
        '<select multiple data-type="date">' +
            '<option value="">---</option>' +
            '<option value="2018-10-01">A</option>' +
            '<option value="2018-11-01" selected>B</option>' +
            '<option value="2018-12-01" selected>C</option>' +
        '</select>');
    var field = new creme.form.Field(input.appendTo(this.qunitFixture()));

    equal(field.multiple(), true);
    deepEqual(field.value(), ['2018-11-01', '2018-12-01']);
    deepEqual([], this.mockListenerJQueryCalls('field-change'));

    field.value([moment([2018, 9, 1])]);
    deepEqual(field.value(), ['2018-10-01']);
    deepEqual([
        ['field-change', [field, ['2018-10-01'], ['2018-11-01', '2018-12-01']]]
    ], this.mockListenerJQueryCalls('field-change'));

    field.value(null);
    deepEqual(field.value(), null);
    deepEqual([
        ['field-change', [field, ['2018-10-01'], ['2018-11-01', '2018-12-01']]],
        ['field-change', [field, null,  ['2018-10-01']]]
    ], this.mockListenerJQueryCalls('field-change'));

    field.value(['2018-12-01']);
    deepEqual(field.value(), ['2018-12-01']);
    deepEqual([
        ['field-change', [field, ['2018-10-01'], ['2018-11-01', '2018-12-01']]],
        ['field-change', [field, null,  ['2018-10-01']]],
        ['field-change', [field, ['2018-12-01'], null]]
    ], this.mockListenerJQueryCalls('field-change'));

    // nothing change, no event
    field.value([moment([2018, 11, 1])]);
    deepEqual(field.value(), ['2018-12-01']);
    deepEqual([
        ['field-change', [field, ['2018-10-01'], ['2018-11-01', '2018-12-01']]],
        ['field-change', [field, null,  ['2018-10-01']]],
        ['field-change', [field, ['2018-12-01'], null]]
    ], this.mockListenerJQueryCalls('field-change'));

    field.value(moment([2018, 10, 1]));
    deepEqual(field.value(), ['2018-11-01']);
    deepEqual([
        ['field-change', [field, ['2018-10-01'], ['2018-11-01', '2018-12-01']]],
        ['field-change', [field, null,  ['2018-10-01']]],
        ['field-change', [field, ['2018-12-01'], null]],
        ['field-change', [field, ['2018-11-01'], ['2018-12-01']]]
    ], this.mockListenerJQueryCalls('field-change'));
});

QUnit.parametrize('creme.form.Field (value, readonly)', [
    [$('<input type="text" value="a" readonly/>'), 'a'],
    [$('<select readonly>' +
           '<option value="">---</option>' +
           '<option value="a">A</option>' +
           '<option value="b" selected>B</option>' +
           '<option value="c">C</option>' +
       '</select>'), 'b']
], function(input, expected, assert) {
    var field = new creme.form.Field(input.appendTo(this.qunitFixture()));

    equal(field.value(), expected);
    deepEqual([], this.mockListenerJQueryCalls('field-change'));

    field.value(null);
    equal(field.value(), expected);

    deepEqual([], this.mockListenerJQueryCalls('field-change'));

    field.value('c');
    equal(field.value(), expected);

    deepEqual([], this.mockListenerJQueryCalls('field-change'));
});

QUnit.parametrize('creme.form.Field (reset)', [
    [$('<input type="text" value="a" />'), ''],
    [$('<input type="text" value="a" data-initial="initial" />'), 'initial'],
    [$('<select data-initial="initial">' +
           '<option value="">---</option>' +
           '<option value="a" selected>A</option>' +
           '<option value="b">B</option>' +
           '<option value="initial">C</option>' +
           '<option value="other">D</option>' +
       '</select>'), 'initial']
], function(input, expected, assert) {
    var field = new creme.form.Field(input.appendTo(this.qunitFixture()));

    equal(field.initial(), expected);
    equal(field.value(), 'a');
    deepEqual([], this.mockListenerJQueryCalls('field-reset'));
    deepEqual([], this.mockListenerJQueryCalls('field-change'));

    field.reset();

    equal(field.initial(), expected);
    equal(field.value(), expected);
    deepEqual([
        ['field-reset', [field, expected]]
    ], this.mockListenerJQueryCalls('field-reset'));
    deepEqual([
        ['field-change', [field, expected, 'a']]
    ], this.mockListenerJQueryCalls('field-change'));

    field.initial('other');

    equal(field.initial(), 'other');
    equal(field.value(), expected);

    field.reset();

    equal(field.initial(), 'other');
    equal(field.value(), 'other');
    deepEqual([
        ['field-reset', [field, expected]],
        ['field-reset', [field, 'other']]
    ], this.mockListenerJQueryCalls('field-reset'));
    deepEqual([
        ['field-change', [field, expected, 'a']],
        ['field-change', [field, 'other', expected]]
    ], this.mockListenerJQueryCalls('field-change'));

    // same value, no change event
    field.reset();

    equal(field.initial(), 'other');
    equal(field.value(), 'other');
    deepEqual([
        ['field-reset', [field, expected]],
        ['field-reset', [field, 'other']],
        ['field-reset', [field, 'other']]
    ], this.mockListenerJQueryCalls('field-reset'));
    deepEqual([
        ['field-change', [field, expected, 'a']],
        ['field-change', [field, 'other', expected]]
    ], this.mockListenerJQueryCalls('field-change'));
});

QUnit.parametrize('creme.form.Field (reset, readonly)', [
    [$('<input type="text" value="a" data-initial="initial" readonly/>'), 'a'],
    [$('<select data-initial="initial" readonly>' +
           '<option value="">---</option>' +
           '<option value="a">A</option>' +
           '<option value="b" selected>B</option>' +
           '<option value="initial">C</option>' +
       '</select>'), 'b']
], function(input, expected, assert) {
    var field = new creme.form.Field(input.appendTo(this.qunitFixture()));

    equal(field.initial(), 'initial');
    equal(field.value(), expected);
    deepEqual([], this.mockListenerJQueryCalls('field-reset'));
    deepEqual([], this.mockListenerJQueryCalls('field-change'));

    field.reset();

    equal(field.initial(), 'initial');
    equal(field.value(), expected);
    deepEqual([], this.mockListenerJQueryCalls('field-reset'));
    deepEqual([], this.mockListenerJQueryCalls('field-change'));
});

QUnit.parametrize('creme.form.Field (error)', [
    [$('<input type="text" value="a" />'), null, null],
    [$('<input type="text" value="a" />'), {code: null}, null],
    [$('<input type="text" value="a" />'), {}, null],
    [$('<input type="text" value="a" />'), {code: 'valueMissing'}, {
        code: 'valueMissing', message: gettext("This value is required")
    }],
    [$('<input type="text" value="a" />'), {code: 'valueMissing', message: 'Not here !'}, {
        code: 'valueMissing', message: 'Not here !'
    }]
], function(input, errorData, expected, assert) {
    var field = new creme.form.Field(input.appendTo(this.qunitFixture()));

    equal(null, field.error());
    equal(null, field.errorCode());
    equal('', field.errorMessage());

    field.error(errorData);

    if (expected !== null) {
        deepEqual(expected, field.error());
        equal(expected.code, field.errorCode());
        equal(expected.message, field.errorMessage());
    } else {
        equal(null, field.error());
        equal(null, field.errorCode());
        equal('', field.errorMessage());
    }
});

QUnit.parameterize('creme.form.Field (html5 validation)', [
    [$('<input type="text" value="" />'), true, undefined],
    [$('<input type="text" value="" required/>'), false, 'valueMissing'],
    [$('<input type="number" value="2" min="1" max="10" />'), true, undefined],
    [$('<input type="number" value="12" min="1" max="10" />'), false, 'rangeOverflow'],
    [$('<input type="number" value="2" min="5" max="10" />'), false, 'rangeUnderflow']
], function(input, isvalid, errorCode, assert) {
    var field = new creme.form.Field(input.appendTo(this.qunitFixture()));

    equal(field.isValidHtml(), isvalid);
    equal(field.htmlErrorCode(), errorCode);
    equal(input.is('.is-field-invalid'), false);

    if (errorCode) {
        deepEqual(field.error(), {
            code: errorCode,
            message: field.errorMessage()
        });
    } else {
        equal(field.error(), null);
    }

    // the class is set only AFTER manual html validation.
    field.validateHtml();

    equal(field.isValidHtml(), isvalid);
    equal(field.htmlErrorCode(), errorCode);

    deepEqual([
        ['field-error', [field, isvalid, field.error()]]
    ], this.mockListenerJQueryCalls('field-error'));
});

QUnit.parameterize('creme.form.Field (html5 validation, data-err-*)', [
    [$('<input type="text" value="" required/>'),
        'valueMissing',
        gettext("This value is required")
    ],
    [$('<input type="text" value="" required data-err-value-missing="Not here !"/>'),
        'valueMissing',
        'Not here !'
    ],
    [$('<input type="number" value="12" min="1" max="10"/>'),
        'rangeOverflow',
        gettext('This value must be inferior or equal to ${max}').template({max: 10})
    ],
    [$('<input type="number" value="2" min="5" max="10"/>'),
        'rangeUnderflow',
        gettext('This value must be superior or equal to ${min}').template({min: 5})
    ],
    [$('<input type="email" value="whatever"/>'),
        'typeMismatch',
        undefined
    ]
], function(input, errorCode, customMessage, assert) {
    var field = new creme.form.Field(input.appendTo(this.qunitFixture()));

    equal(field.isValidHtml(), false);
    equal(field.htmlErrorCode(), errorCode);

    var expectedMessage = customMessage || input.get(0).validationMessage;
    equal(field.errorMessage(), expectedMessage);

    if (errorCode) {
        deepEqual(field.error(), {
            code: errorCode,
            message: expectedMessage
        });
    } else {
        equal(field.error(), null);
    }
});

QUnit.parameterize('creme.form.Field (html5 validation, custom messages)', [
    [$('<input type="text" value="" required/>'),
        'valueMissing', 'Give it now !'
    ],
    [$('<input type="text" value="" required data-err-value-missing="Not here !"/>'),
        'valueMissing', 'Not here !'
    ],
    [$('<input type="number" value="12" min="1" max="10"/>'),
        'rangeOverflow',
        'Ok, ${value} is too much, <= ${max} please'.template({value: 12, max: 10})
    ],
    [$('<input type="number" value="2" min="5" max="10"/>'),
        'rangeUnderflow',
        gettext('This value must be superior or equal to ${min}').template({min: 5})
    ],
    [$('<input type="email" value="whatever"/>'),
        'typeMismatch',
        undefined
    ]
], function(input, errorKey, customMessage, assert) {
    var field = new creme.form.Field(input.appendTo(this.qunitFixture()), {
        errorMessages: {
            valueMissing: 'Give it now !',
            rangeOverflow: 'Ok, ${value} is too much, <= ${max} please'
        }
    });

    equal(field.isValidHtml(), false);
    equal(field.isValid(), false);
    equal(field.htmlErrorCode(), errorKey);

    var expectedMessage = customMessage || input.get(0).validationMessage;
    equal(field.errorMessage(), expectedMessage);
});

QUnit.parametrize('creme.form.Field (clean)', [
    [$('<input type="text" value="a"/>'), 'a', 'a'],
    [$('<input type="text"/>'), '', ''],

    [$('<input type="text" value="12" data-type="number"/>'), '12', 12],
    [$('<input type="text" data-type="number"/>'), '', undefined],

    [$('<input type="number" value="12"/>'), '12', 12],
    [$('<input type="number" value="12.5" data-type="int"/>'), '12.5', 12],
    [$('<input type="number" value="12.5"/>'), '12.5', 12.5],

    [$('<input type="date" value="2019-12-12" data-type="text"/>'), '2019-12-12', '2019-12-12'],
    [$('<input type="date" data-type="text"/>'), '', '']
], function(input, value, expected, assert) {
    var field = new creme.form.Field(input.appendTo(this.qunitFixture()));

    equal(field.isValidHtml(), true);
    equal(field.value(), value);
    equal(field.clean(), expected);
});

QUnit.parametrize('creme.form.Field (clean, datatype=date|datetime)', [
    [$('<input type="text" value="2019-12-12" data-type="date"/>'),
        '2019-12-12', moment([2019, 11, 12])
    ],
    [$('<input type="date" value="2019-12-12"/>'),
        '2019-12-12', moment([2019, 11, 12])
    ],
    [$('<input type="date"/>'), '', undefined],
    [$('<input type="text" value="2019-12-12T08:10:38" data-type="datetime"/>'),
        '2019-12-12T08:10:38', moment([2019, 11, 12, 8, 10, 38])
    ],
    [$('<input type="datetime" value="2019-12-12T08:10:38"/>'),
        '2019-12-12T08:10:38', moment([2019, 11, 12, 8, 10, 38])
    ],
    [$('<input type="datetime"/>'), '', undefined],
    [$('<input type="datetime-local" value="2019-12-12T08:10:38"/>'),
        '2019-12-12T08:10:38', moment([2019, 11, 12, 8, 10, 38])
    ],
    [$('<input type="datetime-local"/>'), '', undefined]
], function(input, value, expected, assert) {
    var field = new creme.form.Field(input.appendTo(this.qunitFixture()));

    equal(field.isValidHtml(), true);
    equal(field.value(), value);

    var cleaned = field.clean();

    equal((cleaned instanceof moment) ? cleaned.format() : cleaned,
          (expected instanceof moment) ? expected.format() : expected);
});

QUnit.parametrize('creme.form.Field (clean, datatype=json)', [
    [$('<input type="text" value="12" data-type="json"/>'), '12', 12],
    [$('<input type="text" value="{&quot;a&quot;:12,&quot;b&quot;:5}" data-type="json"/>'),
        "{\"a\":12,\"b\":5}", {a: 12, b: 5}
    ],
    [$('<input type="text" value="[1,2,3]" data-type="json"/>'),
        "[1,2,3]", [1, 2, 3]
    ],
    [$('<select data-type="json">' +
            '<option value="[1,2]">A</option>' +
            '<option value="[1,4,2]" selected>B</option>' +
            '<option value="{&quot;a&quot;:1}">C</option>' +
       '</select>'),
        '[1,4,2]', [1, 4, 2]
    ]
], function(input, value, expected, assert) {
    var field = new creme.form.Field(input.appendTo(this.qunitFixture()));

    equal(field.isValidHtml(), true);
    equal(field.isValid(), true);
    equal(field.value(), value);

    deepEqual(field.clean(), expected);
});

QUnit.parametrize('creme.form.Field (clean, invalid)', [
    [$('<input name="field-A" type="text" required/>'),
        false, 'valueMissing', '"field-A" is required !'
    ],
    // WTF : invalid value="notadate" means "" for the browser
    [$('<input name="field-A" type="date" value="notadate" required/>'),
        false, 'valueMissing', '"field-A" is required !'
    ],
    // If we use the custom data-type, no pb
    [$('<input name="field-A" type="text" data-type="date" value="notadate"/>'),
        true, 'cleanMismatch', gettext('This value is not a valid "${dataType}"').template({dataType: 'date'})
    ],
    // Same for number
    [$('<input name="field-A" type="text" data-type="number" value="NaN"/>'),
        true, 'cleanMismatch', gettext('This value is not a valid "${dataType}"').template({dataType: 'number'})
    ],
    [$('<input name="field-A" type="number" value="NaN" required/>'),
        false, 'valueMissing', '"field-A" is required !'
    ],
    [$('<input name="field-A" type="number" value="3" min="5"/>'),
        false, 'rangeUnderflow', gettext('This value must be superior or equal to ${min}').template({min: 5})
    ],
    [$('<input name="field-A" type="text" value="12:a" data-type="json"/>'),
        true, 'cleanMismatch', gettext('This value is not a valid "${dataType}"').template({dataType: 'json'})
    ],
    [$('<input name="field-A" type="text" value="12:a" data-type="json" data-err-clean-mismatch="Invalid JSON"/>'),
        true, 'cleanMismatch', 'Invalid JSON'
    ]
], function(input, isValidHtml, code, message, assert) {
    var field = new creme.form.Field(input.appendTo(this.qunitFixture()), {
        errorMessages: {
            valueMissing: '"${name}" is required !'
        }
    });

    equal(field.isValidHtml(), isValidHtml);
    equal(field.isValid(), isValidHtml);

    this.resetMockListenerCalls();

    this.assertRaises(function() {
        field.clean();
    }, Error, 'Error: ${expected}'.template({expected: message}));

    equal(field.isValidHtml(), false);
    equal(field.isValid(), false);
    equal(field.errorCode(), code);
    equal(field.errorMessage(), message);

    // When html validity is check and returns "ok", the errorCode is reset to null
    // and a field-error event is triggered
    if (isValidHtml) {
        deepEqual([
            ['field-error', [field, true, null]],
            ['field-error', [field, false, field.error()]]
        ], this.mockListenerJQueryCalls('field-error'));
    } else {
        deepEqual([
            ['field-error', [field, false, field.error()]]
        ], this.mockListenerJQueryCalls('field-error'));
    }
});

QUnit.test('creme.form.Field (clean, invalid, noThrow)', function(assert) {
    var input = $('<input name="field-A" type="text" required/>');
    var field = new creme.form.Field(input.appendTo(this.qunitFixture()), {
        errorMessages: {
            valueMissing: '"${name}" is required !'
        }
    });

    equal(field.isValidHtml(), false);
    equal(field.isValid(), false);

    equal(undefined, field.clean({noThrow: true}));

    equal(field.isValidHtml(), false);
    equal('valueMissing', field.errorCode());
    equal('"field-A" is required !', field.errorMessage());
});

QUnit.parametrize('creme.form.Field (preventBrowserTooltip)', [
    [$('<input name="A" required/>'), {}, false],
    [$('<input data-notooltip name="A" required/>'), {}, true],
    [$('<input name="A" required/>'), {preventBrowserTooltip: true}, true],
    [$('<input data-notooltip name="A" required/>'), {preventBrowserTooltip: false}, false]
], function(element, options, expected, assert) {
    var field = new creme.form.Field(element, options);
    equal(field.preventBrowserTooltip(), expected);
    equal(element.is('[data-notooltip]'), expected);

    // check if the "invalid" is prevented
    element.on('invalid', this.mockListener('invalid-html'));

    equal(false, field.validateHtml());

    var calls = this.mockListenerCalls('invalid-html');
    equal(1, calls.length);
    equal(expected, calls[0][0].isDefaultPrevented());
});

QUnit.parametrize('creme.form.Field (preventBrowserTooltip, form)', [
    [$('<form><input name="A" /></form>'), {}, false],
    [$('<form data-notooltip><input name="A" /></form>'), {}, true],
    [$('<form><input name="A" data-notooltip/></form>'), {}, true],

    [$('<form><input name="A" /></form>'), {preventBrowserTooltip: true}, true],
    [$('<form data-notooltip><input name="A" /></form>'), {preventBrowserTooltip: false}, true]
], function(element, options, expected, assert) {
    var field = new creme.form.Field(element.find('input'), options);
    equal(field.preventBrowserTooltip(), expected);
});

QUnit.parametrize('creme.form.Field (responsive)', [
    [$('<input name="A" />'), {}, false],
    [$('<input data-responsive name="A" />'), {}, true],
    [$('<input name="A" />'), {responsive: true}, true],
    [$('<input data-responsive name="A" />'), {responsive: false}, false]
], function(element, options, expected, assert) {
    var field = new creme.form.Field(element, options);
    equal(field.responsive(), expected);
    equal(element.is('[data-responsive]'), expected);
});

QUnit.parametrize('creme.form.Field (responsive, form)', [
    [$('<form><input name="A" /></form>'), {}, false],
    [$('<form data-responsive><input name="A" /></form>'), {}, true],
    [$('<form><input name="A" data-responsive/></form>'), {}, true],

    [$('<form><input name="A" /></form>'), {responsive: true}, true],
    [$('<form data-responsive><input name="A" /></form>'), {responsive: false}, true]
], function(element, options, expected, assert) {
    var field = new creme.form.Field(element.find('input'), options);
    equal(field.responsive(), expected);
});

QUnit.test('flyfield (empty, defaults)', function() {
    var element = $('<input name="A">');

    var field = element.flyfield({
        responsive: true
    });

    ok(field instanceof creme.form.Field);
    deepEqual(field, element.flyfield('instance'));

    equal(true, element.flyfield('prop', 'isValid'));
    equal(true, element.flyfield('prop', 'isValidHtml'));
    equal(false, element.flyfield('prop', 'disabled'));
    equal(false, element.flyfield('prop', 'readonly'));
    equal(false, element.flyfield('prop', 'multiple'));
    equal(false, element.flyfield('prop', 'checked'));
    equal(true, element.flyfield('prop', 'responsive'));
    equal(false, element.flyfield('prop', 'preventBrowserTooltip'));

    equal("A", element.flyfield('prop', 'name'));
    equal('text', element.flyfield('prop', 'dataType'));
    equal('text', element.flyfield('prop', 'htmlType'));
    equal('', element.flyfield('prop', 'initial'));

    equal(null, element.flyfield('prop', 'errorCode'));
    equal('', element.flyfield('prop', 'errorMessage'));

    equal(true, element.flyfield('validateHtml'));
    equal('', element.flyfield('value'));
    equal('', element.flyfield('clean'));

    deepEqual(field, element.flyfield('reset'));
});

}(jQuery));
