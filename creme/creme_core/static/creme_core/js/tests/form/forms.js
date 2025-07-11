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
    assert.equal(false, this.form.is('.is-form-active'));
    creme.forms.initialize(this.form);
    assert.equal(true, this.form.is('.is-form-active'));
});

QUnit.test('creme.forms (submit + required)', function(assert) {
    creme.forms.initialize(this.form);
    assert.equal(true, this.form.is('.is-form-active'));
    assert.equal(false, this.form.is('[novalidate]'));

    var firstname = this.form.find('[name="firstname"]');
    var lastname = this.form.find('[name="lastname"]');
    var email = this.form.find('[name="email"]');
    var submit = this.form.find('[type="submit"]');

    assert.equal(false, firstname.is(':invalid'));
    assert.equal(false, firstname.is('.is-field-invalid'));
    assert.equal(true, lastname.is(':invalid'));
    assert.equal(false, lastname.is('.is-field-invalid'));
    assert.equal(false, email.is(':invalid'));
    assert.equal(false, email.is('.is-field-invalid'));

    submit.trigger('click');

    assert.equal(false, this.form.is('[novalidate]'));
    assert.equal(false, submit.is('.is-form-submit'));

    assert.equal(false, firstname.is(':invalid'));
    assert.equal(false, firstname.is('.is-field-invalid'));
    assert.equal(true, lastname.is(':invalid'));
    assert.equal(true, lastname.is('.is-field-invalid'));
    assert.equal(false, email.is(':invalid'));
    assert.equal(false, email.is('.is-field-invalid'));

    assert.deepEqual([], this.mockFormSubmitCalls());
});

QUnit.test('creme.forms (submit + invalid email)', function(assert) {
    creme.forms.initialize(this.form);
    assert.equal(true, this.form.is('.is-form-active'));
    assert.equal(false, this.form.is('[novalidate]'));

    var firstname = this.form.find('[name="firstname"]');
    var lastname = this.form.find('[name="lastname"]');
    var email = this.form.find('[name="email"]');
    var submit = this.form.find('[type="submit"]');

    lastname.val('Doe');
    email.val('this is not an email');
    submit.trigger('click');

    assert.equal(false, this.form.is('[novalidate]'));
    assert.equal(false, submit.is('.is-form-submit'));

    assert.equal(false, firstname.is(':invalid'));
    assert.equal(false, firstname.is('.is-field-invalid'));
    assert.equal(false, lastname.is(':invalid'));
    assert.equal(false, lastname.is('.is-field-invalid'));
    assert.equal(true, email.is(':invalid'));
    assert.equal(true, email.is('.is-field-invalid'));

    assert.deepEqual([], this.mockFormSubmitCalls());
});

QUnit.test('creme.forms (novalidation)', function(assert) {
    creme.forms.initialize(this.form);
    assert.equal(true, this.form.is('.is-form-active'));
    assert.equal(false, this.form.is('[novalidate]'));

    var firstname = this.form.find('[name="firstname"]');
    var lastname = this.form.find('[name="lastname"]');
    var email = this.form.find('[name="email"]');
    var submit = this.form.find('[type="submit"]');

    submit.attr('data-no-validate', '');
    email.val('this is not an email');
    submit.trigger('click');

    assert.equal(true, this.form.is('[novalidate]'));
    assert.equal(true, submit.is('.is-form-submit'));

    assert.equal(false, firstname.is(':invalid'));
    assert.equal(false, firstname.is('.is-field-invalid'));
    assert.equal(true, lastname.is(':invalid'));
    assert.equal(false, lastname.is('.is-field-invalid'));  // skip validation step
    assert.equal(true, email.is(':invalid'));
    assert.equal(false, email.is('.is-field-invalid'));  // skip validation step

    assert.deepEqual(['mock/submit'], this.mockFormSubmitCalls());
});

QUnit.test('creme.forms (submit)', function(assert) {
    creme.forms.initialize(this.form);
    assert.equal(true, this.form.is('.is-form-active'));

    var firstname = this.form.find('[name="firstname"]');
    var lastname = this.form.find('[name="lastname"]');
    var email = this.form.find('[name="email"]');
    var submit = this.form.find('[type="submit"]');

    firstname.val('John');
    lastname.val('Doe');
    email.val('john.doe@unknown.com');
    submit.trigger('click');

    assert.equal(false, this.form.is('[novalidate]'));
    assert.equal(true, submit.is('.is-form-submit'));

    assert.equal(false, firstname.is(':invalid'));
    assert.equal(false, firstname.is('.is-field-invalid'));
    assert.equal(false, lastname.is(':invalid'));
    assert.equal(false, lastname.is('.is-field-invalid'));
    assert.equal(false, email.is(':invalid'));
    assert.equal(false, email.is('.is-field-invalid'));

    assert.deepEqual(['mock/submit'], this.mockFormSubmitCalls());
});

