(function($) {
"use strict";

QUnit.module("creme.BricksConfigEditor", new QUnitMixin(QUnitEventMixin,
                                                      QUnitMouseMixin, {
    createJSONDataHtml: function(data) {
        var html = '<script type="application/json" id="brick-config-choices">${data}</script>'.template({
            data: JSON.stringify(data)
        });

        return html;
    },

    createBrickEditorHtml: function(options) {
        options = $.extend({
            id: 'test-id',
            value: ''
        }, options || {});

        var html = (
            '<div class="bricks-config-widget" id="${id}">' +
                '<input type="hidden" name="${id}" value="${value}">' +
                '<div class="widget-available">' +
                    '<div class="widget-choices widget-available-choices"></div>' +
                '</div>' +
                '<div class="widget-enabled">' +
                    '<div class="widget-enabled-row">' +
                        '<div class="widget-enabled-top">' +
                            '<div class="widget-choices widget-enabled-top-choices"></div>' +
                        '</div>' +
                    '</div>' +
                    '<div class="widget-enabled-row">' +
                        '<div class="widget-enabled-left">' +
                            '<div class="widget-choices widget-enabled-left-choices"></div>' +
                        '</div>' +
                        '<div class="widget-enabled-right">' +
                            '<div class="widget-choices widget-enabled-right-choices"></div>' +
                        '</div>' +
                    '</div>' +
                    '<div class="widget-enabled-row">' +
                        '<div class="widget-enabled-bottom">' +
                            '<div class="widget-choices widget-enabled-bottom-choices"></div>' +
                        '</div>' +
                    '</div>' +
                '</div>' +
            '</div>'
        ).template(options);

        return html;
    },

    assertBrickChoiceGroup: function(element, name, expected) {
        var choices = element.find('.widget-${name}-choices .widget-choice'.template({name: name}));
        this.assert.deepEqual(choices.map(function() {
            return {
                value: $(this).attr('data-choice-id'),
                description: $(this).attr('title'),
                name: $(this).text()
            };
        }).get(), expected);
    }
}));

QUnit.test('creme.BricksConfigEditor (empty)', function(assert) {
    var element = $(this.createBrickEditorHtml()).appendTo(this.qunitFixture());
    var controller = new creme.BricksConfigEditor(element); /* eslint-disable-line */

    assert.equal(element.find('.widget-enabled-available-choices .widget-choice').length, 0);

    assert.equal(element.find('.widget-enabled-top-choices .widget-choice').length, 0);
    assert.equal(element.find('.widget-enabled-left-choices .widget-choice').length, 0);
    assert.equal(element.find('.widget-enabled-right-choices .widget-choice').length, 0);
    assert.equal(element.find('.widget-enabled-bottom-choices .widget-choice').length, 0);
});

QUnit.test('creme.BricksConfigEditor (invalid data)', function(assert) {
    var element = $(this.createBrickEditorHtml()).appendTo(this.qunitFixture());
    this.qunitFixture().append($('<script type="application/json" id="brick-config-choices">invalid !</script>'));

    assert.equal($('#brick-config-choices').text(), 'invalid !');

    this.assertRaises(function() {
        return new creme.BricksConfigEditor(element, {  /* eslint-disable-line */
            choices: $('#brick-config-choices')
        });
    }, Error);

    assert.equal(element.find('.widget-enabled-available-choices .widget-choice').length, 0);

    assert.equal(element.find('.widget-enabled-top-choices .widget-choice').length, 0);
    assert.equal(element.find('.widget-enabled-left-choices .widget-choice').length, 0);
    assert.equal(element.find('.widget-enabled-right-choices .widget-choice').length, 0);
    assert.equal(element.find('.widget-enabled-bottom-choices .widget-choice').length, 0);
});

QUnit.test('creme.BricksConfigEditor (initial data)', function(assert) {
    var element = $(this.createBrickEditorHtml()).appendTo(this.qunitFixture());
    this.qunitFixture().append($(this.createJSONDataHtml([{
        name: 'Brick A', value: 'brick-a', orientation: 'left'
    }, {
        name: 'Brick B', value: 'brick-b', orientation: 'left'
    }, {
        name: 'Brick C', value: 'brick-c', orientation: 'right'
    }, {
        name: 'Brick D', value: 'brick-d', orientation: 'top'
    }, {
        name: 'Brick E', value: 'brick-e', orientation: 'bottom'
    }, {
        name: 'Brick F', value: 'brick-f'
    }, {
        name: 'Brick G', value: 'brick-g', description: 'This is a brick'
    }])));

    var controller = new creme.BricksConfigEditor(element, { /* eslint-disable-line */
        choices: $('#brick-config-choices'),
        targetInput: $('#test-id')
    });

    this.assertBrickChoiceGroup(element, 'available', [{
        value: 'brick-f', name: 'Brick F', description: ''
    }, {
        value: 'brick-g', name: 'Brick G', description: 'This is a brick'
    }]);

    this.assertBrickChoiceGroup(element, 'enabled-top', [{
        value: 'brick-d', name: 'Brick D', description: ''
    }]);

    this.assertBrickChoiceGroup(element, 'enabled-right', [{
        value: 'brick-c', name: 'Brick C', description: ''
    }]);

    this.assertBrickChoiceGroup(element, 'enabled-left', [{
        value: 'brick-a', name: 'Brick A', description: ''
    }, {
        value: 'brick-b', name: 'Brick B', description: ''
    }]);

    this.assertBrickChoiceGroup(element, 'enabled-bottom', [{
        value: 'brick-e', name: 'Brick E', description: ''
    }]);

    assert.equal('', $('#test-id').val());
});

QUnit.test('creme.BricksConfigEditor (initial data)', function(assert) {
    var element = $(this.createBrickEditorHtml()).appendTo(this.qunitFixture());
    this.qunitFixture().append($(this.createJSONDataHtml([{
        name: 'Brick A', value: 'brick-a', orientation: 'left'
    }, {
        name: 'Brick B', value: 'brick-b', orientation: 'left'
    }, {
        name: 'Brick C', value: 'brick-c', orientation: 'right'
    }, {
        name: 'Brick D', value: 'brick-d', orientation: 'top'
    }, {
        name: 'Brick E', value: 'brick-e', orientation: 'bottom'
    }, {
        name: 'Brick F', value: 'brick-f'
    }, {
        name: 'Brick G', value: 'brick-g', description: 'This is a brick'
    }])));

    var controller = new creme.BricksConfigEditor(element, { /* eslint-disable-line */
        choices: $('#brick-config-choices'),
        targetInput: $('#test-id')
    });

    this.assertBrickChoiceGroup(element, 'available', [{
        value: 'brick-f', name: 'Brick F', description: ''
    }, {
        value: 'brick-g', name: 'Brick G', description: 'This is a brick'
    }]);

    this.assertBrickChoiceGroup(element, 'enabled-top', [{
        value: 'brick-d', name: 'Brick D', description: ''
    }]);

    this.assertBrickChoiceGroup(element, 'enabled-right', [{
        value: 'brick-c', name: 'Brick C', description: ''
    }]);

    this.assertBrickChoiceGroup(element, 'enabled-left', [{
        value: 'brick-a', name: 'Brick A', description: ''
    }, {
        value: 'brick-b', name: 'Brick B', description: ''
    }]);

    this.assertBrickChoiceGroup(element, 'enabled-bottom', [{
        value: 'brick-e', name: 'Brick E', description: ''
    }]);

    assert.equal('', $('#test-id').val());
});

QUnit.test('creme.BricksConfigEditor (on change)', function(assert) {
    var element = $(this.createBrickEditorHtml()).appendTo(this.qunitFixture());
    this.qunitFixture().append($(this.createJSONDataHtml([{
        name: 'Brick A', value: 'brick-a', orientation: 'left'
    }, {
        name: 'Brick B', value: 'brick-b', orientation: 'left'
    }, {
        name: 'Brick C', value: 'brick-c', orientation: 'right'
    }, {
        name: 'Brick D', value: 'brick-d', orientation: 'top'
    }, {
        name: 'Brick E', value: 'brick-e', orientation: 'bottom'
    }, {
        name: 'Brick F', value: 'brick-f'
    }, {
        name: 'Brick G', value: 'brick-g', description: 'This is a brick'
    }])));

    var controller = new creme.BricksConfigEditor(element, { /* eslint-disable-line */
        choices: $('#brick-config-choices'),
        targetInput: $('#test-id')
    });

    assert.equal('', $('#test-id').val());

    controller._onSort();

    assert.deepEqual({
        top: ['brick-d'],
        left: ['brick-a', 'brick-b'],
        right: ['brick-c'],
        bottom: ['brick-e']
    }, JSON.parse($('#test-id').val()));
});

// TODO : drag n drop test here

}(jQuery));
