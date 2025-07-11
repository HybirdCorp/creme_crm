
(function($) {

QUnit.module("jQuery.toggle-attr", new QUnitMixin());

QUnit.parametrize('jQuery.toggleAttr', [
    ['my-attr', true, undefined, {
        field_a: 'default',
        field_b: ''
    }],
    ['my-attr', true, 'my-val', {
        field_a: 'my-val',
        field_b: 'my-val'
    }],
    ['my-attr', false, undefined, {
        field_a: undefined,
        field_b: undefined
    }],
    ['my-attr', false, 'my-val', {
        field_a: undefined,
        field_b: undefined
    }],
    ['my-attr', undefined, undefined, {
        field_a: undefined,
        field_b: ''
    }],
    ['my-attr', undefined, 'my-val', {
        field_a: undefined,
        field_b: 'my-val'
    }]
], function(name, enabled, value, expected, assert) {
    var elements = $(
        '<div>' +
            '<input type="text" id="field-a" my-attr="default"/>' +
            '<input type="text" id="field-b" />' +
        '</div>'
    );

    elements.find('input').toggleAttr(name, enabled, value);

    assert.deepEqual(expected, {
        field_a: elements.find('#field-a').attr(name),
        field_b: elements.find('#field-b').attr(name)
    });
});

QUnit.parametrize('jQuery.toggleProp', [
    ['checked', true, undefined, {
        field_a: true,
        field_b: true
    }],
    ['my-prop', true, 'my-val', {
        field_a: 'my-val',
        field_b: 'my-val'
    }],
    ['checked', false, undefined, {
        field_a: false,
        field_b: false
    }],
    ['my-prop', false, 'my-val', {
        field_a: undefined,
        field_b: undefined
    }],
    ['checked', undefined, undefined, {
        field_a: false,
        field_b: true
    }],
    ['disabled', undefined, undefined, {
        field_a: true,
        field_b: false
    }]
], function(name, enabled, value, expected, assert) {
    var elements = $(
        '<div>' +
            '<input type="text" id="field-a" checked="checked" />' +
            '<input type="text" id="field-b" disabled />' +
        '<div>'
    );

    elements.find('input').toggleProp(name, enabled, value);

    assert.deepEqual(expected, {
        field_a: elements.find('#field-a').prop(name),
        field_b: elements.find('#field-b').prop(name)
    });
});

}(jQuery));