QUnit.test('creme.forms (multiple submit)', function(assert) {
    creme.forms.initialize(this.form);
    assert.equal(true, this.form.is('.is-form-active'));

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

    assert.equal(false, this.form.is('[novalidate]'));

    assert.equal(false, firstname.is(':invalid'));
    assert.equal(false, firstname.is('.is-field-invalid'));
    assert.equal(false, lastname.is(':invalid'));
    assert.equal(false, lastname.is('.is-field-invalid'));
    assert.equal(false, email.is(':invalid'));
    assert.equal(false, email.is('.is-field-invalid'));

    assert.deepEqual(['mock/submit'], this.mockFormSubmitCalls());
});

QUnit.test('creme.forms.validateHtml5Field (no constraint)', function(assert) {
    var field = $('<input type="text" name="name"/>');
    field.on('html5-invalid', this.mockListener('invalid'));

    assert.equal(false, field.is(':invalid'));
    assert.equal(false, field.is('.is-field-invalid'));
    assert.deepEqual([], this.mockListenerCalls('invalid'));

    assert.deepEqual({}, creme.forms.validateHtml5Field(field));

    assert.equal(false, field.is(':invalid'));
    assert.equal(false, field.is('.is-field-invalid'));
    assert.deepEqual([
        ['html5-invalid', [false]]
    ], this.mockListenerJQueryCalls('invalid'));
});

QUnit.test('creme.forms.validateHtml5Field (invalid)', function(assert) {
    var field = $('<input type="text" name="name" required/>');
    field.on('html5-invalid', this.mockListener('invalid'));

    assert.equal(true, field.is(':invalid'));
    assert.equal(false, field.is('.is-field-invalid'));
    assert.deepEqual([], this.mockListenerCalls('invalid'));

    assert.deepEqual({
        'name': field.get(0).validationMessage
    }, creme.forms.validateHtml5Field(field));

    assert.equal(true, field.is(':invalid'));
    assert.equal(true, field.is('.is-field-invalid'));
    assert.deepEqual([
        ['html5-invalid', [true, field.get(0).validationMessage]]
    ], this.mockListenerJQueryCalls('invalid'));
});

QUnit.test('creme.forms.validateHtml5Field (invalid => valid)', function(assert) {
    var field = $('<input type="text" name="name" required/>');
    creme.forms.validateHtml5Field(field);

    assert.equal(true, field.is(':invalid'));
    assert.equal(true, field.is('.is-field-invalid'));

    field.on('html5-invalid', this.mockListener('invalid'));
    field.val('not empty');

    assert.deepEqual({}, creme.forms.validateHtml5Field(field));

    assert.equal(false, field.is(':invalid'));
    assert.equal(false, field.is('.is-field-invalid'));
    assert.deepEqual([
        ['html5-invalid', [false]]
    ], this.mockListenerJQueryCalls('invalid'));
});

QUnit.test('creme.forms.validateHtml5Field ([novalidate])', function(assert) {
    var field = $('<input type="text" name="name" required novalidate/>');
    field.on('html5-invalid', this.mockListener('invalid'));

    assert.equal(true, field.is(':invalid'));
    assert.equal(false, field.is('.is-field-invalid'));
    assert.deepEqual([], this.mockListenerCalls('invalid'));

    assert.deepEqual({}, creme.forms.validateHtml5Field(field));

    assert.equal(true, field.is(':invalid'));
    assert.equal(false, field.is('.is-field-invalid'));
    assert.deepEqual([], this.mockListenerJQueryCalls('invalid'));
});


QUnit.test('creme.forms.validateHtml5Field (options.noValidate)', function(assert) {
    var field = $('<input type="text" name="name" required/>');
    field.on('html5-invalid', this.mockListener('invalid'));

    assert.equal(true, field.is(':invalid'));
    assert.equal(false, field.is('.is-field-invalid'));
    assert.deepEqual([], this.mockListenerCalls('invalid'));

    assert.deepEqual({}, creme.forms.validateHtml5Field(field, {noValidate: true}));

    assert.equal(true, field.is(':invalid'));
    assert.equal(false, field.is('.is-field-invalid'));
    assert.deepEqual([], this.mockListenerJQueryCalls('invalid'));
});

QUnit.test('creme.forms.validateHtml5Form (empty)', function(assert) {
    var form = $('<form>');
    assert.deepEqual({}, creme.forms.validateHtml5Form(form));
});

