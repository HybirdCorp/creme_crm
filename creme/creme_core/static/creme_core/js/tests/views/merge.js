/* globals QUnitWidgetMixin */

QUnit.module("creme.initializeMergeForm", new QUnitMixin(QUnitEventMixin,
                                                    QUnitWidgetMixin, {
    createMergeFormHtml: function(options) {
        options = $.extend({
            fields: []
        }, options || {});

        var renderMergeField = function(item) {
            item = $.extend({
                leftValue: '',
                rightValue: '',
                name: 'name',
                renderField: function(field) {
                    return (
                        '<input type="text" name="${name}" value="${value}" id="id_${name}" readonly>'
                    ).template(field);
                }
            }, item || {});

            return (
                '<ul data-name="${name}" class="merge-field" id="id_${name}">' +
                    '<li class="merge-field-container merge-field-1">${left}</li>' +
                    '<li class="merge-field-container merge-field-result">${merged}</li>' +
                    '<li class="merge-field-container merge-field-2">${right}</li>' +
                '</ul>'
            ).template({
                name: item.name,
                left: item.renderField({name: item.name + '_1', value: item.first}),
                merged: item.renderField({name: item.name + '_merged', value: ''}),
                right: item.renderField({name: item.name + '_2', value: item.second})
            });
        };

        return (
            '<form>${items}</form>'
        ).template({
            items: options.fields.map(renderMergeField).join('')
        });
    }
}));

QUnit.test('initializeMergeForm (buttons)', function(assert) {
    var element = $(this.createMergeFormHtml({
        fields: [{
            name: 'field_a', first: 'left', second: 'right'
        }, {
            name: 'field_b', first: '1', second: '2'
        }]
    })).appendTo(this.qunitFixture());

    assert.equal(0, element.find('.merge-field-button').length);

    creme.initializeMergeForm(element);

    assert.equal(4, element.find('.merge-field-button').length);

    assert.deepEqual([
        {from: 'id_field_a_1', to: 'id_field_a_merged'},
        {from: 'id_field_a_2', to: 'id_field_a_merged'},
        {from: 'id_field_b_1', to: 'id_field_b_merged'},
        {from: 'id_field_b_2', to: 'id_field_b_merged'}
    ].sort(), element.find('.merge-field-button button').map(function() {
        return $(this).data();
    }).get().sort());
});

QUnit.test('initializeMergeForm (copy)', function(assert) {
    var element = $(this.createMergeFormHtml({
        fields: [{
            name: 'field_a', first: 'left', second: 'right'
        }]
    })).appendTo(this.qunitFixture());

    creme.initializeMergeForm(element);

    var merged = element.find('#id_field_a_merged');

    assert.equal(merged.val(), '');

    var leftButton = element.find('.merge-right-arrow').parents('button:first');
    var rightButton = element.find('.merge-left-arrow').parents('button:first');

    leftButton.trigger('click');
    assert.equal(merged.val(), 'left');

    rightButton.trigger('click');
    assert.equal(merged.val(), 'right');
});

QUnit.test('initializeMergeForm (copy, checkbox)', function(assert) {
    var element = $(this.createMergeFormHtml({
        fields: [{
            name: 'field_a',
            first: true,
            second: false,
            renderField: function(item) {
                return (
                    '<input type="checkbox" name="${name}" id="id_${name}" readonly ${checked}>'
                ).template({
                    name: item.name,
                    checked: item.value ? 'checked' : ''
                });
            }
        }]
    })).appendTo(this.qunitFixture());

    creme.initializeMergeForm(element);

    var merged = element.find('#id_field_a_merged');
    var first = element.find('#id_field_a_1');
    var second = element.find('#id_field_a_2');

    assert.equal(merged.prop('checked'), false);
    assert.equal(first.prop('checked'), true);
    assert.equal(second.prop('checked'), false);

    var leftButton = element.find('.merge-right-arrow').parents('button:first');
    var rightButton = element.find('.merge-left-arrow').parents('button:first');

    leftButton.trigger('click');
    assert.equal(merged.prop('checked'), true);

    rightButton.trigger('click');
    assert.equal(merged.prop('checked'), false);
});


QUnit.test('initializeMergeForm (copy, widget)', function(assert) {
    var self = this;
    var element = $(this.createMergeFormHtml({
        fields: [{
            name: 'field_a',
            first: '',
            second: '',
            renderField: function(item) {
                var element = self.createEntitySelectorTag({
                    id: 'id_' + item.name,
                    value: item.value
                });

                return $('div').append(element).html();
            }
        }]
    })).appendTo(this.qunitFixture());

    creme.widget.ready(element);

    creme.initializeMergeForm(element);

    var merged = element.find('#id_field_a_merged');
    var first = element.find('#id_field_a_1');
    var second = element.find('#id_field_a_2');

    // must be initialized here through the widget.
    first.creme().widget().val('19');
    second.creme().widget().val('87');

    assert.equal(merged.creme().widget().val(), '');

    var leftButton = element.find('.merge-right-arrow').parents('button:first');
    var rightButton = element.find('.merge-left-arrow').parents('button:first');

    leftButton.trigger('click');
    assert.equal(merged.creme().widget().val(), '19');

    rightButton.trigger('click');
    assert.equal(merged.creme().widget().val(), '87');
});


