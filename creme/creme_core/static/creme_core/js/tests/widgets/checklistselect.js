(function($) {
"use strict";

QUnit.module("creme.widgets.checklistselect.js", new QUnitMixin(QUnitEventMixin, {
    createCheckListSelectElement: function(options, noauto, nodelegate) {
        var options = options || {}
        var select = $('<div widget="ui-creme-checklistselect" class="ui-creme-checklistselect ui-creme-widget"/>');

        select.append($('<div class="checklist-header">' +
                            '<a type="button" class="checklist-check-all">Select All</a>' +
                            '<a type="button" class="checklist-check-none">Unselect All</a>' +
                        '</div>'));
        select.append($('<div class="checklist-counter"/>'));
        select.append($('<div class="checklist-content"/>'));

        if (!nodelegate)
            select.append($('<select class="ui-creme-input" multiple/>'));

        for(var key in options) {
            select.attr(key, options[key]);
        }

        select.toggleClass('widget-auto', !noauto);
        return select;
    },

    addCheckListSelectChoice: function(element, label, value) {
        var choice = $('<option value="' + (value.replace ? value.replace(/\"/g, '&quot;') : value) + '">' + label + '</option>');
        $('select.ui-creme-input', element).append(choice);
        return choice;
    },

    addCheckListSelectSearch: function(element, mode) {
        mode = mode || 'filter';
        $('.checklist-header', element).append('<input type="search" class="checklist-filter">');
        $('.checklist-content', element).addClass(mode);
    },

    assertCheckListEntries: function(element, expected) {
        var options = $('.checkbox-field', element);

        equal(options.length, expected.length, 'checkbox count');

        options.each(function(index) {
            var expected_entry = expected[index];
            var input = $('input[type="checkbox"]', this);
            var label = $('.checkbox-label', this);
            var is_visible = expected_entry.visible !== undefined ? expected_entry.visible : true;

            var expected_label = ('<span class=\"checkbox-label-text\"%s>%s</span>' +
                                  '<span class=\"checkbox-label-help\"%s></span>').format(expected_entry.disabled ? ' disabled=""' : '',
                                                                                          expected_entry.label,
                                                                                          expected_entry.disabled ? ' disabled=""' : '');

            equal(label.html(), expected_label, 'checkbox %d label'.format(index));

            equal(input.val(), expected_entry.value, 'checkbox %d value'.format(index));
            equal(input.is('[disabled]'), expected_entry.disabled || false, 'checkbox %d disabled status'.format(index));
            equal(input.get()[0].checked, expected_entry.selected || false, 'checkbox %d check status'.format(index));
            equal($(this).is('.hidden'), !is_visible, 'checkbox %d visible status'.format(index));
        });
    }
}));

QUnit.test('creme.widget.CheckListSelect.create (no delegate)', function(assert) {
    var element = this.createCheckListSelectElement({}, false, true);
    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal(0, widget.delegate._delegate(element).length);

    equal(0, widget.model().length());
    equal(0, $('input[type="checkbox"]', widget.content()).length);
});

QUnit.test('creme.widget.CheckListSelect.create (delegate)', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 1);

    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal(1, widget.delegate._delegate(element).length);
    equal(false, widget.disabled());

    deepEqual([{label:'item1', value:"12", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false},
               {label:'item2', value:"78", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false},
               {label:'item3', value:"1",  group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false}], widget.model().all());

    this.assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12'},
                            {label:'item2', value:'78'},
                            {label:'item3', value:'1'}])
});

QUnit.test('creme.widget.CheckListSelect.create (disabled)', function(assert) {
    var element = this.createCheckListSelectElement({disabled:true});
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 1);

    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal(1, widget.delegate._delegate(element).length);
    equal(true, widget.disabled());

    deepEqual([{label:'item1', value:"12", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false},
               {label:'item2', value:"78", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false},
               {label:'item3', value:"1",  group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false}], widget.model().all());

    this.assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', disabled:true},
                            {label:'item2', value:'78', disabled:true},
                            {label:'item3', value:'1',  disabled:true}]);
});

QUnit.test('creme.widget.CheckListSelect.create (initial value)', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 1);
    $('select', element).val(['12', '1']);

    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);
    equal(false, widget.disabled());

    deepEqual([{label:'item1', value:"12", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:true},
               {label:'item2', value:"78", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false},
               {label:'item3', value:"1",  group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:true}], widget.model().all());

    this.assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:true},
                            {label:'item2', value:'78', selected:false},
                            {label:'item3', value:'1',  selected:true}]);

    deepEqual(['12', '1'], widget.val());
});

QUnit.test('creme.widget.CheckListSelect.disable', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);

    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);
    equal(false, widget.disabled());

    deepEqual([{label:'item1', value:"12", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false},
               {label:'item2', value:"78", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false}], widget.model().all());

    this.assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', disabled:false},
                            {label:'item2', value:'78', disabled:false}]);

    widget.disabled(true);

    equal(true, widget.disabled());

    deepEqual([{label:'item1', value:"12", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false},
               {label:'item2', value:"78", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false}], widget.model().all());

    this.assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', disabled:true},
                            {label:'item2', value:'78', disabled:true}]);
});

