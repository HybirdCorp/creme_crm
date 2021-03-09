(function($) {
"use strict";

QUnit.module("creme.UserSettingController", new QUnitMixin(QUnitAjaxMixin,
                                                           QUnitEventMixin, {
    buildMockBackend: function() {
        return new creme.ajax.MockAjaxBackend({sync: true, name: 'creme.widget.chainedselect.js'});
    },

    beforeEach: function() {
        this.setMockBackendPOST({
            'mock/toggle': this.backend.response(200, ''),
            'mock/error': this.backend.response(500, 'HTTP - Error 500')
        });
    }
}));

QUnit.test('creme.UserSettingController (change)', function(assert) {
    var current_url = window.location.href;
    var element = $('<div><select class="user-setting-toggle" data-url="mock/toggle" name="theme">' +
        '<option value="a">A</option>' +
        '<option value="b">B</option>' +
    '</select></div>');

    new creme.UserSettingController(element); /* eslint-disable-line */

    element.find('select').val('b').trigger('change');

    deepEqual([
        ['POST', {theme: 'b'}]
    ], this.mockBackendUrlCalls('mock/toggle'));

    deepEqual([current_url], this.mockReloadCalls());
});

QUnit.test('creme.UserSettingController (no url)', function(assert) {
    var element = $('<div><select class="user-setting-toggle" data-url="" name="theme">' +
        '<option value="a">A</option>' +
        '<option value="b">B</option>' +
    '</select></div>');

    new creme.UserSettingController(element); /* eslint-disable-line */

    element.find('select').val('b').trigger('change');

    deepEqual([], this.mockBackendUrlCalls('mock/toggle'));
    deepEqual([], this.mockReloadCalls());
});

QUnit.test('creme.UserSettingController (invalid url)', function(assert) {
    var element = $('<div><select class="user-setting-toggle" data-url="mock/error" name="theme">' +
        '<option value="a">A</option>' +
        '<option value="b">B</option>' +
    '</select></div>');

    new creme.UserSettingController(element); /* eslint-disable-line */

    element.find('select').val('b').trigger('change');

    deepEqual([
        ['POST', {theme: 'b'}]
    ], this.mockBackendUrlCalls('mock/error'));

    deepEqual([], this.mockReloadCalls());
});

}(jQuery));
