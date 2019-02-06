(function($) {

var MOCK_FRAME_CONTENT_FORM = '<form action="mock/submit">' +
                                   '<input type="text" name="firstname"></input>' +
                                   '<input type="text" name="lastname" required></input>' +
                                   '<input type="submit" class="ui-creme-dialog-action"></input>' +
                               '</form>';
var MOCK_FRAME_CONTENT_FORM_ERROR = '<form action="mock/error">' +
                                         '<input type="text" name="firstname"></input>' +
                                         '<input type="text" name="lastname" required></input>' +
                                         '<input type="submit" class="ui-creme-dialog-action"></input>' +
                                    '</form>';
var MOCK_FRAME_CONTENT_FORM_REQUIRED = '<form action="mock/submit">' +
                                           '<input type="text" name="firstname" required></input>' +
                                           '<input type="text" name="lastname" required></input>' +
                                           '<input type="submit" class="ui-creme-dialog-action"></input>' +
                                       '</form>';
var MOCK_FRAME_CONTENT_FORM_BUTTON = '<form action="mock/submit/button">' +
                                         '<input type="text" name="firstname"></input>' +
                                         '<input type="text" name="lastname" required></input>' +
                                         '<button type="submit" class="ui-creme-dialog-action"></button>' +
                                     '</form>';

var MOCK_FRAME_CONTENT_FORM_MULTI = '<form action="mock/submit/multi">' +
                                        '<input type="text" name="firstname"></input>' +
                                        '<input type="text" name="lastname" required></input>' +
                                        '<input type="submit" value="Submit !"></input>' +
                                        '<input class="ui-creme-dialog-action" type="submit" value="Button A"></input>' +
                                        '<button class="ui-creme-dialog-action" type="submit" value="bbb">Button B</button>' +
                                        '<input class="ui-creme-dialog-action" type="submit" name="send-c" value="Button C"></input>' +
                                        '<button class="ui-creme-dialog-action" type="submit" name="button-d">Button D</button>' +
                                        '<button class="ui-creme-dialog-action" type="submit" name="button-e" value="eee">Button E</button>' +
                                   '</form>';

var MOCK_FRAME_CONTENT_FORM_MULTI_UNNAMED = '<form action="mock/submit/multi/unnamed">' +
                                                '<input type="text" name="firstname"></input>' +
                                                '<input type="text" name="lastname" required></input>' +
                                                '<input type="submit" class="ui-creme-dialog-action" value="A"></input>' +
                                                '<input type="submit" class="ui-creme-dialog-action" value="B"></input>' +
                                                '<button class="ui-creme-dialog-action" type="submit">Button A</button>' +
                                                '<button class="ui-creme-dialog-action" type="submit">Button B</button>' +
                                            '</form>';

var MOCK_FRAME_CONTENT_FORM_MULTI_DUPLICATES = '<form action="mock/submit/multi/duplicates">' +
                                                   '<input type="text" name="firstname"></input>' +
                                                   '<input type="text" name="lastname" required></input>' +
                                                   '<input type="submit" name="send" value="A" class="ui-creme-dialog-action"></input>' +
                                                   '<input type="submit" name="send" value="A" class="ui-creme-dialog-action"></input>' +
                                                   '<button class="ui-creme-dialog-action" name="button" type="submit" value="A"></button>' +
                                                   '<button class="ui-creme-dialog-action" name="button" type="submit" value="A">Duplicate</button>' +
                                               '</form>';

var MOCK_FRAME_CONTENT_FORM_JSON = '<form action="mock/submit/json">' +
                                        '<input type="text" name="responseType"></input>' +
                                        '<input type="submit" class="ui-creme-dialog-action"></input>' +
                                   '</form>';

var MOCK_FRAME_CONTENT_SUBMIT_JSON = '<json>${data}</json>';
var MOCK_FRAME_CONTENT_SUBMIT_JSON_PRE = '<pre style="word-wrap: break-word; white-space: pre-wrap;">' + $.toJSON({value: 2, added: [5, 'John Pre']}) + '</pre>';
var MOCK_FRAME_CONTENT_SUBMIT_JSON_INVALID = '<json>' + '{"value":1, added:[1, "John Doe"}' + '</json>';

QUnit.module("creme.dialog-form.js", new QUnitMixin(QUnitEventMixin,
                                                    QUnitAjaxMixin,
                                                    QUnitDialogMixin, {
    buildMockBackend: function() {
        return new creme.ajax.MockAjaxBackend({delay: 0, sync: true, name: 'creme.dialog-form.js'});
    },

    beforeEach: function() {
        var backend = this.backend;

        this.setMockBackendGET({
            'mock/submit': backend.response(200, MOCK_FRAME_CONTENT_FORM),
            'mock/submit/json': backend.response(200, MOCK_FRAME_CONTENT_FORM_JSON),
            'mock/submit/button': backend.response(200, MOCK_FRAME_CONTENT_FORM_BUTTON),
            'mock/submit/fail': backend.response(200, MOCK_FRAME_CONTENT_FORM_ERROR),
            'mock/submit/required': backend.response(200, MOCK_FRAME_CONTENT_FORM_REQUIRED),
            'mock/submit/multi': backend.response(200, MOCK_FRAME_CONTENT_FORM_MULTI),
            'mock/submit/multi/unnamed': backend.response(200, MOCK_FRAME_CONTENT_FORM_MULTI_UNNAMED),
            'mock/submit/multi/duplicates': backend.response(200, MOCK_FRAME_CONTENT_FORM_MULTI_DUPLICATES),
            'mock/forbidden': backend.response(403, 'HTTP - Error 403'),
            'mock/error': backend.response(500, 'HTTP - Error 500')
        });

        this.setMockBackendPOST({
            'mock/submit/json': function(url, data, options) {
                var responseType = data.responseType[0];
                var responseData = data.responseData ? data.responseData[0] : "";

                if (responseType === 'pre') {
                    return backend.response(200, MOCK_FRAME_CONTENT_SUBMIT_JSON_PRE);
                } else if (responseType === 'jsontag') {
                    return backend.response(200, MOCK_FRAME_CONTENT_SUBMIT_JSON.template({data: responseData}));
                } else if (responseType === 'invalid') {
                    return backend.response(200, MOCK_FRAME_CONTENT_SUBMIT_JSON_INVALID);
                } else if (responseType === 'empty') {
                    return backend.response(200, '');
                } else {
                    return backend.response(200, responseData, {'content-type': 'text/json'});
                }
            },
            'mock/submit': backend.response(200, MOCK_FRAME_CONTENT_FORM),
            'mock/submit/required': backend.response(200, MOCK_FRAME_CONTENT_FORM_REQUIRED),
            'mock/submit/button': backend.response(200, MOCK_FRAME_CONTENT_FORM_BUTTON),
            'mock/submit/fail': backend.response(400, 'Unable to submit this form'),
            'mock/submit/multi': backend.response(200, MOCK_FRAME_CONTENT_FORM_MULTI),
            'mock/submit/multi/unnamed': backend.response(200, MOCK_FRAME_CONTENT_FORM_MULTI_UNNAMED),
            'mock/submit/multi/duplicates': backend.response(200, MOCK_FRAME_CONTENT_FORM_MULTI_DUPLICATES),
            'mock/forbidden': backend.response(403, 'HTTP - Error 403'),
            'mock/error': backend.response(500, 'HTTP - Error 500')
        });

        this.mockPostSubmitRegistry = new creme.action.ActionBuilderRegistry();
        this.mockPostSubmitRegistry.registerAll({
            'redirect': function (url) {
                 return new creme.component.Action(function() {
                     creme.utils.goTo(url);
                     this.done();
                 });
             },
             'fail-it': function(url) {
                 return new creme.component.Action(function() {
                     this.fail();
                 });
             },
             'raise-it': function(url) {
                 throw new Error('invalid action !');
             },
             'cancel-it': function(url) {
                 return new creme.component.Action(function() {
                     this.cancel();
                 });
             }
        });
    },

    afterEach: function() {
        creme.widget.shutdown($('body'));
    }
}));

QUnit.test('creme.dialog.FormDialog (default validator)', function(assert) {
    var options = {validator: 'default'};
    var dialog = new creme.dialog.FormDialog(options);

    ok(Object.isFunc(dialog.validator()));

    equal(true, dialog._validate(new creme.dialog.FrameContentData('', 'text/html'), 'text/html'));
    equal(true, dialog._validate(new creme.dialog.FrameContentData('<div></div>', 'text/html'), 'text/html'));

    equal(false, dialog._validate(new creme.dialog.FrameContentData('<div><form></form></div>', 'text/html'), 'text/html'));
    equal(true, dialog._validate(new creme.dialog.FrameContentData('"<div><form></form></div>"', 'text/json'), 'text/json'));
});

QUnit.test('creme.dialog.FormDialog (compatible validator)', function(assert) {
    var options = {validator: 'innerpopup'};
    var dialog = new creme.dialog.FormDialog(options);

    ok(Object.isFunc(dialog.validator()));

    equal(true, dialog._validate(new creme.dialog.FrameContentData('', 'text/html'), 'text/html'));
    equal(false, dialog._validate(new creme.dialog.FrameContentData('<div></div>', 'text/html'), 'text/html'));
    equal(true, dialog._validate(new creme.dialog.FrameContentData('<div class="in-popup"></div>', 'text/html'), 'text/html'));
    equal(true, dialog._validate(new creme.dialog.FrameContentData('<div class="in-popup" closing="true"></div>', 'text/html'), 'text/html'));
    equal(true, dialog._validate(new creme.dialog.FrameContentData('<div class="in-popup" reload="/" closing="true"></div>', 'text/html'), 'text/html'));
    equal(true, dialog._validate(new creme.dialog.FrameContentData('<div closing="true" class="in-popup"></div>', 'text/html'), 'text/html'));
    equal(true, dialog._validate(new creme.dialog.FrameContentData('<div  closing="true"  reload="/"   class="in-popup"></div>', 'text/html'), 'text/html'));

    equal(false, dialog._validate(new creme.dialog.FrameContentData('<div><form></form></div>', 'text/html'), 'text/html'));
    equal(true, dialog._validate(new creme.dialog.FrameContentData('<div class="in-popup" closing="true"><form></form></div>', 'text/html'), 'text/html'), 'closing+form');
    equal(true, dialog._validate(new creme.dialog.FrameContentData('<div closing="true" class="in-popup"><form></form></div>', 'text/html'), 'text/html'));

    equal(true, dialog._validate(new creme.dialog.FrameContentData('"<div><form></form></div>"', 'text/json'), 'text/json'));
});

QUnit.test('creme.dialog.FormDialog (custom validator)', function(assert) {
    var validateAll = function() {
        return true;
    };
    var options = {validator: validateAll};
    var dialog = new creme.dialog.FormDialog(options);

    ok(Object.isFunc(dialog.validator()));
    equal(true, dialog._validate(new creme.dialog.FrameContentData('', 'text/html'), 'text/html'));
    equal(true, dialog._validate(new creme.dialog.FrameContentData('<div></div>', 'text/html'), 'text/html'));
    equal(true, dialog._validate(new creme.dialog.FrameContentData('<div><form></form></div>', 'text/html'), 'text/html'));
    equal(true, dialog._validate(new creme.dialog.FrameContentData('"<div><form></form></div>"', 'text/html'), 'text/json'));
});

QUnit.test('creme.dialog.FormDialog (invalid validator)', function(assert) {
    var options = {validator: 'string'};

    this.assertRaises(function() {
        return new creme.dialog.FormDialog(options);
    }, Error, 'Error: FormDialog validator "string" is unknown');

    var dialog = new creme.dialog.FormDialog();

    ok(Object.isFunc(dialog.validator()));

    this.assertRaises(function() {
        dialog.validator('string');
    }, Error, 'Error: FormDialog validator "string" is unknown');

    this.assertRaises(function() {
        dialog.validator(12);
    }, Error, 'Error: FormDialog validator "12" is not a function');
});

QUnit.test('creme.dialog.FormDialog (default button, empty form)', function(assert) {
    var dialog = new creme.dialog.FormDialog();
    dialog.on('frame-activated', this.mockListener('frame-activated'));

    dialog.open();
    deepEqual([], this.mockListenerCalls('frame-activated')); // nothing to activate

    equal(1, dialog.buttons().find('button').length);
    equal(gettext('Cancel'), dialog.button('cancel').text());

    dialog.close();
    deepEqual([], this.mockListenerCalls('frame-activated'));
});

QUnit.test('creme.dialog.FormDialog (default button, unamed submit input)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit', backend: this.backend});

    dialog.open();

    equal(2, dialog.buttons().find('button').length);
    equal(gettext('Save'), dialog.button('send').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    dialog.close();
});

