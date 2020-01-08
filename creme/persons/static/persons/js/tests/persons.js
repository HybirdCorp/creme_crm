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

QUnit.test('creme.persons.copyTo', function(assert) {
    var form_A = $(this.createFormHtml({id: 'A'})).appendTo(this.qunitFixture());
    var form_B = $(this.createFormHtml({id: 'B'})).appendTo(this.qunitFixture());

    form_A.find('select').val('2');
    form_A.find('textarea').val('This is a test');
    form_B.find('input').val('This is another test');

    deepEqual({
        field_a: ['2'],
        field_b: [''],
        field_c: ['This is a test']
    }, creme.ajax.serializeFormAsDict(form_A));

    deepEqual({
        field_a: ['1'],
        field_b: ['This is another test'],
        field_c: ['']
    }, creme.ajax.serializeFormAsDict(form_B));

    creme.persons.copyTo('A', 'B');

    deepEqual({
        field_a: ['2'],
        field_b: [''],
        field_c: ['This is a test']
    }, creme.ajax.serializeFormAsDict(form_A));

    deepEqual({
        field_a: ['2'],
        field_b: [''],
        field_c: ['This is a test']
    }, creme.ajax.serializeFormAsDict(form_B));
});

}(jQuery));
