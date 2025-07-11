(function($) {

QUnit.module("creme.ajax.backend.js", new QUnitMixin());

QUnit.test('creme.ajax.localizedErrorMessage (unknown)', function(assert) {
    assert.equal(gettext('Error'), creme.ajax.localizedErrorMessage());
    assert.equal(gettext('Error'), creme.ajax.localizedErrorMessage(null));
    assert.equal(gettext('Error'), creme.ajax.localizedErrorMessage({}));
    assert.equal(gettext('Error'), creme.ajax.localizedErrorMessage({status: null}));

    assert.equal(gettext('Error') + ' (612)', creme.ajax.localizedErrorMessage(612));
    assert.equal(gettext('Error') + ' (612)', creme.ajax.localizedErrorMessage('612'));
    assert.equal(gettext('Error') + ' (612)', creme.ajax.localizedErrorMessage({status: 612}));
});

QUnit.test('creme.ajax.localizedErrorMessage (400)', function(assert) {
    assert.equal(gettext('Bad Request'), creme.ajax.localizedErrorMessage(400));
    assert.equal(gettext('Bad Request'), creme.ajax.localizedErrorMessage('400'));
    assert.equal(gettext('Bad Request'), creme.ajax.localizedErrorMessage({status: 400}));
});

QUnit.test('creme.ajax.localizedErrorMessage (401)', function(assert) {
    assert.equal(gettext('Unauthorized'), creme.ajax.localizedErrorMessage(401));
    assert.equal(gettext('Unauthorized'), creme.ajax.localizedErrorMessage('401'));
    assert.equal(gettext('Unauthorized'), creme.ajax.localizedErrorMessage({status: 401}));
});

QUnit.test('creme.ajax.localizedErrorMessage (403)', function(assert) {
    assert.equal(gettext('Forbidden Access'), creme.ajax.localizedErrorMessage(403));
    assert.equal(gettext('Forbidden Access'), creme.ajax.localizedErrorMessage('403'));
    assert.equal(gettext('Forbidden Access'), creme.ajax.localizedErrorMessage({status: 403}));
});

QUnit.test('creme.ajax.localizedErrorMessage (404)', function(assert) {
    assert.equal(gettext('Not Found'), creme.ajax.localizedErrorMessage(404));
    assert.equal(gettext('Not Found'), creme.ajax.localizedErrorMessage('404'));
    assert.equal(gettext('Not Found'), creme.ajax.localizedErrorMessage({status: 404}));
});

QUnit.test('creme.ajax.localizedErrorMessage (406)', function(assert) {
    assert.equal(gettext('Not Acceptable'), creme.ajax.localizedErrorMessage(406));
    assert.equal(gettext('Not Acceptable'), creme.ajax.localizedErrorMessage('406'));
    assert.equal(gettext('Not Acceptable'), creme.ajax.localizedErrorMessage({status: 406}));
});

QUnit.test('creme.ajax.localizedErrorMessage (409)', function(assert) {
    assert.equal(gettext('Conflict'), creme.ajax.localizedErrorMessage(409));
    assert.equal(gettext('Conflict'), creme.ajax.localizedErrorMessage('409'));
    assert.equal(gettext('Conflict'), creme.ajax.localizedErrorMessage({status: 409}));
});

QUnit.test('creme.ajax.localizedErrorMessage (500)', function(assert) {
    assert.equal(gettext('Internal Error'), creme.ajax.localizedErrorMessage(500));
    assert.equal(gettext('Internal Error'), creme.ajax.localizedErrorMessage('500'));
    assert.equal(gettext('Internal Error'), creme.ajax.localizedErrorMessage({status: 500}));
});

}(jQuery));