QUnit.test('creme.dialog.FormDialog (default button, unamed submit input + click cancel)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit', backend: this.backend});

    dialog.open();

    equal(2, dialog.buttons().find('button').length);
    equal(gettext('Save'), dialog.button('send').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    dialog.button('cancel').click();
    equal(false, dialog.isOpened());
});

QUnit.test('creme.dialog.FormDialog (default button, unamed submit button)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/button', backend: this.backend});

    dialog.open();

    equal(2, dialog.buttons().find('button').length);
    equal(gettext('Save'), dialog.button('send').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    dialog.close();
});

QUnit.test('creme.dialog.FormDialog (default button, multiple unamed submit)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/multi/unnamed', backend: this.backend});

    dialog.open();

    equal(5, dialog.buttons().find('button').length);

    equal(gettext('A'), dialog.button('send').text());
    equal(gettext('B'), dialog.button('send-1').text());
    equal(gettext('Button A'), dialog.button('send-2').text());
    equal(gettext('Button B'), dialog.button('send-3').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    dialog.close();
});

QUnit.test('creme.dialog.FormDialog (multiple submit input/buttons)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/multi', backend: this.backend});

    dialog.open();

    equal(6, dialog.buttons().find('button').length);
    equal(gettext('Cancel'), dialog.button('cancel').text());

    equal('Button A', dialog.button('send').text());
    equal('Button B', dialog.button('send-1').text());   // unamed button with value "bbb"
    equal('Button C', dialog.button('send-c').text());   // input named "button-c"
    equal('Button D', dialog.button('button-d').text()); // button named "button-d"
    equal('Button E', dialog.button('button-e').text()); // button named "button-e" with value "eee"

    dialog.close();
});

