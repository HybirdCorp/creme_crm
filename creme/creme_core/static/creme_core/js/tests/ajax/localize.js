module("creme.ajax.backend.js", {
    setup: function() {
    },

    teardown: function() {
    },
});

test('creme.ajax.localizedErrorMessage (unknown)', function() {
    equal(gettext('Error'), creme.ajax.localizedErrorMessage());
    equal(gettext('Error'), creme.ajax.localizedErrorMessage(null));
    equal(gettext('Error'), creme.ajax.localizedErrorMessage({}));
    equal(gettext('Error'), creme.ajax.localizedErrorMessage({status: null}));

    equal(gettext('Error') + ' (612)', creme.ajax.localizedErrorMessage(612));
    equal(gettext('Error') + ' (612)', creme.ajax.localizedErrorMessage('612'));
    equal(gettext('Error') + ' (612)', creme.ajax.localizedErrorMessage({status: 612}));
});

test('creme.ajax.localizedErrorMessage (400)', function() {
    equal(gettext('Bad Request'), creme.ajax.localizedErrorMessage(400));
    equal(gettext('Bad Request'), creme.ajax.localizedErrorMessage('400'));
    equal(gettext('Bad Request'), creme.ajax.localizedErrorMessage({status: 400}));
});

test('creme.ajax.localizedErrorMessage (401)', function() {
    equal(gettext('Unauthorized'), creme.ajax.localizedErrorMessage(401));
    equal(gettext('Unauthorized'), creme.ajax.localizedErrorMessage('401'));
    equal(gettext('Unauthorized'), creme.ajax.localizedErrorMessage({status: 401}));
});

test('creme.ajax.localizedErrorMessage (403)', function() {
    equal(gettext('Forbidden Access'), creme.ajax.localizedErrorMessage(403));
    equal(gettext('Forbidden Access'), creme.ajax.localizedErrorMessage('403'));
    equal(gettext('Forbidden Access'), creme.ajax.localizedErrorMessage({status: 403}));
});

test('creme.ajax.localizedErrorMessage (404)', function() {
    equal(gettext('Not Found'), creme.ajax.localizedErrorMessage(404));
    equal(gettext('Not Found'), creme.ajax.localizedErrorMessage('404'));
    equal(gettext('Not Found'), creme.ajax.localizedErrorMessage({status: 404}));
});

test('creme.ajax.localizedErrorMessage (406)', function() {
    equal(gettext('Not Acceptable'), creme.ajax.localizedErrorMessage(406));
    equal(gettext('Not Acceptable'), creme.ajax.localizedErrorMessage('406'));
    equal(gettext('Not Acceptable'), creme.ajax.localizedErrorMessage({status: 406}));
});

test('creme.ajax.localizedErrorMessage (409)', function() {
    equal(gettext('Conflict'), creme.ajax.localizedErrorMessage(409));
    equal(gettext('Conflict'), creme.ajax.localizedErrorMessage('409'));
    equal(gettext('Conflict'), creme.ajax.localizedErrorMessage({status: 409}));
});

test('creme.ajax.localizedErrorMessage (500)', function() {
    equal(gettext('Internal Error'), creme.ajax.localizedErrorMessage(500));
    equal(gettext('Internal Error'), creme.ajax.localizedErrorMessage('500'));
    equal(gettext('Internal Error'), creme.ajax.localizedErrorMessage({status: 500}));
});
