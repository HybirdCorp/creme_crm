
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

QUnit.test('creme.form.DropDown (empty)', function(assert) {
    var element = this.createSelect();
    var dropdown = new creme.form.DropDown(element);

    assert.equal(true, element.is('.ui-dropdown-hidden'));
    assert.equal(1, $('.ui-dropdown-selection').length);
    assert.equal(element, dropdown.element());
});

QUnit.test('creme.form.DropDown (dropdown-alt)', function(assert) {
    var element = this.createSelect().attr('data-dropdown-alt', 'This is a dropdown');
    var dropdown = new creme.form.DropDown(element);

    assert.equal(true, element.is('.ui-dropdown-hidden'));
    assert.equal('This is a dropdown', $('.ui-dropdown-selection').attr('title'));
    assert.equal(element, dropdown.element());
});

QUnit.test('creme.form.DropDown (title)', function(assert) {
    var element = this.createSelect().attr('data-dropdown-alt', 'This is a dropdown');
    var dropdown = new creme.form.DropDown(element, {
        title: 'Another title !'
    });

    assert.equal('Another title !', $('.ui-dropdown-selection').attr('title'));
    assert.equal(element, dropdown.element());
});

QUnit.test('creme.form.DropDown (auto)', function(assert) {
    var element = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {value: 1, label: 'A'}
    ]);

    var dropdown = new creme.form.DropDown(element, {
        title: 'This is a dropdown'
    });

    var selection = $('.ui-dropdown-selection');

    assert.equal(dropdown.val(), '5');
    assert.equal('This is a dropdown', selection.attr('title'));
    assert.equal('E', selection.text());

    this.assertClosedPopover();

    dropdown.select();

    // < 3 options : No popover
    assert.equal(dropdown.val(), '1');
    assert.equal('A', selection.text());
    this.assertClosedPopover();

    element.append('<option value="8">C</option>');

    dropdown.select();

    // 3 options : Popover !
    assert.equal(dropdown.val(), '1');
    assert.equal('A', selection.text());

    var popover = this.assertOpenedPopover();

    // Note : selected item is not ins the popover list
    assert.equal(2, popover.find('.popover-list-item').length);

    // Select item C
    popover.find('.popover-list-item[data-value="8"]').trigger('click');

    assert.equal(dropdown.val(), '8');
    assert.equal('C', selection.text());
    this.assertClosedPopover();
});

QUnit.test('creme.form.DropDown (toggle)', function(assert) {
    var element = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {value: 1, label: 'A'},
        {value: 8, label: 'C'}
    ]);

    var dropdown = new creme.form.DropDown(element, {
        mode: 'toggle'
    });

    var selection = $('.ui-dropdown-selection');

    assert.equal(dropdown.val(), '5');
    assert.equal('E', selection.text());

    dropdown.select();

    assert.equal(dropdown.val(), '1');
    assert.equal('A', selection.text());
    this.assertClosedPopover();

    dropdown.select();

    assert.equal(dropdown.val(), '8');
    assert.equal('C', selection.text());
    this.assertClosedPopover();

    // Loop on first selection
    dropdown.select();

    assert.equal(dropdown.val(), '5');
    assert.equal('E', selection.text());
    this.assertClosedPopover();
});

QUnit.test('creme.form.DropDown (popover)', function(assert) {
    var element = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {value: 1, label: 'A'}
    ]);

    var dropdown = new creme.form.DropDown(element, {
        mode: 'popover'
    });

    var selection = $('.ui-dropdown-selection');

    assert.equal(dropdown.val(), '5');
    assert.equal('E', selection.text());

    dropdown.select();

    var popover = this.assertOpenedPopover();
    popover.find('.popover-list-item').trigger('click');

    assert.equal(dropdown.val(), '1');
    assert.equal('A', selection.text());
    this.assertClosedPopover();

    dropdown.select();

    popover = this.assertOpenedPopover();
    popover.find('.popover-list-item').trigger('click');

    assert.equal(dropdown.val(), '5');
    assert.equal('E', selection.text());
});

QUnit.test('creme.form.DropDown (jquery plugin)', function(assert) {
    var element = this.createSelect([
        {value: 5, label: 'E', selected: true},
        {value: 1, label: 'A'},
        {value: 8, label: 'C'}
    ]);

    var dropdown = element.dropdown({
        mode: 'toggle',
        title: 'This is a dropdown'
    });

    assert.equal(element.dropdown('prop', 'mode'), 'toggle');
    assert.equal(element.dropdown('instance'), dropdown);

    var selection = $('.ui-dropdown-selection');

    assert.equal('5', element.val());
    assert.equal('E', selection.text());
    assert.equal('This is a dropdown', selection.attr('title'));

    element.dropdown('next');

    assert.equal('1', element.val());
    assert.equal('A', selection.text());

    selection.trigger('click');

    assert.equal('8', element.val());
    assert.equal('C', selection.text());
});

}(jQuery));