QUnit.test('creme.dialog.FormDialog (multiple submit input/buttons, duplicates)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/multi/duplicates', backend: this.backend});

    dialog.open();

    equal(5, dialog.buttons().find('button').length);
    equal(gettext('Cancel'), dialog.button('cancel').text());

    equal('A', dialog.button('send').text());
    equal('A', dialog.button('send-1').text());
    equal(gettext('Save'), dialog.button('button').text());
    equal('Duplicate', dialog.button('button-1').text());

    dialog.close();
});

QUnit.test('creme.dialog.FormDialog (submit)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/button', backend: this.backend});

    dialog.open();

    equal(2, dialog.buttons().find('button').length);
    equal(gettext('Save'), dialog.button('send').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    dialog.form().find('[name="firstname"]').val('John');
    dialog.form().find('[name="lastname"]').val('Doe');

    equal(false, dialog.form().find('[name="firstname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="lastname"]').is(':invalid'));
    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/submit/button'));

    dialog.submit();

    deepEqual([
        ['GET', {}],
        ['POST', {
            firstname: ['John'],
            lastname: ['Doe']
        }]
    ], this.mockBackendUrlCalls('mock/submit/button'));
});

QUnit.test('creme.dialog.FormDialog (submit, invalid response)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/fail', backend: this.backend});

    dialog.open();

    equal(2, dialog.buttons().find('button').length);
    equal(gettext('Save'), dialog.button('send').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    ok(dialog.button('send').is(':not([disabled])'));
    ok(dialog.button('cancel').is(':not([disabled])'));

    dialog.form().find('[name="firstname"]').val('John');
    dialog.form().find('[name="lastname"]').val('Doe');

    equal(false, dialog.form().find('[name="firstname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="lastname"]').is(':invalid'));
    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/submit/fail'));

    dialog.submit();

    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/submit/fail'));

    ok(dialog.button('send').is('[disabled]'));
    ok(dialog.button('cancel').is(':not([disabled])'));
});