QUnit.test('creme.forms.validateHtml5Form (no error)', function(assert) {
    var firstname = this.form.find('[name="firstname"]').on('html5-invalid', this.mockListener('firstname-invalid'));
    var lastname = this.form.find('[name="lastname"]').on('html5-invalid', this.mockListener('lastname-invalid'));
    var email = this.form.find('[name="email"]').on('html5-invalid', this.mockListener('email-invalid'));

    this.form.on('html5-pre-validate', 'input', this.mockListener('pre-validate'));

    lastname.val('Doe');
    email.val('john.doe@unknown.com');

    assert.deepEqual({}, creme.forms.validateHtml5Form(this.form));

    assert.equal(false, firstname.is(':invalid'));
    assert.equal(false, firstname.is('.is-field-invalid'));
    assert.equal(false, lastname.is(':invalid'));
    assert.equal(false, lastname.is('.is-field-invalid'));
    assert.equal(false, email.is(':invalid'));
    assert.equal(false, email.is('.is-field-invalid'));

    assert.deepEqual({
        'firstname-invalid': [['html5-invalid', [false]]],
        'lastname-invalid': [['html5-invalid', [false]]],
        'email-invalid': [['html5-invalid', [false]]],
        'pre-validate': [
            ['html5-pre-validate', [{}]],
            ['html5-pre-validate', [{}]],
            ['html5-pre-validate', [{}]]
            // ignore input[type="submit"] field
        ]
    }, this.mockListenerJQueryCalls());
});

