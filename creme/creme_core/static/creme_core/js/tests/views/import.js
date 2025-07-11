(function($) {

QUnit.module("creme.widget.ImportField", new QUnitMixin());

QUnit.parameterize('creme.widget.ImportField', [
    ['0', false],  // "Not in CSV" => not visible
    ['1', true]    // "Column 1" => visible
], function(initial, expected, assert) {
    var element = $(
        '<table id="csv_field_a" class="ui-creme-widget widget-auto ui-import-field" widget="ui-import-field">' +
            '<tbody><tr>' +
                '<td class="csv_column_select import-field-select">' +
                    '<select name="column_select" class="csv_col_select">' +
                        '<option value="0">Not here</option>' +
                        '<option value="1">Column 1</option>' +
                        '<option value="2">Column 2</option>' +
                    '</select>' +
                '</td>' +
                '<td class="csv_column_options import-field-details">' +
                    '<input type="checkbox" id="field_a_create" name="field_a_create">Create</input>' +
                '</td>' +
            '</tr></tbody>' +
        '</table>'
    ).appendTo(this.qunitFixture());

    element.find('.csv_col_select').val(initial);

    creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    // initial visible state : 0 => hidden, 1 => visible
    assert.equal(element.find('.csv_column_options').is(':not(.hidden)'), expected);

    // toggle state "not in csv" => not visible
    element.find('.csv_col_select').val('0').trigger('change');
    assert.equal(element.find('.csv_column_options.hidden').length, 1);

    // toggle state "Column 1" => visible
    element.find('.csv_col_select').val('1').trigger('change');
    assert.equal(element.find('.csv_column_options:not(.hidden)').length, 1);
});

}(jQuery));