QUnit.test('creme.dialog.FormDialog (submit lastname required)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/button', backend: this.backend});

    dialog.open();

    equal(2, dialog.buttons().find('button').length);
    equal(gettext('Save'), dialog.button('send').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    dialog.form().find('[name="firstname"]').val('John');

    equal(false, dialog.form().find('[name="firstname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="firstname"]').is('.is-field-invalid'));

    equal(true, dialog.form().find('[name="lastname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="lastname"]').is('.is-field-invalid'));

    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/submit/button'));

    dialog.submit();

    equal(false, dialog.form().find('[name="firstname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="firstname"]').is('.is-field-invalid'));

    equal(true, dialog.form().find('[name="lastname"]').is(':invalid'));
    equal(true, dialog.form().find('[name="lastname"]').is('.is-field-invalid'));

    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/submit/button'));
});

QUnit.test('creme.dialog.FormDialog (submit all required)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/required', backend: this.backend});

    dialog.open();

    equal(2, dialog.buttons().find('button').length);
    equal(gettext('Save'), dialog.button('send').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    dialog.form().find('[name="firstname"]').val('John');

    equal(false, dialog.form().find('[name="firstname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="firstname"]').is('.is-field-invalid'));

    equal(true, dialog.form().find('[name="lastname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="lastname"]').is('.is-field-invalid'));

    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/submit/required'));

    dialog.submit();

    equal(false, dialog.form().find('[name="firstname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="firstname"]').is('.is-field-invalid'));

    equal(true, dialog.form().find('[name="lastname"]').is(':invalid'));
    equal(true, dialog.form().find('[name="lastname"]').is('.is-field-invalid'));

    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/submit/required'));

    dialog.form().find('[name="firstname"]').val('');
    dialog.form().find('[name="lastname"]').val('Doe');

    dialog.submit();

    equal(true, dialog.form().find('[name="firstname"]').is(':invalid'));
    equal(true, dialog.form().find('[name="firstname"]').is('.is-field-invalid'));

    equal(false, dialog.form().find('[name="lastname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="lastname"]').is('.is-field-invalid'));

    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/submit/required'));
});

