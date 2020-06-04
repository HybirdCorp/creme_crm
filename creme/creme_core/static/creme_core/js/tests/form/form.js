/* global QUnitFormMixin FunctionFaker */
(function($) {

QUnit.module("creme.form.Form", new QUnitMixin(QUnitEventMixin,
                                               QUnitAjaxMixin,
                                               QUnitFormMixin, {
    beforeEach: function() {
        var backend = this.backend;
        this.setMockBackendGET({
            'mock/submit': backend.response(200, ''),
            'mock/other': backend.response(200, '')
        });

        this.setMockBackendPOST({
            'mock/submit': backend.response(200, ''),
            'mock/other': backend.response(200, '')
        });
    }
}));

QUnit.test('creme.form.Form (empty, defaults)', function() {
    var element = $('<form action="mock/submit">');
    var form = new creme.form.Form(element);

    equal(true, form.isValid());
    equal(true, form.isValidHtml());

    deepEqual([], form.fields());
    deepEqual({}, form.initialData());
    deepEqual({}, form.data());
    deepEqual({
        cleanedData: {},
        data: {},
        fieldErrors: {},
        isValid: true
    }, form.clean());

    this.equalOuterHtml(element, form.element());
});

QUnit.parametrize('creme.form.Form (init, invalid element)', [
    [undefined, 'DOM element "undefined" is not a string nor a jQuery element'],
    [12, 'DOM element "12" is not a string nor a jQuery element'],
    [$('#unknown'), 'A single DOM element is required'],
    [$(['<input/>', '<input/>']), 'A single DOM element is required']
], function(element, message, assert) {
    this.assertRaises(function() {
        return new creme.form.Form(element);
    }, Error, 'Error: ${message}'.template({message: message}));
});

QUnit.test('creme.form.Form (validator)', function(options, message, assert) {
    this.assertRaises(function() {
        return new creme.form.Form($('<form action="mock/submit">'), {validator: 'notamethod'});
    }, Error, 'Error: Validator must be a function');

    var form = new creme.form.Form($('<form action="mock/submit">'));
    this.assertRaises(function() {
        form.validator('notamethod');
    }, Error, 'Error: Validator must be a function');

    var validator = function() {};
    form.validator(validator);
    equal(validator, form.validator());
});

QUnit.parametrize('creme.form.Form (fields)', [
    [$('<form><input name="field_a" type="text" value="a"></form>'), ['field_a']],
    [$('<form><select name="field_a">' +
            '<option value="a">A</option>' +
            '<option value="b" selected>B</option>' +
            '<option value="c">C</option>' +
       '</select></form>'), ['field_a']],
    [$('<form>' +
            '<input name="field_a" type="text" value="a">' +
            '<input name="field_b" type="text" value="a">' +
       '</form>'), ['field_a', 'field_b']],
    [$('<form>' +
            '<input name="" type="text" value="a">' +
            '<input type="text" value="a">' +
            '<input name="field_b" type="text" value="a">' +
       '</form>'), ['field_b']],
    [$('<form>' +
            '<input type="checkbox" name="field_a" value="a" checked>A</input>' +
            '<input type="checkbox" name="field_a" value="b">B</option>' +
            '<input type="checkbox" name="field_a" value="c" checked>C</option>' +
       '</form>'), ['field_a', 'field_a', 'field_a']]
], function(element, expected, assert) {
    var form = new creme.form.Form(element);
    deepEqual(expected, form.fields().map(function(field) {
        return field.name();
    }));
});

QUnit.parametrize('creme.form.Form (field)', [
    [$('<form><input name="field_a" type="text" value="a"></form>'), 'a'],
    [$('<form>' +
            '<input type="checkbox" name="field_a" value="a" checked>A</input>' +
            '<input type="checkbox" name="field_a" value="b">B</option>' +
            '<input type="checkbox" name="field_a" value="c" checked>C</option>' +
       '</form>'), 'a']
], function(element, expected, assert) {
    var form = new creme.form.Form(element);
    var field = form.field('field_a');

    equal(field.value(), expected);
});

QUnit.parametrize('creme.form.Form (data)', [
    [$('<form><input name="field_a" type="text" value="a"></form>'), {field_a: 'a'}],
    [$('<form><select name="field_a">' +
            '<option value="a">A</option>' +
            '<option value="b" selected>B</option>' +
            '<option value="c">C</option>' +
       '</select></form>'), {field_a: 'b'}],
    [$('<form><select name="field_a" multiple>' +
            '<option value="a">A</option>' +
            '<option value="b" selected>B</option>' +
            '<option value="c" selected>C</option>' +
       '</select></form>'), {field_a: ['b', 'c']}],
    [$('<form>' +
            '<input type="checkbox" name="field_a" value="a" checked>A</input>' +
            '<input type="checkbox" name="field_a" value="b">B</option>' +
            '<input type="checkbox" name="field_a" value="c" checked>C</option>' +
       '</form>'), {field_a: ['a', 'c']}]
], function(element, expected, assert) {
    var form = new creme.form.Form(element);
    deepEqual(expected, form.data());
});

QUnit.parametrize('creme.form.Form (data, ignore empty names)', [
    [$('<form><input type="text" value="a"></form>'), {}],
    [$('<form>' +
            '<input type="text" value="a">' +
            '<input name="field_b" type="text" value="b">' +
       '</form>'), {field_b: 'b'}],
    [$('<form><select><option value="a">A</option></select></form>'), {}],
    [$('<form>' +
            '<input type="checkbox" value="a" checked>A</input>' +
            '<input type="checkbox" value="b">B</option>' +
            '<input type="checkbox" value="c" checked>C</option>' +
       '</form>'), {}]
], function(element, expected, assert) {
    var form = new creme.form.Form(element);
    deepEqual(expected, form.data());
});

QUnit.parametrize('creme.form.Form (data, setter)', [
    [{date_a: moment([2018, 11, 8]), int_b: 1778, test_c: 'a test'},
     {date_a: '2018-12-08', int_b: '1778', test_c: 'a test'}],
    [{date_a: moment([2018, 11, 8]), int_b: 1778, test_c: 'a test', unknown_c: 'unknown'},
     {date_a: '2018-12-08', int_b: '1778', test_c: 'a test'}],
    [{test_c: 'a test'},
     {date_a: '2019-05-18', int_b: '5', test_c: 'a test'}],
    [{date_a: moment([2018, 11, 8]), int_b: '1778', test_c: 'a too long test'},
     {date_a: '2018-12-08', int_b: '1778', test_c: 'a too long test'}]
], function(data, expected, assert) {
    var form = new creme.form.Form($(
        '<form>' +
            '<input type="date" name="date_a" value="2019-05-18"/>' +
            '<input type="number" name="int_b" value="5"/>' +
            '<input type="text" name="test_c" maxlength="6"/>' +
        '</form>'
    ));

    deepEqual(form.data(data).data(), expected);
});

QUnit.parametrize('creme.form.Form (initialData)', [
    [$('<form><input type="text" value="a"></form>'), {}],
    [$('<form><input type="text" value="a" data-initial="b"></form>'), {}],
    [$('<form><input type="text" name="field_a" value="a" data-initial="b"></form>'), {field_a: 'b'}],
    [$('<form><select name="field_a" data-initial="c">' +
            '<option value="a">A</option>' +
            '<option value="b" selected>B</option>' +
            '<option value="c">C</option>' +
       '</select></form>'), {field_a: 'c'}],
    [$('<form><select name="field_a" multiple data-initial="b,c">' +
            '<option value="a">A</option>' +
            '<option value="b" selected>B</option>' +
            '<option value="c" selected>C</option>' +
       '</select></form>'), {field_a: ['b', 'c']}],
    [$('<form>' +
            '<input type="checkbox" name="field_a" value="a" checked data-initial="1">A</input>' +
            '<input type="checkbox" name="field_a" value="b" data-initial="2">B</option>' +
            '<input type="checkbox" name="field_a" value="c" checked data-initial="3">C</option>' +
       '</form>'), {field_a: [1, 2, 3]}]
], function(element, expected, assert) {
    var form = new creme.form.Form(element);
    deepEqual(form.initialData(), expected);
});

QUnit.parametrize('creme.form.Form (initialData, setter)', [
    [{date_a: moment([2018, 11, 8]), int_b: 1778, test_c: 'a test'},
     {date_a: moment([2018, 11, 8]), int_b: 1778, test_c: 'a test'}],
    [{date_a: moment([2018, 11, 8]), int_b: 1778, test_c: 'a test', unknown_c: 'unknown'},
     {date_a: moment([2018, 11, 8]), int_b: 1778, test_c: 'a test'}],
    [{test_c: 'a test'},
     {date_a: '2017-01-01', int_b: '', test_c: 'a test'}]
], function(data, expected, assert) {
    var form = new creme.form.Form($(
        '<form>' +
            '<input type="date" name="date_a" value="2019-05-18" data-initial="2017-01-01"/>' +
            '<input type="number" name="int_b" value="5"/>' +
            '<input type="text" name="test_c" maxlength="6"/>' +
        '</form>'
    ));

    deepEqual(form.initialData(data).initialData(), expected);
});

QUnit.test('creme.form.Form (reset)', function(element, expected, assert) {
    var form = new creme.form.Form($(
        '<form>' +
            '<input type="date" name="date_a" value="2019-05-18" data-initial="2017-01-01"/>' +
            '<input type="number" name="int_b" value="12" data-initial="5"/>' +
            '<input type="text" name="test_c" maxlength="6" data-initial="a test"/>' +
        '</form>'
    ));

    deepEqual(form.data(), {
        date_a: '2019-05-18',
        int_b: '12',
        test_c: ''
    });

    form.reset();

    deepEqual(form.data(), {
        date_a: '2017-01-01',
        int_b: '5',
        test_c: 'a test'
    });
});

QUnit.parametrize('creme.form.Form (isValidHtml)', [
    [$('<form><input name="a" type="number" required></form>'), {}, false],
    [$('<form><input name="a" type="number" required></form>'), {noValidate: true}, true],
    [$('<form novalidate><input name="a" type="number" required></form>'), {}, true]
], function(element, options, expected, assert) {
    var form = new creme.form.Form(element, options);
    equal(form.validateHtml(), expected);
});

QUnit.parametrize('creme.form.Form (clean)', [
    [$('<form><input name="field_a" type="number" value="12"></form>'), {
        cleanedData: {field_a: 12},
        data: {field_a: '12'},
        isValid: true,
        fieldErrors: {}
    }],
    [$('<form><input name="field_a" type="text" data-type="json" value="{&quot;a&quot;:12}"></form>'), {
        cleanedData: {field_a: {a: 12}},
        data: {field_a: '{\"a\":12}'},
        isValid: true,
        fieldErrors: {}
    }]
], function(element, expected, assert) {
    var form = new creme.form.Form(element);
    deepEqual(expected, form.clean());
    equal(form.isValidHtml(), true);
});

QUnit.parametrize('creme.form.Form (clean, datatype=date|datetime)', [
    [$('<form><input name="field_a" type="date" value="2018-12-08"></form>'), {
        cleanedData: {field_a: moment([2018, 11, 8])},
        data: {field_a: '2018-12-08'},
        isValid: true,
        fieldErrors: {}
    }],
    [$('<form><input name="field_a" type="datetime" value="2018-12-08T08:15:32"></form>'), {
        cleanedData: {field_a: moment([2018, 11, 8, 8, 15, 32])},
        data: {field_a: '2018-12-08T08:15:32'},
        isValid: true,
        fieldErrors: {}
    }]
], function(element, expected, assert) {
    var form = new creme.form.Form(element);
    var output = form.clean();

    deepEqual(expected.data, output.data);
    deepEqual(expected.errors, output.errors);
    deepEqual(expected.cleanedData.field_a.format(), output.cleanedData.field_a.format());

    equal(form.isValidHtml(), true);
});

QUnit.parametrize('creme.form.Form (clean, html5 errors)', [
    [$('<form><input name="field_a" type="number" required></form>'), {
        cleanedData: {},
        data: {field_a: ''},
        isValid: false,
        fieldErrors: {
            field_a: {
                code: 'valueMissing',
                message: gettext('This value is required')
            }
        }
    }],
    [$('<form><input name="field_a" type="number" value="notnumber"></form>'), {
        cleanedData: {},
        data: {field_a: ''},
        isValid: false,
        fieldErrors: {
            field_a: {
                code: 'cleanMismatch',
                message: gettext('This value is not a valid "number"')
            }
        }
    }]
], function(element, expected, assert) {
    var form = new creme.form.Form(element);
    deepEqual(expected, form.clean({noThrow: true}));
    equal(form.isValidHtml(), false);

    var error = this.assertRaises(function() {
        form.clean();
    }, Error, 'Error: Form data is invalid');

    deepEqual(expected, error.output);
});

QUnit.parametrize('creme.form.Form (clean, html5 errors, custom messages)', [
    [$('<form><input name="field_a" type="number" required></form>'), {
        cleanedData: {},
        data: {field_a: ''},
        isValid: false,
        fieldErrors: {
            field_a: {
                code: 'valueMissing',
                message: 'Not here !'
            }
        }
    }],
    [$('<form><input name="field_a" type="number" value="notnumber" data-err-clean-mismatch="Not a number"></form>'), {
        cleanedData: {},
        data: {field_a: ''},
        isValid: false,
        fieldErrors: {
            field_a: {
                code: 'cleanMismatch',
                message: 'Not a number'
            }
        }
    }]
], function(element, expected, assert) {
    var form = new creme.form.Form(element, {
        errorMessages: {
            valueMissing: 'Not here !',
            badValue: 'Wrong value'
        }
    });

    deepEqual(expected, form.clean({noThrow: true}));
    equal(form.isValidHtml(), false);
});

QUnit.parametrize('creme.form.Form (clean, novalidate)', [
   [$('<form><input name="a" required /></form>'), {}, false, false],
   [$('<form novalidate><input name="a" required /></form>'), {}, true, true],
   [$('<form><input name="a" required /></form>'), {noValidate: true}, true, true],
   [$('<form novalidate><input name="a" required /></form>'), {noValidate: false}, false, false]
], function(element, options, expected, isValid, assert) {
    var form = new creme.form.Form(element, options);

    equal(form.noValidate(), expected);
    equal(element.is('[novalidate]'), expected);
    equal(element.get(0).noValidate, expected);
});

QUnit.parametrize('creme.form.Form (clean, validators)', [
    [{}, {
        cleanedData: {},
        data: {a: '', clone: ''},
        isValid: false,
        fieldErrors: {
            a: {code: 'valueMissing', message: 'Not here !'},
            clone: {code: 'valueMissing', message: 'Not here !'}
        },
        formError: 'One or both of the fields are empty'
    }],
    [{a: 'a'}, {
        cleanedData: {a: 'a'},
        data: {a: 'a', clone: ''},
        isValid: false,
        fieldErrors: {
            clone: {code: 'valueMissing', message: 'Not here !'}
        },
        formError: 'One or both of the fields are empty'
    }],
    [{a: 'a', clone: 'b'}, {
        cleanedData: {a: 'a', clone: 'b'},
        data: {a: 'a', clone: 'b'},
        isValid: false,
        fieldErrors: {},
        formError: "The fields aren't the same !"
    }],
    [{a: 'a', clone: 'a'}, {
        cleanedData: {a: 'a', clone: 'a'},
        data: {a: 'a', clone: 'a'},
        isValid: true,
        fieldErrors: {}
    }]
], function(data, expected, assert) {
    var form = new creme.form.Form($(
        '<form>' +
            '<input name="a" required>' +
            '<input name="clone" required>' +
        '</form>'
    ), {errorMessages: {valueMissing: 'Not here !'}});

    form.validator(function(data) {
        if (data.isValid) {
            Assert.that(data.cleanedData['a'] === data.cleanedData['clone'],
                        "The fields aren't the same !");
        } else {
            throw new Error('One or both of the fields are empty');
        }
    });

    deepEqual(expected, form.data(data).clean({noThrow: true}));
});

QUnit.parametrize('creme.form.Form (preventBrowserTooltip)', [
    [$('<form></form>'), {}, false],
    [$('<form data-notooltip></form>'), {}, true],
    [$('<form></form>'), {preventBrowserTooltip: true}, true],
    [$('<form data-notooltip></form>'), {preventBrowserTooltip: false}, false]
], function(element, options, expected, assert) {
    var form = new creme.form.Form(element, options);
    equal(form.preventBrowserTooltip(), expected);
});

QUnit.parametrize('creme.form.Form (submit)', [
    [$('<form action="mock/submit"><input name="a" value="1" /></form>'), {}, {a: '1'}],
    [$('<form action="mock/submit" novalidate><input name="a" required /></form>'), {}, {a: ''}],
    [$('<form action="mock/submit"><input name="a" required /></form>'), {noValidate: true}, {a: ''}],
    [$('<form action="mock/submit"><input name="a" value="1" required /></form>'), {}, {a: '1'}]
], function(element, options, expected, assert) {
    var form = new creme.form.Form(element.appendTo(this.qunitFixture()), options);

    equal(false, form.isSubmitting());

    form.submit();

    equal(true, form.isValidHtml());
    equal(true, form.isValid());
    equal(true, form.isSubmitting());

    deepEqual(['mock/submit'], this.mockFormSubmitCalls());
});

QUnit.parametrize('creme.form.Form (submit, html5 errors)', [
    [$('<form action="mock/submit"><input name="a" required /></form>'), {}, {}],
    [$('<form action="mock/submit"><input name="a" type="number" required value="NaN"/></form>'), {}, {}]
], function(element, options, expected, assert) {
    var form = new creme.form.Form(element.appendTo(this.qunitFixture()), options);

    equal(false, form.isSubmitting());

    form.submit();

    equal(false, form.isValidHtml());
    ok(form.isValid() === false);
    ok(form.isSubmitting() === false);

    deepEqual(['mock/submit'], this.mockFormSubmitCalls());
});

QUnit.parametrize('creme.form.Form (submit, convertion errors)', [
    [$('<form action="mock/submit"><input name="a" data-type="number" value="NaN"/></form>'), {}, {}],
    [$('<form action="mock/submit"><input name="a" data-type="datetime" required value="NaN"/></form>'), {}, {}]
], function(element, options, expected, assert) {
    var form = new creme.form.Form(element.appendTo(this.qunitFixture()), options);

    equal(false, form.isSubmitting());

    form.submit();

    equal(false, form.isValidHtml());
    ok(form.isValid() === false);
    ok(form.isSubmitting() === false);

    deepEqual(['mock/submit'], this.mockFormSubmitCalls());
});

QUnit.parametrize('creme.form.Form (submit, scrollOnError)', [
    [$('<form action="mock/submit"><input name="a" data-type="number" value="NaN"/></form>'), {}, 0],
    [$('<form action="mock/submit"><input name="a" data-type="number" value="NaN"/></form>'), {scrollOnError: true}, 1],
    [$('<form action="mock/submit"><input name="a" data-type="datetime" required/></form>'), {}, 0],
    [$('<form action="mock/submit"><input name="a" data-type="datetime" required/></form>'), {scrollOnError: true}, 1]
], function(element, options, expected, assert) {
    var form = new creme.form.Form(element.appendTo(this.qunitFixture()), options);
    var scrollToFaker = new FunctionFaker({
        instance: form,
        method: 'scrollToInvalidField',
        follow: true
    });

    equal(false, form.isSubmitting());
    equal(0, scrollToFaker.count());

    scrollToFaker.with(function() {
        form.submit();
    });

    equal(false, form.isValidHtml());
    ok(form.isValid() === false);
    ok(form.isSubmitting() === false);
    equal(expected, scrollToFaker.count());

    deepEqual(['mock/submit'], this.mockFormSubmitCalls());
});

QUnit.parametrize('creme.form.Form (ajaxQuery)', [
    'GET', 'POST'
], {
    simple: [
        $('<form action="mock/submit"><input name="a" value="1" /></form>'), {}, {},
        'mock/submit', {a: '1'}
    ],
    simple_required: [
        $('<form action="mock/submit"><input name="a" value="1" required /></form>'), {}, {},
        'mock/submit', {a: '1'}
    ],
    replace_empty_url: [
        $('<form><input name="a" value="1" /></form>'), {url: 'mock/other'}, {},
        'mock/other', {a: '1'}
    ],
    replace_url: [
        $('<form action="mock/submit"><input name="a" value="1" /></form>'), {url: 'mock/other'}, {b: 12},
        'mock/other', {a: '1', b: 12}
    ],
    cleaned_data_override_extra: [
        $('<form action="mock/submit"><input name="a" value="1" /></form>'), {}, {a: 5},
        'mock/submit', {a: '1'}
    ],
    form_novalidate: [
        $('<form action="mock/submit" novalidate><input name="a" required /></form>'), {}, {},
        'mock/submit', {}
    ],
    form_novalidate_extra_data_as_default: [
        $('<form action="mock/submit" novalidate><input name="a" required /></form>'), {}, {a: 5},
        'mock/submit', {a: 5}
    ],
    option_novalidate: [
        $('<form action="mock/submit"><input name="a" required /></form>'), {noValidate: true}, {},
        'mock/submit', {}
    ]
}, function(method, element, options, data, expected_url, expected, assert) {
    var form = new creme.form.Form(element.appendTo(this.qunitFixture()), options);

    equal(false, form.isSubmitting(), 'form is not submitting');
    deepEqual([], this.mockFormSubmitCalls());
    deepEqual([], this.mockBackendUrlCalls(expected_url));

    var query = form.ajaxQuery(data, options);

    equal(false, form.isSubmitting());
    deepEqual([], this.mockFormSubmitCalls());
    deepEqual([], this.mockBackendUrlCalls(expected_url));

    query.start({action: method});

    equal(true, form.isValidHtml());
    equal(true, form.isValid());
    equal(false, form.isSubmitting());

    deepEqual([], this.mockFormSubmitCalls());
    deepEqual([
        [method, expected]
    ], this.mockBackendUrlCalls(expected_url));
});

QUnit.parametrize('creme.form.Form (ajaxSubmit)', [
    [$('<form action="mock/submit"><input name="a" value="1" /></form>'), {}, {a: '1'}],
    [$('<form action="mock/submit" novalidate><input name="a" required /></form>'), {}, {}],
    [$('<form action="mock/submit"><input name="a" required /></form>'), {noValidate: true}, {}],
    [$('<form action="mock/submit"><input name="a" value="1" required /></form>'), {}, {a: '1'}]
], function(element, options, expected, assert) {
    var form = new creme.form.Form(element.appendTo(this.qunitFixture()), options);

    equal(false, form.isSubmitting(), 'form is not submitting');
    deepEqual([], this.mockFormSubmitCalls());
    deepEqual([], this.mockBackendUrlCalls('mock/submit'));
    equal('mock/submit', form.url());

    form.ajaxSubmit();

    equal(true, form.isValidHtml());
    equal(true, form.isValid());
    equal(false, form.isSubmitting());

    deepEqual([], this.mockFormSubmitCalls());
    deepEqual([
        ['POST', expected]
    ], this.mockBackendUrlCalls('mock/submit'));
});

QUnit.parametrize('creme.form.Form (submit button)', [
    [$('<form action="mock/submit"><input name="a" value="1" /><button type="submit"></form>'), {}, {
        cleanedData: {a: '1'},
        data: {a: '1'},
        isValid: true,
        fieldErrors: {}
    }],
    [$('<form action="mock/submit"><input name="a" value="1" required/><button type="submit"></form>'), {}, {
        cleanedData: {a: '1'},
        data: {a: '1'},
        isValid: true,
        fieldErrors: {}
    }],

    [$('<form action="mock/submit" novalidate><input name="a" required/><button type="submit"></form>'), {}, {
        cleanedData: {},
        data: {a: ''},
        isValid: true,
        fieldErrors: {}
    }],
    [$('<form action="mock/submit"><input name="a" required/><button type="submit"></form>'), {noValidate: true}, {
        cleanedData: {},
        data: {a: ''},
        isValid: true,
        fieldErrors: {}
    }],
    [$('<form action="mock/submit"><input name="a" required/><button type="submit" data-novalidate></form>'), {}, {
        cleanedData: {},
        data: {a: ''},
        isValid: true,
        fieldErrors: {}
    }]
], function(element, options, expected) {
    var form = new creme.form.Form(element.appendTo(this.qunitFixture()), options);
    form.on('form-submit', this.mockListener('form-submit'));

    equal(false, form.isSubmitting(), 'form is not submitting');
    equal('mock/submit', form.url());
    deepEqual([], this.mockListenerCalls('form-submit'));

    element.on('submit', function(e) {
        e.preventDefault();
        return false;
    });

    element.find('button').click();

    deepEqual([
        ['form-submit', [form, expected]]
    ], this.mockListenerJQueryCalls('form-submit'));
    equal(true, form.isValidHtml());
    equal(true, form.isValid());
    equal(true, form.isSubmitting());

    element.find('button').click();
    element.find('button').click();
    element.find('button').click();

    deepEqual([
        ['form-submit', [form, expected]]
    ], this.mockListenerJQueryCalls('form-submit'));
    equal(true, form.isValidHtml());
    equal(true, form.isValid());
    equal(true, form.isSubmitting());
});

}(jQuery));
