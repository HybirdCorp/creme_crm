/* globals QUnitConsoleMixin */

(function($) {

QUnit.module("creme.forms.js", new QUnitMixin(QUnitEventMixin,
                                              QUnitConsoleMixin, {
    beforeEach: function() {
        var self = this;

        this.resetMockFormSubmitCalls();
        this.form = $('<form action="mock/submit">' +
                          '<input type="text" name="firstname"></input>' +
                          '<input type="text" name="lastname" required></input>' +
                          '<input type="email" name="email"></input>' +
                          '<input type="submit" class="ui-creme-dialog-action"></input>' +
                      '</form>').appendTo(this.qunitFixture());

        this.form.on('submit', function(e) {
            e.preventDefault();
            self._mockFormSubmitCalls.push($(e.target).attr('action'));
        });
    },

    resetMockFormSubmitCalls: function() {
        this._mockFormSubmitCalls = [];
    },

    mockFormSubmitCalls: function() {
        return this._mockFormSubmitCalls;
    }
}));

QUnit.test('creme.forms.initialize', function(assert) {
    equal(false, this.form.is('.is-form-active'));
    creme.forms.initialize(this.form);
    equal(true, this.form.is('.is-form-active'));
});

QUnit.test('creme.forms (submit + required)', function(assert) {
    creme.forms.initialize(this.form);
    equal(true, this.form.is('.is-form-active'));
    equal(false, this.form.is('[novalidate]'));

    var firstname = this.form.find('[name="firstname"]');
    var lastname = this.form.find('[name="lastname"]');
    var email = this.form.find('[name="email"]');
    var submit = this.form.find('[type="submit"]');

    equal(false, firstname.is(':invalid'));
    equal(false, firstname.is('.is-field-invalid'));
    equal(true, lastname.is(':invalid'));
    equal(false, lastname.is('.is-field-invalid'));
    equal(false, email.is(':invalid'));
    equal(false, email.is('.is-field-invalid'));

    submit.trigger('click');

    equal(false, this.form.is('[novalidate]'));
    equal(false, submit.is('.is-form-submit'));

    equal(false, firstname.is(':invalid'));
    equal(false, firstname.is('.is-field-invalid'));
    equal(true, lastname.is(':invalid'));
    equal(true, lastname.is('.is-field-invalid'));
    equal(false, email.is(':invalid'));
    equal(false, email.is('.is-field-invalid'));

    deepEqual([], this.mockFormSubmitCalls());
});

QUnit.test('creme.forms (submit + invalid email)', function(assert) {
    creme.forms.initialize(this.form);
    equal(true, this.form.is('.is-form-active'));
    equal(false, this.form.is('[novalidate]'));

    var firstname = this.form.find('[name="firstname"]');
    var lastname = this.form.find('[name="lastname"]');
    var email = this.form.find('[name="email"]');
    var submit = this.form.find('[type="submit"]');

    lastname.val('Doe');
    email.val('this is not an email');
    submit.trigger('click');

    equal(false, this.form.is('[novalidate]'));
    equal(false, submit.is('.is-form-submit'));

    equal(false, firstname.is(':invalid'));
    equal(false, firstname.is('.is-field-invalid'));
    equal(false, lastname.is(':invalid'));
    equal(false, lastname.is('.is-field-invalid'));
    equal(true, email.is(':invalid'));
    equal(true, email.is('.is-field-invalid'));

    deepEqual([], this.mockFormSubmitCalls());
});

QUnit.test('creme.forms (novalidation)', function(assert) {
    creme.forms.initialize(this.form);
    equal(true, this.form.is('.is-form-active'));
    equal(false, this.form.is('[novalidate]'));

    var firstname = this.form.find('[name="firstname"]');
    var lastname = this.form.find('[name="lastname"]');
    var email = this.form.find('[name="email"]');
    var submit = this.form.find('[type="submit"]');

    submit.attr('data-no-validate', '');
    email.val('this is not an email');
    submit.trigger('click');

    equal(true, this.form.is('[novalidate]'));
    equal(true, submit.is('.is-form-submit'));

    equal(false, firstname.is(':invalid'));
    equal(false, firstname.is('.is-field-invalid'));
    equal(true, lastname.is(':invalid'));
    equal(false, lastname.is('.is-field-invalid'));  // skip validation step
    equal(true, email.is(':invalid'));
    equal(false, email.is('.is-field-invalid'));  // skip validation step

    deepEqual(['mock/submit'], this.mockFormSubmitCalls());
});

QUnit.test('creme.forms (submit)', function(assert) {
    creme.forms.initialize(this.form);
    equal(true, this.form.is('.is-form-active'));

    var firstname = this.form.find('[name="firstname"]');
    var lastname = this.form.find('[name="lastname"]');
    var email = this.form.find('[name="email"]');
    var submit = this.form.find('[type="submit"]');

    firstname.val('John');
    lastname.val('Doe');
    email.val('john.doe@unknown.com');
    submit.trigger('click');

    equal(false, this.form.is('[novalidate]'));
    equal(true, submit.is('.is-form-submit'));

    equal(false, firstname.is(':invalid'));
    equal(false, firstname.is('.is-field-invalid'));
    equal(false, lastname.is(':invalid'));
    equal(false, lastname.is('.is-field-invalid'));
    equal(false, email.is(':invalid'));
    equal(false, email.is('.is-field-invalid'));

    deepEqual(['mock/submit'], this.mockFormSubmitCalls());
});

QUnit.test('creme.forms (multiple submit)', function(assert) {
    creme.forms.initialize(this.form);
    equal(true, this.form.is('.is-form-active'));

    var firstname = this.form.find('[name="firstname"]');
    var lastname = this.form.find('[name="lastname"]');
    var email = this.form.find('[name="email"]');
    var submit = this.form.find('[type="submit"]');

    firstname.val('John');
    lastname.val('Doe');
    email.val('john.doe@unknown.com');

    submit.trigger('click');
    submit.trigger('click');
    submit.trigger('click');
    submit.trigger('click');
    submit.trigger('click');

    equal(false, this.form.is('[novalidate]'));

    equal(false, firstname.is(':invalid'));
    equal(false, firstname.is('.is-field-invalid'));
    equal(false, lastname.is(':invalid'));
    equal(false, lastname.is('.is-field-invalid'));
    equal(false, email.is(':invalid'));
    equal(false, email.is('.is-field-invalid'));

    deepEqual(['mock/submit'], this.mockFormSubmitCalls());
});

QUnit.test('creme.forms.validateHtml5Field (no constraint)', function(assert) {
    var field = $('<input type="text" name="name"/>');
    field.on('html5-invalid', this.mockListener('invalid'));

    equal(false, field.is(':invalid'));
    equal(false, field.is('.is-field-invalid'));
    deepEqual([], this.mockListenerCalls('invalid'));

    deepEqual({}, creme.forms.validateHtml5Field(field));

    equal(false, field.is(':invalid'));
    equal(false, field.is('.is-field-invalid'));
    deepEqual([
        ['html5-invalid', [false]]
    ], this.mockListenerJQueryCalls('invalid'));
});

QUnit.test('creme.forms.validateHtml5Field (invalid)', function(assert) {
    var field = $('<input type="text" name="name" required/>');
    field.on('html5-invalid', this.mockListener('invalid'));

    equal(true, field.is(':invalid'));
    equal(false, field.is('.is-field-invalid'));
    deepEqual([], this.mockListenerCalls('invalid'));

    deepEqual({
        'name': field.get(0).validationMessage
    }, creme.forms.validateHtml5Field(field));

    equal(true, field.is(':invalid'));
    equal(true, field.is('.is-field-invalid'));
    deepEqual([
        ['html5-invalid', [true, field.get(0).validationMessage]]
    ], this.mockListenerJQueryCalls('invalid'));
});

QUnit.test('creme.forms.validateHtml5Field (invalid => valid)', function(assert) {
    var field = $('<input type="text" name="name" required/>');
    creme.forms.validateHtml5Field(field);

    equal(true, field.is(':invalid'));
    equal(true, field.is('.is-field-invalid'));

    field.on('html5-invalid', this.mockListener('invalid'));
    field.val('not empty');

    deepEqual({}, creme.forms.validateHtml5Field(field));

    equal(false, field.is(':invalid'));
    equal(false, field.is('.is-field-invalid'));
    deepEqual([
        ['html5-invalid', [false]]
    ], this.mockListenerJQueryCalls('invalid'));
});

QUnit.test('creme.forms.validateHtml5Field ([novalidate])', function(assert) {
    var field = $('<input type="text" name="name" required novalidate/>');
    field.on('html5-invalid', this.mockListener('invalid'));

    equal(true, field.is(':invalid'));
    equal(false, field.is('.is-field-invalid'));
    deepEqual([], this.mockListenerCalls('invalid'));

    deepEqual({}, creme.forms.validateHtml5Field(field));

    equal(true, field.is(':invalid'));
    equal(false, field.is('.is-field-invalid'));
    deepEqual([], this.mockListenerJQueryCalls('invalid'));
});


QUnit.test('creme.forms.validateHtml5Field (options.noValidate)', function(assert) {
    var field = $('<input type="text" name="name" required/>');
    field.on('html5-invalid', this.mockListener('invalid'));

    equal(true, field.is(':invalid'));
    equal(false, field.is('.is-field-invalid'));
    deepEqual([], this.mockListenerCalls('invalid'));

    deepEqual({}, creme.forms.validateHtml5Field(field, {noValidate: true}));

    equal(true, field.is(':invalid'));
    equal(false, field.is('.is-field-invalid'));
    deepEqual([], this.mockListenerJQueryCalls('invalid'));
});

QUnit.test('creme.forms.validateHtml5Form (empty)', function(assert) {
    var form = $('<form>');
    deepEqual({}, creme.forms.validateHtml5Form(form));
});

QUnit.test('creme.forms.validateHtml5Form (no error)', function(assert) {
    var firstname = this.form.find('[name="firstname"]').on('html5-invalid', this.mockListener('firstname-invalid'));
    var lastname = this.form.find('[name="lastname"]').on('html5-invalid', this.mockListener('lastname-invalid'));
    var email = this.form.find('[name="email"]').on('html5-invalid', this.mockListener('email-invalid'));

    lastname.val('Doe');
    email.val('john.doe@unknown.com');

    deepEqual({}, creme.forms.validateHtml5Form(this.form));

    equal(false, firstname.is(':invalid'));
    equal(false, firstname.is('.is-field-invalid'));
    equal(false, lastname.is(':invalid'));
    equal(false, lastname.is('.is-field-invalid'));
    equal(false, email.is(':invalid'));
    equal(false, email.is('.is-field-invalid'));

    deepEqual({
        'firstname-invalid': [['html5-invalid', [false]]],
        'lastname-invalid': [['html5-invalid', [false]]],
        'email-invalid': [['html5-invalid', [false]]]
    }, this.mockListenerJQueryCalls());
});

QUnit.test('creme.forms.validateHtml5Form (errors)', function(assert) {
    var firstname = this.form.find('[name="firstname"]').on('html5-invalid', this.mockListener('firstname-invalid'));
    var lastname = this.form.find('[name="lastname"]').on('html5-invalid', this.mockListener('lastname-invalid'));
    var email = this.form.find('[name="email"]').on('html5-invalid', this.mockListener('email-invalid'));

    email.val('not email');

    deepEqual({
        'lastname': lastname.get(0).validationMessage,
        'email': email.get(0).validationMessage
    }, creme.forms.validateHtml5Form(this.form));

    equal(false, firstname.is(':invalid'));
    equal(false, firstname.is('.is-field-invalid'));
    equal(true, lastname.is(':invalid'));
    equal(true, lastname.is('.is-field-invalid'));
    equal(true, email.is(':invalid'));
    equal(true, email.is('.is-field-invalid'));

    deepEqual({
        'firstname-invalid': [['html5-invalid', [false]]],
        'lastname-invalid': [['html5-invalid', [true, lastname.get(0).validationMessage]]],
        'email-invalid': [['html5-invalid', [true, email.get(0).validationMessage]]]
    }, this.mockListenerJQueryCalls());
});

QUnit.test('creme.forms.validateHtml5Form (errors + novalidate)', function(assert) {
    var firstname = this.form.find('[name="firstname"]').on('html5-invalid', this.mockListener('firstname-invalid'));
    var lastname = this.form.find('[name="lastname"]').on('html5-invalid', this.mockListener('lastname-invalid'));
    var email = this.form.find('[name="email"]').on('html5-invalid', this.mockListener('email-invalid'));

    email.val('not email');

    this.form.attr('novalidate', 'novalidate');

    deepEqual({}, creme.forms.validateHtml5Form(this.form));

    equal(false, firstname.is(':invalid'));
    equal(false, firstname.is('.is-field-invalid'));
    equal(true, lastname.is(':invalid'));
    equal(false, lastname.is('.is-field-invalid'));
    equal(true, email.is(':invalid'));
    equal(false, email.is('.is-field-invalid'));

    deepEqual({}, this.mockListenerJQueryCalls());
});

QUnit.test('creme.forms.validateHtml5Form (errors + options.noValidate)', function(assert) {
    var firstname = this.form.find('[name="firstname"]').on('html5-invalid', this.mockListener('firstname-invalid'));
    var lastname = this.form.find('[name="lastname"]').on('html5-invalid', this.mockListener('lastname-invalid'));
    var email = this.form.find('[name="email"]').on('html5-invalid', this.mockListener('email-invalid'));

    email.val('not email');

    deepEqual({}, creme.forms.validateHtml5Form(this.form, {noValidate: true}));

    equal(false, firstname.is(':invalid'));
    equal(false, firstname.is('.is-field-invalid'));
    equal(true, lastname.is(':invalid'));
    equal(false, lastname.is('.is-field-invalid'));
    equal(true, email.is(':invalid'));
    equal(false, email.is('.is-field-invalid'));

    deepEqual({}, this.mockListenerJQueryCalls());
});

QUnit.test('creme.forms.Select.fill (deprecated)', function(assert) {
    var element = $('<select></select>');

    creme.forms.Select.fill(element, []);
    this.equalOuterHtml(element, '<select></select>');

    equal(this.mockConsoleWarnCalls().length, 1);
});

QUnit.test('creme.forms.Select.fill (select)', function(assert) {
    var element = $('<select></select>');

    creme.forms.Select.fill(element, [
        ['a', 'Label A'], ['b', 'Label B']
    ]);
    this.equalOuterHtml(element,
        '<select>' +
            '<option value="a">Label A</option>' +
            '<option value="b">Label B</option>' +
        '</select>');
    equal(element.val(), 'a');

    creme.forms.Select.fill(element, [
        ['a', 'Label A'], ['b', 'Label B']
    ], 'unknown');
    this.equalOuterHtml(element,
        '<select>' +
            '<option value="a">Label A</option>' +
            '<option value="b">Label B</option>' +
        '</select>');
    equal(element.val(), 'a');

    creme.forms.Select.fill(element, [
        ['c', 'Label C'], ['d', 'Label D'], ['e', 'Label E']
    ], 'd');
    this.equalOuterHtml(element,
        '<select>' +
            '<option value="c">Label C</option>' +
            '<option value="d">Label D</option>' +
            '<option value="e">Label E</option>' +
        '</select>');
    equal(element.val(), 'd');
});

QUnit.test('creme.forms.TimePicker', function(assert) {
    var element = $('<ul>' +
        '<input type="hidden" id="time_field" value="08:32:00">' +
        '<li class="hour"><input type="text"/></li>' +
        '<li class="minute"><input type="text"/></li>' +
        '<li><button>Now</button></li>' +
    '</ul>');

    var input = element.find('#time_field');

    deepEqual({hour: '08', minute: '32'}, creme.forms.TimePicker.timeval(element));

    creme.forms.TimePicker.init(element);
    equal("08:32:00", input.val());
    equal('08', element.find('.hour input').val());
    equal('32', element.find('.minute input').val());
    equal('08:32:00', creme.forms.TimePicker.val(element));

    equal(element.find('.hour input').is('[disabled]'), false);
    equal(element.find('.minute input').is('[disabled]'), false);
    equal(element.find('button').is('[disabled]'), false);

    creme.forms.TimePicker.clear(element);
    equal("", input.val());
    equal('', element.find('.hour input').val());
    equal('', element.find('.minute input').val());

    creme.forms.TimePicker.set(element, 12, 54);
    equal("12:54", input.val());
    equal('12', element.find('.hour input').val());
    equal('54', element.find('.minute input').val());

    element.find('.hour input').val('07').trigger('change');
    equal("07:54", input.val());
    equal('07', element.find('.hour input').val());
    equal('54', element.find('.minute input').val());

    this.withFrozenTime(new Date(2020, 5, 1, 16, 30), function() {
        element.find('button').trigger('click');
        equal("16:30", input.val());
        equal('16', element.find('.hour input').val());
        equal('30', element.find('.minute input').val());
    });
});

QUnit.test('creme.forms.TimePicker (disabled)', function(assert) {
    var element = $('<ul>' +
        '<input type="hidden" id="time_field" value="09:26:00" disabled>' +
        '<li class="hour"><input type="text"/></li>' +
        '<li class="minute"><input type="text"/></li>' +
        '<li><button>Now</button></li>' +
    '</ul>');

    var input = element.find('#time_field');

    creme.forms.TimePicker.init(element);
    equal("09:26:00", input.val());
    equal('09', element.find('.hour input').val());
    equal('26', element.find('.minute input').val());

    equal(element.find('.hour input').is('[disabled]'), true);
    equal(element.find('.minute input').is('[disabled]'), true);
    equal(element.find('button').is('[disabled]'), true);
});

QUnit.test('creme.forms.DateTimePicker', function(assert) {
    var element = $('<ul>' +
            '<input type="hidden" id="time_field" value="2020-10-12 08:32:00">' +
            '<li class="date"><input type="text"/></li>' +
            '<li class="hour"><input type="text"/></li>' +
            '<li class="minute"><input type="text"/></li>' +
            '<li class="now"><button></button></li>' +
            '<li class="clear"><button></button></li>' +
        '</ul>');
    var input = element.find('#time_field');

    deepEqual({date: '2020-10-12', hour: '08', minute: '32'}, creme.forms.DateTimePicker.datetimeval(element));

    creme.forms.DateTimePicker.init(element);
    equal("2020-10-12 08:32:00", input.val());
    equal('2020-10-12', element.find('.date input').val());
    equal('08', element.find('.hour input').val());
    equal('32', element.find('.minute input').val());
    equal('2020-10-12 08:32:00', creme.forms.DateTimePicker.val(element));

    creme.forms.DateTimePicker.clear(element);
    equal("", input.val());
    equal('', element.find('.date input').val());
    equal('', element.find('.hour input').val());
    equal('', element.find('.minute input').val());

    creme.forms.DateTimePicker.setDate(element, new Date(2020, 4, 1, 16, 30));
    equal("2020-05-01 16:30", input.val());
    equal('2020-05-01', element.find('.date input').val());
    equal('16', element.find('.hour input').val());
    equal('30', element.find('.minute input').val());

    this.withFrozenTime(new Date(2020, 9, 18, 12, 30), function() {
        element.find('.now button').trigger('click');
        equal("2020-10-18 12:30", input.val());
        equal('2020-10-18', element.find('.date input').val());
        equal('12', element.find('.hour input').val());
        equal('30', element.find('.minute input').val());
    });

    element.find('.clear button').trigger('click');
    equal("", input.val());
    equal('', element.find('.date input').val());
    equal('', element.find('.hour input').val());
    equal('', element.find('.minute input').val());

    creme.forms.DateTimePicker.set(element, 2020, 4, 18, 17, 32);
    equal("2020-05-18 17:32", input.val());
    equal('2020-05-18', element.find('.date input').val());
    equal('17', element.find('.hour input').val());
    equal('32', element.find('.minute input').val());

    element.find('.date input').val('2021-12-24').trigger('change');
    equal('2021-12-24', element.find('.date input').val());
    equal('17', element.find('.hour input').val());
    equal('32', element.find('.minute input').val());

    element.find('.minute input').val('54').trigger('change');
    equal('2021-12-24', element.find('.date input').val());
    equal('17', element.find('.hour input').val());
    equal('54', element.find('.minute input').val());
});

QUnit.parameterize('creme.forms.toImportField', [
    ['0', false],  // "Not in CSV" => not visible
    ['1', true]    // "Column 1" => visible
], function(initial, expected, assert) {
    this.qunitFixture().append($(
        '<table id="csv_field_a">' +
            '<tbody><tr>' +
                '<td class="csv_column_select">' +
                    '<select name="column_select" class="csv_col_select">' +
                        '<option value="0">Not here</option>' +
                        '<option value="1">Column 1</option>' +
                        '<option value="2">Column 2</option>' +
                    '</select>' +
                '</td>' +
                '<td class="csv_column_options">' +
                    '<input type="checkbox" id="field_a_create" name="field_a_create">Create</input>' +
                '</td>' +
            '</tr></tbody>' +
        '</table>')
    );

    $('#csv_field_a .csv_col_select').val(initial);

    // jquery 3.6+ : replace speed=0 by speed=null or an animation will be triggered anyway
    // and the ':visible' state may randomly fail
    creme.forms.toImportField('csv_field_a', '.csv_column_options', null);

    // initial visible state : 0 => hidden, 1 => visible
    equal($('#csv_field_a .csv_column_options').is(':visible'), expected);

    // toggle state "not in csv" => not visible
    $('#csv_field_a .csv_col_select').val('0').trigger('change');
    equal($('#csv_field_a .csv_column_options:not(:visible)').length, 1);

    // toggle state "Column 1" => visible
    $('#csv_field_a .csv_col_select').val('1').trigger('change');
    equal($('#csv_field_a .csv_column_options:visible').length, 1);
});

}(jQuery));