QUnit.test('creme.dialog.FormDialog (submit + form[novalidate])', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/button', backend: this.backend});

    dialog.open();

    equal(2, dialog.buttons().find('button').length);
    equal(gettext('Save'), dialog.button('send').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    dialog.form().attr('novalidate', 'novalidate');

    equal(false, dialog.form().find('[name="firstname"]').is(':invalid'));
    equal(true, dialog.form().find('[name="lastname"]').is(':invalid'));
    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/submit/button'));

    dialog.submit();

    equal(false, dialog.form().find('[name="firstname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="firstname"]').is('.is-field-invalid'));

    equal(true, dialog.form().find('[name="lastname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="lastname"]').is('.is-field-invalid'));

    deepEqual([
        ['GET', {}],
        ['POST', {
            firstname: [''],
            lastname: ['']
        }]
    ], this.mockBackendUrlCalls('mock/submit/button'));
});


QUnit.test('creme.dialog.FormDialog (submit + options.noValidate)', function(assert) {
    var dialog = new creme.dialog.FormDialog({
        url: 'mock/submit/button',
        backend: this.backend,
        noValidate: true
    });

    dialog.open();

    equal(2, dialog.buttons().find('button').length);
    equal(gettext('Save'), dialog.button('send').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    equal(false, dialog.form().find('[name="firstname"]').is(':invalid'));
    equal(true, dialog.form().find('[name="lastname"]').is(':invalid'));
    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/submit/button'));

    dialog.submit();

    equal(false, dialog.form().find('[name="firstname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="firstname"]').is('.is-field-invalid'));

    equal(true, dialog.form().find('[name="lastname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="lastname"]').is('.is-field-invalid'));

    deepEqual([
        ['GET', {}],
        ['POST', {
            firstname: [''],
            lastname: ['']
        }]
    ], this.mockBackendUrlCalls('mock/submit/button'));
});

QUnit.test('creme.dialog.FormDialog (submit + extra data)', function(assert) {
    var dialog = new creme.dialog.FormDialog({
        url: 'mock/submit/button',
        backend: this.backend,
        submitData: {
            extra: 12,
            other: 'test'
        }
    });

    dialog.open();

    equal(2, dialog.buttons().find('button').length);
    equal(gettext('Save'), dialog.button('send').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    dialog.form().find('[name="firstname"]').val('John');
    dialog.form().find('[name="lastname"]').val('Doe');

    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/submit/button'));

    dialog.submit();

    deepEqual([
        ['GET', {}],
        ['POST', {
            firstname: ['John'],
            lastname: ['Doe'],
            extra: [12],
            other: ['test']
        }]
    ], this.mockBackendUrlCalls('mock/submit/button'));

    dialog.form().find('[name="firstname"]').val('John');
    dialog.form().find('[name="lastname"]').val('Doe');

    dialog.submit({}, {
        extra: 78,
        custom: true,
        lastname: 'Toe'
    });

    deepEqual([
        ['GET', {}],
        ['POST', {
            firstname: ['John'],
            lastname: ['Doe'],
            extra: [12],
            other: ['test']
        }],
        ['POST', {
            firstname: ['John'],
            lastname: ['Doe', 'Toe'],
            extra: [78],
            other: ['test'],
            custom: [true]
        }]
    ], this.mockBackendUrlCalls('mock/submit/button'));
});

QUnit.test('creme.dialog.FormDialog (click + submit)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/button', backend: this.backend});

    dialog.open();

    equal(2, dialog.buttons().find('button').length);
    equal(gettext('Save'), dialog.button('send').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    dialog.form().find('[name="firstname"]').val('John');
    dialog.form().find('[name="lastname"]').val('Doe');

    equal(false, dialog.form().find('[name="firstname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="lastname"]').is(':invalid'));
    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/submit/button'));

    dialog.button('send').click();

    deepEqual([
        ['GET', {}],
        ['POST', {
            firstname: ['John'],
            lastname: ['Doe']
        }]
    ], this.mockBackendUrlCalls('mock/submit/button'));
});