QUnit.test('creme.widget.CheckListSelect.val', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    deepEqual([{label:'item1', value:"12", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false},
               {label:'item2', value:"78", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false},
               {label:'item3', value:"5",  group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:false},
                            {label:'item2', value:'78', selected:false},
                            {label:'item3', value:'5',  selected:false}]);
    equal(null, widget.val());

    widget.val(["12", "5"]);

    deepEqual([{label:'item1', value:"12", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:true},
               {label:'item2', value:"78", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false},
               {label:'item3', value:"5",  group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:true}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:true},
                            {label:'item2', value:'78', selected:false},
                            {label:'item3', value:'5',  selected:true}]);
});

QUnit.test('creme.widget.CheckListSelect.val (select / unselect)', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    deepEqual([{label:'item1', value:"12", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false},
               {label:'item2', value:"78", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false},
               {label:'item3', value:"5",  group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:false},
                            {label:'item2', value:'78', selected:false},
                            {label:'item3', value:'5',  selected:false}]);
    equal(null, widget.val());

    $('input[type="checkbox"][value="12"]', widget.content()).prop('checked', true).change();

    deepEqual([{label:'item1', value:"12", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:true},
               {label:'item2', value:"78", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false},
               {label:'item3', value:"5",  group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:true},
                            {label:'item2', value:'78', selected:false},
                            {label:'item3', value:'5',  selected:false}]);
    deepEqual(["12"], widget.val());

    $('input[type="checkbox"][value="12"]', widget.content()).prop('checked', false).change();
    $('input[type="checkbox"][value="5"]', widget.content()).prop('checked', true).change();

    deepEqual([{label:'item1', value:"12", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false},
               {label:'item2', value:"78", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false},
               {label:'item3', value:"5",  group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:true}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:false},
                            {label:'item2', value:'78', selected:false},
                            {label:'item3', value:'5',  selected:true}]);
    deepEqual(["5"], widget.val());
});

QUnit.test('creme.widget.CheckListSelect.selectAll', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    this.assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:false},
                            {label:'item2', value:'78', selected:false},
                            {label:'item3', value:'5',  selected:false}]);
    equal(null, widget.val());

    widget.selectAll();

    deepEqual([{label:'item1', value:"12", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:true},
               {label:'item2', value:"78", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:true},
               {label:'item3', value:"5",  group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:true}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:true},
                            {label:'item2', value:'78', selected:true},
                            {label:'item3', value:'5',  selected:true}]);

    deepEqual(["12", "78", "5"], widget.val());
});

QUnit.test('creme.widget.CheckListSelect.selectAll (disabled options)', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78).attr('disabled', 'disabled');
    this.addCheckListSelectChoice(element, 'item3', 5);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    this.assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:false},
                            {label:'item2', value:'78', selected:false, disabled:true},
                            {label:'item3', value:'5',  selected:false}]);
    equal(null, widget.val());

    widget.selectAll();

    deepEqual([{label:'item1', value:"12", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:true},
               {label:'item2', value:"78", group: undefined, help: undefined, disabled:true, visible:true, tags:[], selected:false},
               {label:'item3', value:"5",  group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:true}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:true},
                            {label:'item2', value:'78', selected:false, disabled:true},
                            {label:'item3', value:'5',  selected:true}]);

    deepEqual(["12", "5"], widget.val());
});

QUnit.test('creme.widget.CheckListSelect.unselectAll', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);
    $('select', element).val(['12', '5']);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    this.assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:true},
                            {label:'item2', value:'78', selected:false},
                            {label:'item3', value:'5',  selected:true}]);
    deepEqual(['12', '5'], widget.val());

    widget.unselectAll();

    deepEqual([{label:'item1', value:"12", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false},
               {label:'item2', value:"78", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false},
               {label:'item3', value:"5",  group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:false},
                            {label:'item2', value:'78', selected:false},
                            {label:'item3', value:'5',  selected:false}]);

    deepEqual(null, widget.val());
});

QUnit.test('creme.widget.CheckListSelect.reset', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);
    $('select', element).val(['12', '5']);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    this.assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:true},
                            {label:'item2', value:'78', selected:false},
                            {label:'item3', value:'5',  selected:true}]);
    deepEqual(['12', '5'], widget.val());

    widget.reset();

    deepEqual([{label:'item1', value:"12", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false},
               {label:'item2', value:"78", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false},
               {label:'item3', value:"5",  group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:false},
                            {label:'item2', value:'78', selected:false},
                            {label:'item3', value:'5',  selected:false}]);

    deepEqual(null, widget.val());
});