QUnit.test('creme.forms.validateHtml5Form (errors)', function(assert) {
    var firstname = this.form.find('[name="firstname"]').on('html5-invalid', this.mockListener('firstname-invalid'));
    var lastname = this.form.find('[name="lastname"]').on('html5-invalid', this.mockListener('lastname-invalid'));
    var email = this.form.find('[name="email"]').on('html5-invalid', this.mockListener('email-invalid'));

    email.val('not email');

    assert.deepEqual({
        'lastname': lastname.get(0).validationMessage,
        'email': email.get(0).validationMessage
    }, creme.forms.validateHtml5Form(this.form));

    assert.equal(false, firstname.is(':invalid'));
    assert.equal(false, firstname.is('.is-field-invalid'));
    assert.equal(true, lastname.is(':invalid'));
    assert.equal(true, lastname.is('.is-field-invalid'));
    assert.equal(true, email.is(':invalid'));
    assert.equal(true, email.is('.is-field-invalid'));

    assert.deepEqual({
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

    assert.deepEqual({}, creme.forms.validateHtml5Form(this.form));

    assert.equal(false, firstname.is(':invalid'));
    assert.equal(false, firstname.is('.is-field-invalid'));
    assert.equal(true, lastname.is(':invalid'));
    assert.equal(false, lastname.is('.is-field-invalid'));
    assert.equal(true, email.is(':invalid'));
    assert.equal(false, email.is('.is-field-invalid'));

    assert.deepEqual({}, this.mockListenerJQueryCalls());
});

QUnit.test('creme.forms.validateHtml5Form (errors + options.noValidate)', function(assert) {
    var firstname = this.form.find('[name="firstname"]').on('html5-invalid', this.mockListener('firstname-invalid'));
    var lastname = this.form.find('[name="lastname"]').on('html5-invalid', this.mockListener('lastname-invalid'));
    var email = this.form.find('[name="email"]').on('html5-invalid', this.mockListener('email-invalid'));

    email.val('not email');

    assert.deepEqual({}, creme.forms.validateHtml5Form(this.form, {noValidate: true}));

    assert.equal(false, firstname.is(':invalid'));
    assert.equal(false, firstname.is('.is-field-invalid'));
    assert.equal(true, lastname.is(':invalid'));
    assert.equal(false, lastname.is('.is-field-invalid'));
    assert.equal(true, email.is(':invalid'));
    assert.equal(false, email.is('.is-field-invalid'));

    assert.deepEqual({}, this.mockListenerJQueryCalls());
});

QUnit.test('creme.forms.TimePicker', function(assert) {
    var element = $('<ul>' +
        '<input type="hidden" id="time_field" value="08:32:00">' +
        '<li class="hour"><input type="number"/></li>' +
        '<li class="minute"><input type="number"/></li>' +
        '<li><button>Now</button></li>' +
    '</ul>');

    var input = element.find('#time_field');

    assert.deepEqual({hour: '08', minute: '32'}, creme.forms.TimePicker.timeval(element));

    creme.forms.TimePicker.init(element);
    assert.equal("08:32:00", input.val());
    assert.equal('08', element.find('.hour input').val());
    assert.equal('32', element.find('.minute input').val());
    assert.equal('08:32:00', creme.forms.TimePicker.val(element));

    assert.equal(element.find('.hour input').is('[disabled]'), false);
    assert.equal(element.find('.minute input').is('[disabled]'), false);
    assert.equal(element.find('button').is('[disabled]'), false);

    creme.forms.TimePicker.clear(element);
    assert.equal("", input.val());
    assert.equal('', element.find('.hour input').val());
    assert.equal('', element.find('.minute input').val());

    creme.forms.TimePicker.set(element, 12, 54);
    assert.equal("12:54", input.val());
    assert.equal('12', element.find('.hour input').val());
    assert.equal('54', element.find('.minute input').val());

    element.find('.hour input').val('07').trigger('change');
    assert.equal("07:54", input.val());
    assert.equal('07', element.find('.hour input').val());
    assert.equal('54', element.find('.minute input').val());

    this.withFrozenTime(new Date(2020, 5, 1, 16, 30), function() {
        element.find('button').trigger('click');
        assert.equal("16:30", input.val());
        assert.equal('16', element.find('.hour input').val());
        assert.equal('30', element.find('.minute input').val());
    });
});

QUnit.test('creme.forms.TimePicker (disabled)', function(assert) {
    var element = $('<ul>' +
        '<input type="hidden" id="time_field" value="09:26:00" disabled>' +
        '<li class="hour"><input type="number"/></li>' +
        '<li class="minute"><input type="number"/></li>' +
        '<li><button>Now</button></li>' +
    '</ul>');

    var input = element.find('#time_field');

    creme.forms.TimePicker.init(element);
    assert.equal("09:26:00", input.val());
    assert.equal('09', element.find('.hour input').val());
    assert.equal('26', element.find('.minute input').val());

    assert.equal(element.find('.hour input').is('[disabled]'), true);
    assert.equal(element.find('.minute input').is('[disabled]'), true);
    assert.equal(element.find('button').is('[disabled]'), true);
});

QUnit.test('creme.forms.DateTimePicker', function(assert) {
    var element = $('<ul>' +
            '<input type="hidden" id="time_field" value="2020-10-12 08:32:00">' +
            '<li class="date"><input type="text"/></li>' +
            '<li class="hour"><input type="number"/></li>' +
            '<li class="minute"><input type="number"/></li>' +
            '<li class="now"><button></button></li>' +
            '<li class="clear"><button></button></li>' +
        '</ul>');
    var input = element.find('#time_field');

    assert.deepEqual({date: '2020-10-12', hour: '08', minute: '32'}, creme.forms.DateTimePicker.datetimeval(element));

    creme.forms.DateTimePicker.init(element);
    assert.equal("2020-10-12 08:32:00", input.val());
    assert.equal('2020-10-12', element.find('.date input').val());
    assert.equal('08', element.find('.hour input').val());
    assert.equal('32', element.find('.minute input').val());
    assert.equal('2020-10-12 08:32:00', creme.forms.DateTimePicker.val(element));

    creme.forms.DateTimePicker.clear(element);
    assert.equal("", input.val());
    assert.equal('', element.find('.date input').val());
    assert.equal('', element.find('.hour input').val());
    assert.equal('', element.find('.minute input').val());

    creme.forms.DateTimePicker.setDate(element, new Date(2020, 4, 1, 16, 30));
    assert.equal("2020-05-01 16:30", input.val());
    assert.equal('2020-05-01', element.find('.date input').val());
    assert.equal('16', element.find('.hour input').val());
    assert.equal('30', element.find('.minute input').val());

    this.withFrozenTime(new Date(2020, 9, 18, 12, 30), function() {
        element.find('.now button').trigger('click');
        assert.equal("2020-10-18 12:30", input.val());
        assert.equal('2020-10-18', element.find('.date input').val());
        assert.equal('12', element.find('.hour input').val());
        assert.equal('30', element.find('.minute input').val());
    });

    element.find('.clear button').trigger('click');
    assert.equal("", input.val());
    assert.equal('', element.find('.date input').val());
    assert.equal('', element.find('.hour input').val());
    assert.equal('', element.find('.minute input').val());

    creme.forms.DateTimePicker.set(element, 2020, 4, 18, 17, 32);
    assert.equal("2020-05-18 17:32", input.val());
    assert.equal('2020-05-18', element.find('.date input').val());
    assert.equal('17', element.find('.hour input').val());
    assert.equal('32', element.find('.minute input').val());

    element.find('.date input').val('2021-12-24').trigger('change');
    assert.equal('2021-12-24', element.find('.date input').val());
    assert.equal('17', element.find('.hour input').val());
    assert.equal('32', element.find('.minute input').val());

    element.find('.minute input').val('54').trigger('change');
    assert.equal('2021-12-24', element.find('.date input').val());
    assert.equal('17', element.find('.hour input').val());
    assert.equal('54', element.find('.minute input').val());
});

}(jQuery));