QUnit.test('creme.dialog.FormDialog (submitOnKey + submit)', function(assert) {
    var dialog = new creme.dialog.FormDialog({
        url: 'mock/submit/button',
        backend: this.backend
    });

    equal(13, dialog.submitKey());

    dialog.open();

    equal(2, dialog.buttons().find('button').length);
    equal(gettext('Save'), dialog.button('send').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    dialog.form().find('[name="firstname"]').val('John');
    dialog.form().find('[name="lastname"]').val('Doe');

    equal(false, dialog.form().find('[name="firstname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="lastname"]').is(':invalid'));
    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/submit/button'));

    dialog.content().trigger($.Event("keypress", {keyCode: 13}));

    deepEqual([
        ['GET', {}],
        ['POST', {
            firstname: ['John'],
            lastname: ['Doe']
        }]
    ], this.mockBackendUrlCalls('mock/submit/button'));
});

QUnit.test('creme.dialog.FormDialog (no submitOnKey)', function(assert) {
    var dialog = new creme.dialog.FormDialog({
        url: 'mock/submit/button',
        backend: this.backend,
        submitOnKey: false
    });

    equal(false, dialog.submitKey());

    dialog.open();

    equal(2, dialog.buttons().find('button').length);
    equal(gettext('Save'), dialog.button('send').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    dialog.form().find('[name="firstname"]').val('John');
    dialog.form().find('[name="lastname"]').val('Doe');

    equal(false, dialog.form().find('[name="firstname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="lastname"]').is(':invalid'));
    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/submit/button'));

    // no submitkey
    dialog.content().trigger($.Event("keypress", {keyCode: 13}));

    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/submit/button'));

    dialog.submitKey(13);

    equal(13, dialog.submitKey());
    dialog.content().trigger($.Event("keypress", {keyCode: 13}));

    deepEqual([
        ['GET', {}],
        ['POST', {
            firstname: ['John'],
            lastname: ['Doe']
        }]
    ], this.mockBackendUrlCalls('mock/submit/button'));
});

QUnit.test('creme.dialog.FormDialog (prevent multiple submit click)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/button', backend: this.backend});

    dialog.open();

    equal(2, dialog.buttons().find('button').length);
    equal(gettext('Save'), dialog.button('send').text());
    equal(gettext('Cancel'), dialog.button('cancel').text());

    dialog.form().find('[name="firstname"]').val('John');
    dialog.form().find('[name="lastname"]').val('Doe');

    equal(false, dialog.form().find('[name="firstname"]').is(':invalid'));
    equal(false, dialog.form().find('[name="lastname"]').is(':invalid'));
    equal(false, dialog.button('send').is('.ui-state-disabled'));
    deepEqual([
        ['GET', {}]
    ], this.mockBackendUrlCalls('mock/submit/button'));

    dialog.button('send').click();
    dialog.button('send').click();
    dialog.button('send').click();
    dialog.button('send').click();
    dialog.button('send').click();

    deepEqual([
        ['GET', {}],
        ['POST', {
            firstname: ['John'],
            lastname: ['Doe']
        }]
    ], this.mockBackendUrlCalls('mock/submit/button'));
});

