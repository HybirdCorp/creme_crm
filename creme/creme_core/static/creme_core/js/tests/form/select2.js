
(function($) {

QUnit.module("creme.form.Select2", new QUnitMixin({
    afterEach: function() {
        $('.select2-hidden-accessible').select2('destroy');
        $('.select2-container').remove();
    },

    createSelect: function(options) {
        options = options || [];

        var select = $('<select></select>').appendTo(this.qunitFixture('field'));
        var add = this.addSelectOption.bind(this);

        options.forEach(function(option) {
            add(select, option);
        });

        return select;
    },

    addSelectOption: function(select, option) {
        select.append('<option value="${value}" ${disabled} ${selected}>${label}</option>'.template({
            value: option.value,
            label: option.label,
            disabled: option.disabled ? 'disabled' : '',
            selected: option.selected ? 'selected' : ''
        }));
    }
}));

QUnit.test('creme.form.Select2.bind (empty)', function() {
    var select = this.createSelect();
    var select2 = new creme.form.Select2();

    equal(false, select.is('.select2-hidden-accessible'));
    equal(false, select2.isBound());
    equal(undefined, select2.element);

    select2.bind(select);

    equal(true, select.is('.select2-hidden-accessible'));
    equal(true, select2.isBound());
    equal(select, select2.element);
});

QUnit.test('creme.form.Select2.bind (already activated)', function() {
    var select = this.createSelect([{value: 1, label: 'A'}]);
    var select2 = new creme.form.Select2();

    select2.bind(select);

    this.assertRaises(function() {
        select2.bind(select);
    }, Error, 'Error: Select2 instance is already active');
});


QUnit.test('creme.form.Select2.bind (single)', function() {
    var select = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {value: 1, label: 'A'}
    ]);

    var select2 = new creme.form.Select2();

    select2.bind(select);

    equal('E', select.next('.select2').find('.select2-selection__rendered').text());
});

QUnit.test('creme.form.Select2.bind (multiple)', function() {
    var select = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {value: 1, label: 'A', selected: true}
    ]);

    var select2 = new creme.form.Select2({multiple: true});

    deepEqual({
        multiple: true,
        sortable: false,
        clearable: false,
        noResults: gettext("No result")
    }, select2.options());

    select.attr('multiple', '');
    select.val([5, 1]);

    select2.bind(select);

    equal(2, select.next('.select2').find('.select2-selection__choice').length);
    equal(false, select.parent().is('.ui-sortable'), 'is NOT sortable'); // not sortable

    equal(0, $('.select2-dropdown .select2-results__option').length);
    select.select2('open');
    equal(2, $('.select2-dropdown .select2-results__option').length);
});

QUnit.test('creme.form.Select2.bind (multiple, sortable)', function() {
    var select = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {value: 1, label: 'A', selected: true}
    ]);

    var select2 = new creme.form.Select2({multiple: true, sortable: true});

    select.attr('multiple', '');
    select.val([5, 1]);

    select2.bind(select);

    equal(2, select.next('.select2').find('.select2-selection__choice').length);
    equal(true, select.parent().is('.ui-sortable'), 'is sortable'); // sortable

    equal(0, $('.select2-dropdown .select2-results__option').length);
    select.select2('open');
    equal(2, $('.select2-dropdown .select2-results__option').length);
});

QUnit.test('creme.form.Select2.refresh', function() {
    var select = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {value: 1, label: 'A'}
    ]);

    var select2 = new creme.form.Select2();

    select2.bind(select);

    equal('E', select.next('.select2').find('.select2-selection__rendered').text());

    select.select2('open');
    equal(2, $('.select2-dropdown .select2-results__option').length);

    select.select2('close');

    this.addSelectOption(select, {value: 8, label: 'G'});
    this.addSelectOption(select, {value: 2, label: 'B', selected: true});
    this.addSelectOption(select, {value: 3, label: 'C'});

    select2.refresh();

    equal('B', select.next('.select2').find('.select2-selection__rendered').text());

    select.select2('open');
    equal(5, $('.select2-dropdown .select2-results__option').length);
});

QUnit.test('creme.form.Select2.refresh (replace)', function() {
    var select = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {value: 1, label: 'A'}
    ]);

    var select2 = new creme.form.Select2();

    select2.bind(select);

    equal('E', select.next('.select2').find('.select2-selection__rendered').text());

    select.select2('open');
    equal(2, $('.select2-dropdown .select2-results__option').length);

    select.select2('close');

    select.find('option').remove();
    this.addSelectOption(select, {value: 8, label: 'G'});
    this.addSelectOption(select, {value: 2, label: 'B', selected: true});
    this.addSelectOption(select, {value: 3, label: 'C'});

    select2.refresh();

    equal('B', select.next('.select2').find('.select2-selection__rendered').text());

    select.select2('open');
    equal(3, $('.select2-dropdown .select2-results__option').length);
});

QUnit.test('creme.form.Select2.unbind', function() {
    var select = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {value: 1, label: 'A'}
    ]);

    var select2 = new creme.form.Select2();

    select2.bind(select);

    equal(true, select.is('.select2-hidden-accessible'));
    equal(true, select2.isBound());
    equal(select, select2.element);
    equal('E', select.next('.select2').find('.select2-selection__rendered').text());

    select2.unbind(select);

    equal(false, select.is('.select2-hidden-accessible'));
    equal(false, select2.isBound());
    equal(undefined, select2.element);
    equal('', select.next('.select2').find('.select2-selection__rendered').text());
});

QUnit.test('creme.form.Select2.unbind (sortable)', function() {
    var select = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {value: 1, label: 'A'}
    ]);

    var select2 = new creme.form.Select2({multiple: true, sortable: true});

    select.attr('multiple', '');
    select.val([1, 5]);

    select2.bind(select);

    equal(true, select.is('.select2-hidden-accessible'));
    equal(true, select2.isBound());
    equal(select, select2.element);
    equal(true, select.parent().is('.ui-sortable')); // sortable

    equal(0, $('.select2-dropdown .select2-results__option').length);
    select.select2('open');
    equal(2, $('.select2-dropdown .select2-results__option').length);

    select2.unbind(select);

    equal(false, select.is('.select2-hidden-accessible'));
    equal(false, select2.isBound());
    equal(undefined, select2.element);
    equal(0, $('.select2-dropdown .select2-results__option').length);
    equal(false, select.parent().is('.ui-sortable')); // sortable
});

QUnit.test('creme.form.Select2.unbind (already deactivated)', function() {
    var select = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {value: 1, label: 'A'}
    ]).appendTo(this.qunitFixture('field'));
    var select2 = new creme.form.Select2();

    select2.bind(select);

    equal(true, select.is('.select2-hidden-accessible'));
    equal(true, select2.isBound());
    equal('E', select.next('.select2').find('.select2-selection__rendered').text());

    select2.unbind(select);
    select2.unbind(select);
    select2.unbind(select);

    equal(false, select.is('.select2-hidden-accessible'));
    equal(false, select2.isBound());
    equal('', select.next('.select2').find('.select2-selection__rendered').text());
});

}(jQuery));
