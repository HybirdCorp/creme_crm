/* eslint operator-linebreak: ["error", "before"] */

(function($) {

QUnit.module("creme.persons", new QUnitMixin(QUnitEventMixin,
                                             QUnitAjaxMixin,
                                             QUnitBrickMixin, {
    createFormHtml: function(options) {
        options = $.extend({
            id: '',
            fields: [
                '<select name="field_a"><option value="1">#1</option><option value="2">#2</option></option>',
                '<input name="field_b" type="text" value="" />',
                '<textarea name="field_c"></textarea>'
            ]
        }, options || {});

        return (
            '<form action="${url}" id="${id}">'
                + '${fields}'
            + '</form>'
        ).template({
            url: options.url || '',
            id: options.id || '',
            fields: (options.fields || []).join('')
        });
    }
}));


QUnit.test('creme.persons.copyAddressInputs', function(assert) {
    var form_left = $(this.createFormHtml({
        id: 'A',
        fields: [
            '<select name="left-select"><option value="1">#1</option><option value="2">#2</option></option>',
            '<input name="left-text" type="text" value="" />',
            '<textarea name="left-area"></textarea>',
            '<input name="other-text" type="text" value="Left side" />'
        ]
    })).appendTo(this.qunitFixture());

    var form_right = $(this.createFormHtml({
        id: 'B',
        fields: [
            '<select name="right-select"><option value="1">#1</option><option value="2">#2</option></option>',
            '<input name="right-text" type="text" value="" />',
            '<textarea name="right-area"></textarea>',
            '<input name="other-text" type="text" value="Right side" />'
        ]
    })).appendTo(this.qunitFixture());

    form_left.find('[name="left-select"]').val('2');
    form_left.find('[name="left-area"]').val('This is a test');
    form_right.find('[name="right-text"]').val('This is another test');

    assert.deepEqual({
        'left-select': ['2'],
        'left-text': [''],
        'left-area': ['This is a test'],
        'other-text': ['Left side']
    }, creme.ajax.serializeFormAsDict(form_left));

    assert.deepEqual({
        'right-select': ['1'],
        'right-text': ['This is another test'],
        'right-area': [''],
        'other-text': ['Right side']
    }, creme.ajax.serializeFormAsDict(form_right));

    creme.persons.copyAddressInputs('left', 'right', form_left, form_right);

    assert.deepEqual({
        'left-select': ['2'],
        'left-text': [''],
        'left-area': ['This is a test'],
        'other-text': ['Left side']
    }, creme.ajax.serializeFormAsDict(form_left));

    assert.deepEqual({
        'right-select': ['2'],
        'right-text': [''],
        'right-area': ['This is a test'],
        'other-text': ['Right side']
    }, creme.ajax.serializeFormAsDict(form_right));

    creme.persons.copyAddressInputs('other', 'right', form_left, form_right);

    assert.deepEqual({
        'left-select': ['2'],
        'left-text': [''],
        'left-area': ['This is a test'],
        'other-text': ['Left side']
    }, creme.ajax.serializeFormAsDict(form_left));

    assert.deepEqual({
        'right-select': ['2'],
        'right-text': ['Left side'],
        'right-area': ['This is a test'],
        'other-text': ['Right side']
    }, creme.ajax.serializeFormAsDict(form_right));

    creme.persons.copyAddressInputs('other', 'left', form_right, form_left);

    assert.deepEqual({
        'left-select': ['2'],
        'left-text': ['Right side'],
        'left-area': ['This is a test'],
        'other-text': ['Left side']
    }, creme.ajax.serializeFormAsDict(form_left));

    assert.deepEqual({
        'right-select': ['2'],
        'right-text': ['Left side'],
        'right-area': ['This is a test'],
        'other-text': ['Right side']
    }, creme.ajax.serializeFormAsDict(form_right));
});

QUnit.test('creme.persons.copyAddressInputs (self copy)', function(assert) {
    var form_left = $(this.createFormHtml({
        id: 'A',
        fields: [
            '<select name="left-select"><option value="1">#1</option><option value="2">#2</option></option>',
            '<input name="left-text" type="text" value="This is a text" />',
            '<textarea name="left-area">This is an area</textarea>',
            '<input name="other-text" type="text" value="Other text" />',
            '<textarea name="other-area" type="text"></textarea>'
        ]
    })).appendTo(this.qunitFixture());

    assert.deepEqual({
        'left-select': ['1'],
        'left-text': ['This is a text'],
        'left-area': ['This is an area'],
        'other-text': ['Other text'],
        'other-area': ['']
    }, creme.ajax.serializeFormAsDict(form_left));

    creme.persons.copyAddressInputs('left', 'other', form_left);

    assert.deepEqual({
        'left-select': ['1'],
        'left-text': ['This is a text'],
        'left-area': ['This is an area'],
        'other-text': ['This is a text'],
        'other-area': ['This is an area']
    }, creme.ajax.serializeFormAsDict(form_left));
});

}(jQuery));