QUnit.test('creme.dialog.FormDialog (multiple submit input/buttons click)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/multi', backend: this.backend});

    dialog.open();

    equal(6, dialog.buttons().find('button').length);
    equal(gettext('Cancel'), dialog.button('cancel').text());

    equal('Button A', dialog.button('send').text());
    equal('Button B', dialog.button('send-1').text());   // unamed button with value "bbb"
    equal('Button C', dialog.button('send-c').text());   // input named "button-c"
    equal('Button D', dialog.button('button-d').text()); // button named "button-d"
    equal('Button E', dialog.button('button-e').text()); // button named "button-e" with value "eee"

    dialog.form().find('[name="firstname"]').val('John');
    dialog.form().find('[name="lastname"]').val('Doe');
    dialog.button('send').click();

    deepEqual([
        ['GET', {}],
        ['POST', {firstname: ['John'], lastname: ['Doe']}]
    ], this.mockBackendUrlCalls('mock/submit/multi'));

    this.resetMockBackendCalls();

    dialog.fetch('mock/submit/multi');
    dialog.form().find('[name="firstname"]').val('John');
    dialog.form().find('[name="lastname"]').val('Doe');
    dialog.button('send-1').click();

    deepEqual([
        ['GET', {}],
        ['POST', {firstname: ['John'], lastname: ['Doe']}]
    ], this.mockBackendUrlCalls('mock/submit/multi'));

    this.resetMockBackendCalls();

    dialog.fetch('mock/submit/multi');
    dialog.form().find('[name="firstname"]').val('John');
    dialog.form().find('[name="lastname"]').val('Doe');
    dialog.button('send-c').click();

    deepEqual([
        ['GET', {}],
        ['POST', {firstname: ['John'], lastname: ['Doe']}]
    ], this.mockBackendUrlCalls('mock/submit/multi'));

    this.resetMockBackendCalls();

    dialog.fetch('mock/submit/multi');
    dialog.form().find('[name="firstname"]').val('John');
    dialog.form().find('[name="lastname"]').val('Doe');
    dialog.button('button-d').click();

    deepEqual([
        ['GET', {}],
        ['POST', {firstname: ['John'], lastname: ['Doe'], 'button-d': ['']}]
    ], this.mockBackendUrlCalls('mock/submit/multi'));

    this.resetMockBackendCalls();

    dialog.fetch('mock/submit/multi');
    dialog.form().find('[name="firstname"]').val('John');
    dialog.form().find('[name="lastname"]').val('Doe');
    dialog.button('button-e').click();

    deepEqual([
        ['GET', {}],
        ['POST', {firstname: ['John'], lastname: ['Doe'], 'button-e': ['eee']}]
    ], this.mockBackendUrlCalls('mock/submit/multi'));

    dialog.close();
});

QUnit.test('creme.dialog.FormDialog (multiple submit duplicates input/buttons click)', function(assert) {
    // Check if 'button' and its duplicate 'button-1' with the same value 'A' will
    // send the same POST data : {button: ['A']}
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/multi/duplicates', backend: this.backend});

    dialog.open();

    equal(5, dialog.buttons().find('button').length);
    equal(gettext('Cancel'), dialog.button('cancel').text());

    equal('A', dialog.button('send').text());
    equal('A', dialog.button('send-1').text());
    equal(gettext('Save'), dialog.button('button').text());
    equal('Duplicate', dialog.button('button-1').text());

    dialog.form().find('[name="firstname"]').val('John');
    dialog.form().find('[name="lastname"]').val('Doe');
    dialog.button('send').click();

    deepEqual([
        ['GET', {}],
        ['POST', {firstname: ['John'], lastname: ['Doe']}]
    ], this.mockBackendUrlCalls('mock/submit/multi/duplicates'));

    this.resetMockBackendCalls();

    dialog.fetch('mock/submit/multi/duplicates');
    dialog.form().find('[name="firstname"]').val('John');
    dialog.form().find('[name="lastname"]').val('Doe');
    dialog.button('send-1').click();

    deepEqual([
        ['GET', {}],
        ['POST', {firstname: ['John'], lastname: ['Doe']}]
    ], this.mockBackendUrlCalls('mock/submit/multi/duplicates'));

    this.resetMockBackendCalls();

    dialog.fetch('mock/submit/multi/duplicates');
    dialog.form().find('[name="firstname"]').val('John');
    dialog.form().find('[name="lastname"]').val('Doe');
    dialog.button('button').click();

    deepEqual([
        ['GET', {}],
        ['POST', {firstname: ['John'], lastname: ['Doe'], button: ['A']}]
    ], this.mockBackendUrlCalls('mock/submit/multi/duplicates'));

    this.resetMockBackendCalls();

    dialog.fetch('mock/submit/multi/duplicates');
    dialog.form().find('[name="firstname"]').val('John');
    dialog.form().find('[name="lastname"]').val('Doe');
    dialog.button('button-1').click();

    deepEqual([
        ['GET', {}],
        ['POST', {firstname: ['John'], lastname: ['Doe'], button: ['A']}]
    ], this.mockBackendUrlCalls('mock/submit/multi/duplicates'));

    dialog.close();
});