QUnit.test('creme.widget.CheckListSelect.filter', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectSearch(element, 'filter');
    this.addCheckListSelectChoice(element, 'itemAD', 12);
    this.addCheckListSelectChoice(element, 'itemAB', 78);
    this.addCheckListSelectChoice(element, 'itemABC', 5);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    deepEqual([{label:'itemAD',   value:"12", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false},
               {label:'itemAB',  value:"78", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false},
               {label:'itemABC', value:"5",  group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false}], widget.model().all());

    element.find('.checklist-filter').val('B').trigger($.Event("keyup", {keyCode: 13}));

    deepEqual([{label:'itemAD',   value:"12", group: undefined, help: undefined, disabled:false, visible:false, tags:[], selected:false},
               {label:'itemAB',  value:"78", group: undefined, help: undefined, disabled:false, visible:true,  tags:[], selected:false},
               {label:'itemABC', value:"5",  group: undefined, help: undefined, disabled:false, visible:true,  tags:[], selected:false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
            [{label:'itemAD', value:'12', disabled: false, visible: false},
             {label:'itemAB', value:'78', disabled: false, visible: true},
             {label:'itemABC', value:'5',  disabled: false, visible: true}]);

    element.find('.checklist-filter').val('BC').trigger($.Event("keyup", {keyCode: 13}));

    deepEqual([{label:'itemAD',   value:"12", group: undefined, help: undefined, disabled:false, visible:false, tags:[], selected:false},
               {label:'itemAB',  value:"78", group: undefined, help: undefined, disabled:false, visible:false, tags:[], selected:false},
               {label:'itemABC', value:"5",  group: undefined, help: undefined, disabled:false, visible:true,  tags:[], selected:false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
            [{label:'itemAD', value:'12', disabled: false, visible: false},
             {label:'itemAB', value:'78', disabled: false, visible: false},
             {label:'itemABC', value:'5',  disabled: false, visible: true}]);

    element.find('.checklist-filter').val('D').trigger($.Event("keyup", {keyCode: 13}));

    deepEqual([{label:'itemAD',  value:"12", group: undefined, help: undefined, disabled:false, visible:true,  tags:[], selected:false},
               {label:'itemAB',  value:"78", group: undefined, help: undefined, disabled:false, visible:false, tags:[], selected:false},
               {label:'itemABC', value:"5",  group: undefined, help: undefined, disabled:false, visible:false, tags:[], selected:false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
            [{label:'itemAD', value:'12', disabled: false, visible: true},
             {label:'itemAB', value:'78', disabled: false, visible: false},
             {label:'itemABC', value:'5',  disabled: false, visible: false}]);
});

QUnit.test('creme.widget.CheckListSelect.search', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectSearch(element, 'search');
    this.addCheckListSelectChoice(element, 'itemAD', 12);
    this.addCheckListSelectChoice(element, 'itemAB', 78);
    this.addCheckListSelectChoice(element, 'itemABC', 5);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    deepEqual([{label:'itemAD',   value:"12", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false},
               {label:'itemAB',  value:"78", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false},
               {label:'itemABC', value:"5",  group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false}], widget.model().all());

    element.find('.checklist-filter').val('B').trigger($.Event("keyup", {keyCode: 13}));

    deepEqual([{label:'itemAD',   value:"12", group: undefined, help: undefined, disabled:true,  visible:true, tags:[], selected:false},
               {label:'itemAB',  value:"78", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false},
               {label:'itemABC', value:"5",  group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
            [{label:'itemAD', value:'12', disabled: true, visible: true},
             {label:'itemAB', value:'78', disabled: false, visible: true},
             {label:'itemABC', value:'5',  disabled: false, visible: true}]);

    element.find('.checklist-filter').val('BC').trigger($.Event("keyup", {keyCode: 13}));

    deepEqual([{label:'itemAD',   value:"12", group: undefined, help: undefined, disabled:true,  visible:true, tags:[], selected:false},
               {label:'itemAB',  value:"78", group: undefined, help: undefined, disabled:true,  visible:true, tags:[], selected:false},
               {label:'itemABC', value:"5",  group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
            [{label:'itemAD', value:'12', disabled: true, visible: true},
             {label:'itemAB', value:'78', disabled: true, visible: true},
             {label:'itemABC', value:'5',  disabled: false, visible: true}]);

    element.find('.checklist-filter').val('D').trigger($.Event("keyup", {keyCode: 13}));

    deepEqual([{label:'itemAD',  value:"12", group: undefined, help: undefined, disabled:false, visible:true, tags:[], selected:false},
               {label:'itemAB',  value:"78", group: undefined, help: undefined, disabled:true,  visible:true, tags:[], selected:false},
               {label:'itemABC', value:"5",  group: undefined, help: undefined, disabled:true,  visible:true, tags:[], selected:false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
            [{label:'itemAD', value:'12', disabled: false, visible: true},
             {label:'itemAB', value:'78', disabled: true, visible: true},
             {label:'itemABC', value:'5',  disabled: true, visible: true}]);
});

}(jQuery));
