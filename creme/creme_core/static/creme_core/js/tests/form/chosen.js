
(function($) {

QUnit.module("creme.chosen.js", new QUnitMixin({
    afterEach: function() {
        $('.chzn-drop').detach();
    },

    createSelect: function(options) {
        options = options || [];

        var select = $('<select></select>').appendTo(this.qunitFixture());
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

QUnit.test('creme.form.Chosen.activate (empty)', function() {
    var select = this.createSelect();
    var chosen = new creme.form.Chosen();

    equal(false, select.is('.chzn-select'));
    equal(false, chosen.isActive());
    equal(undefined, chosen.element);

    chosen.activate(select);

    equal(true, select.is('.chzn-select'));
    equal(true, chosen.isActive());
    equal(select, chosen.element);
});

QUnit.test('creme.form.Chosen.activate (already activated)', function() {
    var select = this.createSelect([{value: 1, label: 'A'}]);
    var chosen = new creme.form.Chosen();

    chosen.activate(select);

    this.assertRaises(function() {
        chosen.activate(select);
    }, Error, 'Error: Chosen component is already active');
});


QUnit.test('creme.form.Chosen.activate (single)', function() {
    var select = this.createSelect([{value: 5, label: 'E', selected: true}, {value: 1, label: 'A'}]);
    var chosen = new creme.form.Chosen();

    chosen.activate(select);
    equal('E', select.parent().find('.chzn-single span').text());
});

QUnit.test('creme.form.Chosen.activate (multiple)', function() {
    var select = this.createSelect([{value: 5, label: 'E', selected: true}, {value: 1, label: 'A', selected: true}]);
    var chosen = new creme.form.Chosen({multiple: true});

    select.attr('multiple', '');
    select.val([5, 1]);

    chosen.activate(select);
    equal(2, select.parent().find('ul.chzn-choices .search-choice').length);
    equal(0, select.parent().find('ul.chzn-choices.ui-sortable').length); // not sortable
});

QUnit.test('creme.form.Chosen.activate (multiple, sortable)', function() {
    var select = this.createSelect([{value: 5, label: 'E', selected: true}, {value: 1, label: 'A', selected: true}]);
    var chosen = new creme.form.Chosen({multiple: true, sortable: true});

    select.attr('multiple', '');
    select.val([5, 1]);

    chosen.activate(select);

    equal(2, select.parent().find('ul.chzn-choices .search-choice').length);
    equal(1, select.parent().find('ul.chzn-choices.ui-sortable').length); // sortable
});

QUnit.test('creme.form.Chosen.refresh', function() {
    var select = this.createSelect([{value: 5, label: 'E', selected: true}, {value: 1, label: 'A'}]);
    var chosen = new creme.form.Chosen();

    chosen.activate(select);
    equal('E', select.parent().find('.chzn-single span').text());
    equal(2, $('.chzn-drop .chzn-results li').length);

    this.addSelectOption(select, {value: 8, label: 'G'});
    this.addSelectOption(select, {value: 2, label: 'B'});
    this.addSelectOption(select, {value: 3, label: 'C'});

    chosen.refresh();
    equal(5, $('.chzn-drop .chzn-results li').length);
});

QUnit.test('creme.form.Chosen.deactivate', function() {
    var select = this.createSelect([{value: 5, label: 'E', selected: true}, {value: 1, label: 'A'}]);
    var chosen = new creme.form.Chosen();

    chosen.activate(select);

    equal(true, select.is('.chzn-select'));
    equal(true, chosen.isActive());
    equal(select, chosen.element);
    equal('E', select.parent().find('.chzn-single span').text());

    chosen.deactivate(select);

    equal(false, select.is('.chzn-select'));
    equal(false, chosen.isActive());
    equal(undefined, chosen.element);
    equal(0, select.parent().find('.chzn-single span').length);
});

QUnit.test('creme.form.Chosen.deactivate (sortable)', function() {
    var select = this.createSelect([{value: 5, label: 'E', selected: true}, {value: 1, label: 'A'}]);
    var chosen = new creme.form.Chosen({multiple: true, sortable: true});

    select.attr('multiple', '');
    select.val([1, 5]);

    chosen.activate(select);

    equal(true, select.is('.chzn-select'));
    equal(true, chosen.isActive());
    equal(select, chosen.element);
    equal(2, select.parent().find('ul.chzn-choices .search-choice').length);
    equal(1, select.parent().find('ul.chzn-choices.ui-sortable').length); // sortable

    chosen.deactivate(select);

    equal(false, select.is('.chzn-select'));
    equal(false, chosen.isActive());
    equal(undefined, chosen.element);
    equal(0, select.parent().find('ul.chzn-choices').length);
});

QUnit.test('creme.form.Chosen.deactivate (already deactivated)', function() {
    var select = this.createSelect([{value: 5, label: 'E', selected: true}, {value: 1, label: 'A'}]);
    var chosen = new creme.form.Chosen();

    chosen.activate(select);

    equal(true, select.is('.chzn-select'));
    equal(true, chosen.isActive());
    equal('E', select.parent().find('.chzn-single span').text());

    chosen.deactivate(select);
    chosen.deactivate(select);
    chosen.deactivate(select);

    equal(false, select.is('.chzn-select'));
    equal(false, chosen.isActive());
    equal(0, select.parent().find('.chzn-single span').length);
});

}(jQuery));
