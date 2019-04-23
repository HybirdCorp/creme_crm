(function($) {

QUnit.module("creme.ajax.backend.js", new QUnitMixin());

QUnit.test('creme.ajax.localizedErrorMessage (unknown)', function(assert) {
    equal(gettext('Error'), creme.ajax.localizedErrorMessage());
    equal(gettext('Error'), creme.ajax.localizedErrorMessage(null));
    equal(gettext('Error'), creme.ajax.localizedErrorMessage({}));
    equal(gettext('Error'), creme.ajax.localizedErrorMessage({status: null}));

    equal(gettext('Error') + ' (612)', creme.ajax.localizedErrorMessage(612));
    equal(gettext('Error') + ' (612)', creme.ajax.localizedErrorMessage('612'));
    equal(gettext('Error') + ' (612)', creme.ajax.localizedErrorMessage({status: 612}));
});

QUnit.test('creme.ajax.localizedErrorMessage (400)', function(assert) {
    equal(gettext('Bad Request'), creme.ajax.localizedErrorMessage(400));
    equal(gettext('Bad Request'), creme.ajax.localizedErrorMessage('400'));
    equal(gettext('Bad Request'), creme.ajax.localizedErrorMessage({status: 400}));
});

QUnit.test('creme.ajax.localizedErrorMessage (401)', function(assert) {
    equal(gettext('Unauthorized'), creme.ajax.localizedErrorMessage(401));
    equal(gettext('Unauthorized'), creme.ajax.localizedErrorMessage('401'));
    equal(gettext('Unauthorized'), creme.ajax.localizedErrorMessage({status: 401}));
});

QUnit.test('creme.ajax.localizedErrorMessage (403)', function(assert) {
    equal(gettext('Forbidden Access'), creme.ajax.localizedErrorMessage(403));
    equal(gettext('Forbidden Access'), creme.ajax.localizedErrorMessage('403'));
    equal(gettext('Forbidden Access'), creme.ajax.localizedErrorMessage({status: 403}));
});

QUnit.test('creme.ajax.localizedErrorMessage (404)', function(assert) {
    equal(gettext('Not Found'), creme.ajax.localizedErrorMessage(404));
    equal(gettext('Not Found'), creme.ajax.localizedErrorMessage('404'));
    equal(gettext('Not Found'), creme.ajax.localizedErrorMessage({status: 404}));
});

QUnit.test('creme.ajax.localizedErrorMessage (406)', function(assert) {
    equal(gettext('Not Acceptable'), creme.ajax.localizedErrorMessage(406));
    equal(gettext('Not Acceptable'), creme.ajax.localizedErrorMessage('406'));
    equal(gettext('Not Acceptable'), creme.ajax.localizedErrorMessage({status: 406}));
});

QUnit.test('creme.ajax.localizedErrorMessage (409)', function(assert) {
    equal(gettext('Conflict'), creme.ajax.localizedErrorMessage(409));
    equal(gettext('Conflict'), creme.ajax.localizedErrorMessage('409'));
    equal(gettext('Conflict'), creme.ajax.localizedErrorMessage({status: 409}));
});

QUnit.test('creme.ajax.localizedErrorMessage (500)', function(assert) {
    equal(gettext('Internal Error'), creme.ajax.localizedErrorMessage(500));
    equal(gettext('Internal Error'), creme.ajax.localizedErrorMessage('500'));
    equal(gettext('Internal Error'), creme.ajax.localizedErrorMessage({status: 500}));
});

}(jQuery));
