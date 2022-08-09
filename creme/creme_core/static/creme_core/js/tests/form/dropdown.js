
(function($) {

QUnit.module("creme.form.DropDown", new QUnitMixin(QUnitDialogMixin, {
    afterEach: function() {
        $('.ui-dropdown-hidden').dropdown('destroy');
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

QUnit.test('creme.form.DropDown (empty)', function() {
    var element = this.createSelect();
    var dropdown = new creme.form.DropDown(element);

    equal(true, element.is('.ui-dropdown-hidden'));
    equal(1, $('.ui-dropdown-selection').length);
    equal(element, dropdown.element());
});

QUnit.test('creme.form.DropDown (dropdown-alt)', function() {
    var element = this.createSelect().attr('data-dropdown-alt', 'This is a dropdown');
    var dropdown = new creme.form.DropDown(element);

    equal(true, element.is('.ui-dropdown-hidden'));
    equal('This is a dropdown', $('.ui-dropdown-selection').attr('title'));
    equal(element, dropdown.element());
});

QUnit.test('creme.form.DropDown (title)', function() {
    var element = this.createSelect().attr('data-dropdown-alt', 'This is a dropdown');
    var dropdown = new creme.form.DropDown(element, {
        title: 'Another title !'
    });

    equal('Another title !', $('.ui-dropdown-selection').attr('title'));
    equal(element, dropdown.element());
});

QUnit.test('creme.form.DropDown (auto)', function() {
    var element = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {value: 1, label: 'A'}
    ]);

    var dropdown = new creme.form.DropDown(element, {
        title: 'This is a dropdown'
    });

    var selection = $('.ui-dropdown-selection');

    equal(dropdown.val(), '5');
    equal('This is a dropdown', selection.attr('title'));
    equal('E', selection.text());

    this.assertClosedPopover();

    dropdown.select();

    // < 3 options : No popover
    equal(dropdown.val(), '1');
    equal('A', selection.text());
    this.assertClosedPopover();

    element.append('<option value="8">C</option>');

    dropdown.select();

    // 3 options : Popover !
    equal(dropdown.val(), '1');
    equal('A', selection.text());

    var popover = this.assertOpenedPopover();

    // Note : selected item is not ins the popover list
    equal(2, popover.find('.popover-list-item').length);

    // Select item C
    popover.find('.popover-list-item[data-value="8"]').trigger('click');

    equal(dropdown.val(), '8');
    equal('C', selection.text());
    this.assertClosedPopover();
});

QUnit.test('creme.form.DropDown (toggle)', function() {
    var element = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {value: 1, label: 'A'},
        {value: 8, label: 'C'}
    ]);

    var dropdown = new creme.form.DropDown(element, {
        mode: 'toggle'
    });

    var selection = $('.ui-dropdown-selection');

    equal(dropdown.val(), '5');
    equal('E', selection.text());

    dropdown.select();

    equal(dropdown.val(), '1');
    equal('A', selection.text());
    this.assertClosedPopover();

    dropdown.select();

    equal(dropdown.val(), '8');
    equal('C', selection.text());
    this.assertClosedPopover();

    // Loop on first selection
    dropdown.select();

    equal(dropdown.val(), '5');
    equal('E', selection.text());
    this.assertClosedPopover();
});

QUnit.test('creme.form.DropDown (popover)', function() {
    var element = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {value: 1, label: 'A'}
    ]);

    var dropdown = new creme.form.DropDown(element, {
        mode: 'popover'
    });

    var selection = $('.ui-dropdown-selection');

    equal(dropdown.val(), '5');
    equal('E', selection.text());

    dropdown.select();

    var popover = this.assertOpenedPopover();
    popover.find('.popover-list-item').trigger('click');

    equal(dropdown.val(), '1');
    equal('A', selection.text());
    this.assertClosedPopover();

    dropdown.select();

    popover = this.assertOpenedPopover();
    popover.find('.popover-list-item').trigger('click');

    equal(dropdown.val(), '5');
    equal('E', selection.text());
});

QUnit.test('creme.form.DropDown (jquery plugin)', function() {
    var element = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {value: 1, label: 'A'},
        {value: 8, label: 'C'}
    ]);

    var dropdown = element.dropdown({
        mode: 'toggle',
        title: 'This is a dropdown'
    });

    equal(element.dropdown('prop', 'mode'), 'toggle');
    equal(element.dropdown('instance'), dropdown);

    var selection = $('.ui-dropdown-selection');

    equal('5', element.val());
    equal('E', selection.text());
    equal('This is a dropdown', selection.attr('title'));

    element.dropdown('next');

    equal('1', element.val());
    equal('A', selection.text());

    selection.trigger('click');

    equal('8', element.val());
    equal('C', selection.text());
});

}(jQuery));
