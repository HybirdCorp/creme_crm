/* global QUnitFormMixin */
(function($) {

QUnit.module("creme.forms.js", new QUnitMixin(QUnitEventMixin,
                                              QUnitFormMixin, {
    beforeEach: function() {
        this.form = $('<form action="mock/submit">' +
                          '<input type="text" name="firstname"></input>' +
                          '<input type="text" name="lastname" required></input>' +
                          '<input type="email" name="email"></input>' +
                          '<input type="submit" class="ui-creme-dialog-action"></input>' +
                      '</form>').appendTo(this.qunitFixture());
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

    submit.click();

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
    submit.click();

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
    submit.click();

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
    submit.click();

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

    submit.click();
    submit.click();
    submit.click();
    submit.click();
    submit.click();

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

}(jQuery));
