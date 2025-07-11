/* globals QUnitWidgetMixin  */

(function($) {

QUnit.module("creme.widget.OrderedSelectList", new QUnitMixin(QUnitEventMixin,
                                                                QUnitWidgetMixin, {
    createOrderedSelectHtml: function(options) {
        options = Object.assign({
            choices: [],
            selection: []
        }, options || {});

        var html = (
            '<span widget="ui-creme-ordered" class="ui-creme-ordered ui-creme-widget ${auto}">' +
                '<script type="application/json"><!-- ${choices} --></script>' +
                '<input type="hidden" class="ordered-widget-value" value="${selection}" />' +
                '<div class="ordered-widget-container ordered-widget-container-available">' +
                    '<div class="ordered-widget-choices ordered-widget-available-choices"></div>' +
                '</div>' +
                '<div class="ordered-widget-container ordered-widget-container-enabled">' +
                    '<div class="ordered-widget-choices ordered-widget-enabled-choices"></div>' +
                '</div>' +
            '</span>'
        ).template({
            auto: options.auto ? 'widget-auto' : '',
            choices: JSON.stringify(options.choices || []),
            selection: JSON.stringify(options.selection || []).escapeHTML()
        });

        return html;
    },

    createOrderedSelect: function(options) {
        return creme.widget.create($(this.createOrderedSelectHtml(options)));
    },

    assertOrderedChoices: function(container, expected) {
        var data = container.find('.ordered-widget-choice').map(function() {
            return {
                order: $(this).data('order'),
                title: $(this).attr('title'),
                id: $(this).data('choiceId')
            };
        }).get();

        this.assert.deepEqual(data, (expected || []).map(function(item) {
            return {
                order: item.order,
                title: item.title,
                id: item.id
            };
        }));
    },

    assertEnabledChoices: function(element, expected) {
        this.assertOrderedChoices(element.find('.ordered-widget-enabled-choices'), expected);
    },

    assertAvailableChoices: function(element, expected) {
        this.assertOrderedChoices(element.find('.ordered-widget-available-choices'), expected);
    }
}));

QUnit.test('creme.widget.OrderedListSelect.create (empty)', function(assert) {
    var element = $(this.createOrderedSelectHtml({
        choices: [],
        selection: []
    }));

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.deepEqual([], widget.selected());
    assert.deepEqual([], widget.choices());

    this.assertAvailableChoices(element, []);
    this.assertEnabledChoices(element, []);
});

QUnit.test('creme.widget.OrderedListSelect.create', function(assert) {
    var element = $(this.createOrderedSelectHtml({
        choices: [
            {value: 'memo', label: 'Memo'},
            {value: 'past', label: 'Past', help: 'past ?'},
            {value: 'next', label: 'Next', disabled: true}
        ],
        selection: ['past', 'memo']
    }));

    var widget = creme.widget.create(element);

    assert.deepEqual(['past', 'memo'], JSON.parse($('input', element).val()));
    assert.deepEqual(['past', 'memo'], widget.selected());
    assert.deepEqual([
        {value: 'memo', initialOrder: 0, label: 'Memo'},
        {value: 'past', initialOrder: 1, help: 'past ?', label: 'Past'},
        {value: 'next', initialOrder: 2, label: 'Next', disabled: true}
    ], widget.choices());

    this.assertAvailableChoices(element, [
        {order: 2, id: 'next'}
    ]);

    this.assertEnabledChoices(element, [
        {order: 1, title: 'past ?', id: 'past'},
        {order: 0, id: 'memo'}
    ]);
});

QUnit.test('creme.widget.OrderedListSelect.select (dblclick)', function(assert) {
    var element = $(this.createOrderedSelectHtml({
        choices: [
            {value: 'memo', label: 'Memo'},
            {value: 'past', label: 'Past'},
            {value: 'next', label: 'Next'}
        ],
        selection: ['memo']
    }));

    var widget = creme.widget.create(element);

    assert.deepEqual(['memo'], widget.selected());
    this.assertEnabledChoices(element, [
        {order: 0, id: 'memo'}
    ]);

    element.find('.ordered-widget-available-choices [data-choice-id="next"]').trigger('dblclick');

    assert.deepEqual(['memo', 'next'], widget.selected());
    this.assertEnabledChoices(element, [
        {order: 0, id: 'memo'},
        {order: 2, id: 'next'}
    ]);

    element.find('.ordered-widget-available-choices [data-choice-id="past"]').trigger('dblclick');

    assert.deepEqual(['memo', 'next', 'past'], widget.selected());
    this.assertEnabledChoices(element, [
        {order: 0, id: 'memo'},
        {order: 2, id: 'next'},
        {order: 1, id: 'past'}
    ]);
});

QUnit.test('creme.widget.OrderedListSelect.deselect (click)', function(assert) {
    var element = $(this.createOrderedSelectHtml({
        choices: [
            {value: 'memo', label: 'Memo'},
            {value: 'past', label: 'Past'},
            {value: 'next', label: 'Next'}
        ],
        selection: ['memo', 'next']
    }));

    var widget = creme.widget.create(element);

    assert.deepEqual(['memo', 'next'], widget.selected());
    this.assertEnabledChoices(element, [
        {order: 0, id: 'memo'},
        {order: 2, id: 'next'}
    ]);

    element.find('.ordered-widget-enabled-choices [data-choice-id="next"] button').trigger('click');

    assert.deepEqual(['memo'], widget.selected());
    this.assertEnabledChoices(element, [
        {order: 0, id: 'memo'}
    ]);

    this.assertAvailableChoices(element, [
        {order: 1, id: 'past'},
        {order: 2, id: 'next'}
    ]);

    element.find('.ordered-widget-enabled-choices [data-choice-id="memo"] button').trigger('click');

    assert.deepEqual([], widget.selected());
    this.assertEnabledChoices(element, []);
    this.assertAvailableChoices(element, [
        {order: 0, id: 'memo'},
        {order: 1, id: 'past'},
        {order: 2, id: 'next'}
    ]);
});

}(jQuery));