QUnit.test('creme.dialog.FormDialog (<json>JSON</json> response)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/json', backend: this.backend});

    dialog.onFormSuccess(this.mockListener('form-success'));
    dialog.open();

    dialog.form().find('[name="responseType"]').val('jsontag');
    dialog.submit({}, {
        responseData: $.toJSON({value: 1, added: [1, 'John Doe']})
    });

    deepEqual([
        ['GET', {}],
        ['POST', {
            responseType: ['jsontag'],
            responseData: [$.toJSON({value: 1, added: [1, 'John Doe']})]
        }]
    ], this.mockBackendUrlCalls('mock/submit/json'));

    deepEqual([
        ['form-success', {
            content: $.toJSON({value: 1, added: [1, 'John Doe']}),
            data: {value: 1, added: [1, 'John Doe']},
            type: 'text/json'
        }, 'text/json']
    ], this.mockFormSubmitCalls('form-success'));
});

QUnit.test('creme.dialog.FormDialog (<pre>JSON</pre> response)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/json', backend: this.backend});

    dialog.onFormSuccess(this.mockListener('form-success'));
    dialog.open();

    dialog.form().find('[name="responseType"]').val('pre');
    dialog.submit();

    deepEqual([
        ['GET', {}],
        ['POST', {
            responseType: ['pre']
        }]
    ], this.mockBackendUrlCalls('mock/submit/json'));

    deepEqual([
        ['form-success', {
            content: $.toJSON({value: 2, added: [5, 'John Pre']}),
            data: {value: 2, added: [5, 'John Pre']},
            type: 'text/json'
        }, 'text/json']
    ], this.mockFormSubmitCalls('form-success'));
});

QUnit.test('creme.dialog.FormDialog (JSON response)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/json', backend: this.backend});

    dialog.onFormSuccess(this.mockListener('form-success'));
    dialog.open();

    dialog.submit({}, {
        responseData: $.toJSON({value: 3, added: [-8, 'John NoTag']})
    });

    deepEqual([
        ['GET', {}],
        ['POST', {
            responseType: [''],
            responseData: [$.toJSON({value: 3, added: [-8, 'John NoTag']})]
        }]
    ], this.mockBackendUrlCalls('mock/submit/json'));

    deepEqual([
        ['form-success', {
            content: $.toJSON({value: 3, added: [-8, 'John NoTag']}),
            data: {value: 3, added: [-8, 'John NoTag']},
            type: 'text/json'
        }, 'text/json']
    ], this.mockFormSubmitCalls('form-success'));
});

QUnit.test('creme.dialog.FormDialog (invalid JSON response)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/json', backend: this.backend});

    dialog.onFormSuccess(this.mockListener('form-success'));
    dialog.open();

    dialog.form().find('[name="responseType"]').val('invalid');
    dialog.submit();

    deepEqual([
        ['GET', {}],
        ['POST', {
            responseType: ['invalid']
        }]
    ], this.mockBackendUrlCalls('mock/submit/json'));

    deepEqual([
        ['form-success', {
            content: '<json>{"value":1, added:[1, "John Doe"}</json>',
            data: '<json>{"value":1, added:[1, "John Doe"}</json>',
            type: 'text/html'
         }, 'text/html']
    ], this.mockFormSubmitCalls('form-success'));
});

QUnit.test('creme.dialog.FormDialog (empty response)', function(assert) {
    var dialog = new creme.dialog.FormDialog({url: 'mock/submit/json', backend: this.backend});

    dialog.onFormSuccess(this.mockListener('form-success'));
    dialog.open();

    dialog.form().find('[name="responseType"]').val('empty');
    dialog.submit();

    deepEqual([
        ['GET', {}],
        ['POST', {
            responseType: ['empty']
        }]
    ], this.mockBackendUrlCalls('mock/submit/json'));

    deepEqual([
        ['form-success', {content: '', data: '', type: 'text/html'}, 'text/html']
    ], this.mockFormSubmitCalls('form-success'));
});

}(jQuery));
