var SIMPLE_FORM = 

QUnit.module("creme.forms.js", {
    setup: function() {
        var self = this;

        this.resetMockSubmitCalls();
        this.anchor = $('<div></div>').appendTo($('body'));
        this.form = $('<form action="mock/submit">' +
                          '<input type="text" name="firstname"></input>' +
                          '<input type="text" name="lastname" required></input>' +
                          '<input type="email" name="email"></input>' +
                          '<input type="submit" class="ui-creme-dialog-action"></input>' +
                      '</form>').appendTo(this.anchor);

        this.form.on('submit', function(e) {
            e.preventDefault();
            self._mockSubmitCalls.push($(e.target).attr('action'));
        });
    },

    teardown: function() {
        this.anchor.detach();
    },

    resetMockSubmitCalls: function() {
        this._mockSubmitCalls = [];
    },

    mockSubmitCalls: function() {
        return this._mockSubmitCalls;
    },

    assertRaises: function(block, expected, message) {
        QUnit.assert.raises(block.bind(this),
               function(error) {
                    ok(error instanceof expected, 'error is ' + expected);
                    equal(message, '' + error);
                    return true;
               });
    }
});

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

    deepEqual([], this.mockSubmitCalls());
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

    deepEqual([], this.mockSubmitCalls());
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

    deepEqual(['mock/submit'], this.mockSubmitCalls());
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

    deepEqual(['mock/submit'], this.mockSubmitCalls());
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

    deepEqual(['mock/submit'], this.mockSubmitCalls());
});
