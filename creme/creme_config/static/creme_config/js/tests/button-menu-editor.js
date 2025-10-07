(function($) {
"use strict";

QUnit.module("creme.ButtonMenuEditor", new QUnitMixin(QUnitEventMixin,
                                                      QUnitMouseMixin, {
    createJSONDataHtml: function(data) {
        var html = '<script type="application/json" id="buttons-widget-choices">${data}</script>'.template({
            data: JSON.stringify(data)
        });

        return html;
    },

    createButtonEditorHtml: function(options) {
        options = $.extend({
            id: 'id'
        }, options || {});

        var html = (
            '<div class="buttonmenu-edit-widget" id="${id}">' +
                '<div class="widget-available buttons-list instance-buttons">' +
                    '<div class="buttons-list-header">Available buttons</div>' +
                    '<div class="widget-container"></div>' +
                '</div>' +
                '<div class="widget-selected buttons-list instance-buttons">' +
                    '<div class="buttons-list-header">Selected buttons</div>' +
                    '<div class="widget-container" style="width: 100px;height: 100px;"></div>' +
                '</div>' +
            '</div>'
        ).template(options);

        return html;
    }
}));

QUnit.test('creme.ButtonMenuEditor (empty)', function(assert) {
    var element = $(this.createButtonEditorHtml()).appendTo(this.qunitFixture());
    var controller = new creme.ButtonMenuEditor(element); /* eslint-disable-line */

    assert.equal(element.find('.widget-available .widget-container .menu_button').length, 0);
    assert.equal(element.find('.widget-selected .widget-container .menu_button').length, 0);
});

QUnit.test('creme.ButtonMenuEditor (invalid data)', function(assert) {
    var element = $(this.createButtonEditorHtml()).appendTo(this.qunitFixture());
    this.qunitFixture().append($('<script type="application/json" id="buttons-widget-choices">invalid !</script>'));

    this.assertRaises(function() {
        return new creme.ButtonMenuEditor(element, {  /* eslint-disable-line */
            optionsId: 'buttons-widget-choices'
        });
    }, Error);

    assert.equal(element.find('.widget-available .widget-container .menu_button').length, 0);
    assert.equal(element.find('.widget-selected .widget-container .menu_button').length, 0);
});

QUnit.test('creme.ButtonMenuEditor (selected)', function(assert) {
    var element = $(this.createButtonEditorHtml()).appendTo(this.qunitFixture());

    this.qunitFixture().append($(this.createJSONDataHtml([{
        name: 'button-a', value: 'a', label: 'Button A', description: 'This is a button'
    }, {
        name: 'button-b', value: 'b', label: 'Button B', description: 'This is a button', selected: true
    }])));

    var controller = new creme.ButtonMenuEditor(element, {  /* eslint-disable-line */
        optionsId: 'buttons-widget-choices'
    });

    assert.equal(element.find('.widget-available .widget-container .menu_button').length, 1);
    assert.equal(element.find('.widget-selected .widget-container .menu_button').length, 1);
});

// TODO : drag n drop test here

}(jQuery));
