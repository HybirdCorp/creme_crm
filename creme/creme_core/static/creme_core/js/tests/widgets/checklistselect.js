(function($) {
"use strict";

QUnit.module("creme.widgets.checklistselect.js", new QUnitMixin(QUnitEventMixin,
                                                                QUnitAjaxMixin,
                                                                QUnitDialogMixin, {
    beforeEach: function() {
        var backend = this.backend;

        this.setMockBackendGET({
            'mock/items/create': backend.response(200, '<form></form>')
        });

        this.setMockBackendPOST({
            'mock/items/create': backend.responseJSON(200, {
                                              added: [
                                                  ['A1', 'Item A1'],
                                                  ['A2', 'Item A2']
                                              ]
                                          })
        });
    },

    createCheckListSelectElement: function(options) {
        options = $.extend({
            less: false,
            createUrl: 'mock/items/create',
            delegate: '<select class="ui-creme-input" multiple></select>',
            attrs: {},
//            auto: true,
//            disabled: false
            auto: true
        }, options || {});

        var html = (
//                '<div widget="ui-creme-checklistselect" class="ui-creme-checklistselect ui-creme-widget" ${disabled}>' +
                '<div widget="ui-creme-checklistselect" class="ui-creme-checklistselect ui-creme-widget">' +
                    '${delegate}' +
                    '<div class="checklist-header">' +
                        '<a type="button" class="checklist-check-all">Select All</a>' +
                        '<a type="button" class="checklist-check-none">Unselect All</a>' +
                        '<a type="button" class="checklist-create" href="${createUrl}">Create</a>' +
                    '</div>' +
                    '<div class="checklist-counter"></div>' +
                    '<div class="checklist-body">' +
                        '<div class="checklist-content"/>' +
                    '</div>' +
                '</div>'
            ).template({
                createUrl: options.createUrl,
//                delegate: options.delegate,
//                disabled: options.disabled ? 'disabled' : ''
                delegate: options.delegate
            });

        var select = $(html);

        for (var key in options.attrs) {
            select.attr(key, options[key]);
        }

        if (options.less) {
            select.attr('less', options.less === true ? '' : options.less);
            select.append($('<div class="checklist-footer"><a class="checklist-toggle-less">More</a></div>'));
        }

        select.toggleClass('widget-auto', options.auto);
        return select;
    },

    addCheckListSelectChoice: function(element, label, value, options) {
        options = options || {};

        var choice = $((
                '<option value="${value}" ${disabled} ${readonly} ${selected}>${label}</option>'
            ).template({
                value: (value.replace ? value.replace(/\"/g, '&quot;') : value),
                label: label,
                disabled: options.disabled ? 'disabled' : '',
                readonly: options.readonly ? 'readonly' : '',
                selected: options.selected ? 'selected' : ''
            }));

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
        var equalHtml = this.equalHtml.bind(this);

        equal(options.length, expected.length, 'checkbox count');

        options.each(function(index) {
            var expected_entry = expected[index];
            var input = $('input[type="checkbox"]', this);
            var label = $('.checkbox-label', this);
            var is_visible = expected_entry.visible !== undefined ? expected_entry.visible : true;

            var expected_label = (
                    '<span class=\"checkbox-label-text\" ${disabled}>${label}</span>' +
                    '<span class=\"checkbox-label-help\" ${disabled}></span>'
                ).template({
                     disabled: expected_entry.disabled ? 'disabled' : '',
                     label: expected_entry.label
                });

            equalHtml(expected_label, label, 'checkbox %d label'.format(index));

            equal(input.val(), expected_entry.value, 'checkbox %d value'.format(index));
            equal(input.is('[disabled]'), expected_entry.disabled || false, 'checkbox %d disabled status'.format(index));
            equal($(this).is('[readonly]'), expected_entry.readonly || false, 'checkbox %d readonly status'.format(index));
            equal(input.get()[0].checked, expected_entry.selected || false, 'checkbox %d check status'.format(index));
            equal($(this).is('.hidden'), !is_visible, 'checkbox %d visible status'.format(index));
        });
    }
}));

QUnit.test('creme.widget.CheckListSelect.create (no delegate)', function(assert) {
    var element = this.createCheckListSelectElement({delegate: ''});
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
    deepEqual([], widget.dependencies());

    deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "1",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());

    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12'},
                            {label: 'item2', value: '78'},
                            {label: 'item3', value: '1'}]);
});

QUnit.test('creme.widget.CheckListSelect.create (disabled)', function(assert) {
//    var element = this.createCheckListSelectElement({disabled: true});
    var element = this.createCheckListSelectElement({
        delegate: '<select class="ui-creme-input" multiple disabled></select>'
    });
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 1);

    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);
    equal(element.hasClass('is-disabled'), true);

    equal(1, widget.delegate._delegate(element).length);
    equal(true, widget.disabled());
    deepEqual([], widget.val());
    deepEqual([], widget.selected());

    deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "1",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());

    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', disabled: true},
                            {label: 'item2', value: '78', disabled: true},
                            {label: 'item3', value: '1',  disabled: true}]);

    widget.selectAll();
    deepEqual([], widget.selected());

    element.find('.checklist-check-all').trigger('click');
    deepEqual([], widget.selected());

    widget.val(['12', '1']);
    deepEqual(['12', '1'], widget.selected());

    widget.unselectAll();
    deepEqual(['12', '1'], widget.selected());

    element.find('.checklist-check-none').trigger('click');
    deepEqual(['12', '1'], widget.selected());

    element.find('.checklist-create').trigger('click');
    this.assertClosedDialog();
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
    equal(element.hasClass('is-disabled'), false);

    deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "1",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true}], widget.model().all());

    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: true},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '1',  selected: true}]);

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

    deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());

    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', disabled: false},
                            {label: 'item2', value: '78', disabled: false}]);

    widget.disabled(true);

    equal(true, widget.disabled());

    deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());

    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', disabled: true},
                            {label: 'item2', value: '78', disabled: true}]);
});

QUnit.test('creme.widget.CheckListSelect.val (required)', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    var input = element.find('select');

    deepEqual([], widget.val());
    equal(false, element.is('.is-field-invalid'));

    // not required
    creme.forms.validateHtml5Field(input);
    equal(false, element.is('.is-field-invalid'));

    element.find('select').attr('required', '');

    // required
    creme.forms.validateHtml5Field(input);
    equal(true, element.is('.is-field-invalid'));

    widget.val(['12']);

    creme.forms.validateHtml5Field(input);
    equal(false, element.is('.is-field-invalid'));
});

QUnit.test('creme.widget.CheckListSelect.val', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    var counter = element.find('.checklist-counter');

    equal('&nbsp;', counter.html());
    deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: false}]);
    deepEqual([], widget.val());

    widget.val(["12", "5"]);

    equal(ngettext('%d selection', '%d selections', 2).format(2) + '&nbsp;', counter.html());
    deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: true},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: true}]);
});

QUnit.test('creme.widget.CheckListSelect.val (select / unselect)', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    var counter = element.find('.checklist-counter');

    equal('&nbsp;', counter.html());
    deepEqual([], widget.val());
    deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: false}]);

    $('input[type="checkbox"][value="12"]', widget.content()).prop('checked', true).trigger('change');

    equal(ngettext('%d selection', '%d selections', 1).format(1) + '&nbsp;', counter.html());
    deepEqual(["12"], widget.val());

    deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: true},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: false}]);

    $('input[type="checkbox"][value="12"]', widget.content()).prop('checked', false).trigger('change');
    $('input[type="checkbox"][value="5"]', widget.content()).prop('checked', true).trigger('change');

    equal(ngettext('%d selection', '%d selections', 1).format(1) + '&nbsp;', counter.html());
    deepEqual(["5"], widget.val());

    deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: true}]);
});

QUnit.test('creme.widget.CheckListSelect.val (select / unselect, click on label)', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: false}]);
    deepEqual([], widget.val());

    element.find('.checkbox-field[checklist-index="0"] .checkbox-label').trigger('click');

    deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: true},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: false}]);
    deepEqual(["12"], widget.val());

    element.find('.checkbox-field[checklist-index="0"] .checkbox-label').trigger('click');  // toggle => unselect
    element.find('.checkbox-field[checklist-index="2"] .checkbox-label').trigger('click');

    deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: true}]);
    deepEqual(["5"], widget.val());
});

QUnit.test('creme.widget.CheckListSelect.val (select / unselect, disabled / readonly)', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78, {selected: true, disabled: true});
    this.addCheckListSelectChoice(element, 'item3', 5, {selected: true, readonly: true});

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: true, readonly: false, visible: true, tags: [], selected: false},   // disabled => not selected
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: true, visible: true, tags: [], selected: true}],   // readonly => selected
              widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false, disabled: true},
                            {label: 'item3', value: '5',  selected: true, readonly: true, disabled: true}]);
    deepEqual(["5"], widget.val());

    $('input[type="checkbox"][value="5"]', widget.content()).trigger('click'); // readonly

    deepEqual(["5"], widget.val());

    $('input[type="checkbox"][value="78"]', widget.content()).trigger('click'); // disabled

    deepEqual(["5"], widget.val());
});

QUnit.test('creme.widget.CheckListSelect.val (select / unselect, disabled / readonly, click on label)', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78, {selected: true, disabled: true});
    this.addCheckListSelectChoice(element, 'item3', 5, {selected: true, readonly: true});

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: true, readonly: false, visible: true, tags: [], selected: false},   // disabled => not selected
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: true, visible: true, tags: [], selected: true}],   // readonly => selected
              widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false, disabled: true},
                            {label: 'item3', value: '5',  selected: true, readonly: true, disabled: true}]);
    deepEqual(["5"], widget.val());

    element.find('.checkbox-field[checklist-index="0"] .checkbox-label').trigger('click');
    element.find('.checkbox-field[checklist-index="1"] .checkbox-label').trigger('click'); // disabled
    element.find('.checkbox-field[checklist-index="2"] .checkbox-label').trigger('click'); // readonly

    deepEqual(["12", "5"], widget.val());

    element.find('.checkbox-field[checklist-index="0"] .checkbox-label').trigger('click'); // toggle => unselect
    element.find('.checkbox-field[checklist-index="1"] .checkbox-label').trigger('click'); // disabled
    element.find('.checkbox-field[checklist-index="2"] .checkbox-label').trigger('click'); // readonly

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
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: false}]);
    deepEqual([], widget.val());

    widget.selectAll();

    deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: true},
                            {label: 'item2', value: '78', selected: true},
                            {label: 'item3', value: '5',  selected: true}]);

    deepEqual(["12", "78", "5"], widget.val());
});

QUnit.test('creme.widget.CheckListSelect.selectAll (click)', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: false}]);
    deepEqual([], widget.val());

    element.find('.checklist-check-all').trigger('click');

    deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: true},
                            {label: 'item2', value: '78', selected: true},
                            {label: 'item3', value: '5',  selected: true}]);

    deepEqual(["12", "78", "5"], widget.val());
});

QUnit.test('creme.widget.CheckListSelect.selectAll (disabled options)', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78, {disabled: true});
    this.addCheckListSelectChoice(element, 'item3', 5);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false, disabled: true},
                            {label: 'item3', value: '5',  selected: false}]);
    deepEqual([], widget.val());

    widget.selectAll();

    deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: true, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: true},
                            {label: 'item2', value: '78', selected: false, disabled: true},
                            {label: 'item3', value: '5',  selected: true}]);

    deepEqual(["12", "5"], widget.val());
});


QUnit.test('creme.widget.CheckListSelect.selectAll (readonly options)', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78, {disabled: true});
    this.addCheckListSelectChoice(element, 'item3', 5, {readonly: true});
    this.addCheckListSelectChoice(element, 'item4', 8, {readonly: true, selected: true});

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false, disabled: true},
                            {label: 'item3', value: '5',  selected: false, disabled: true, readonly: true},
                            {label: 'item4', value: '8',  selected: true, disabled: true, readonly: true}]);
    deepEqual(["8"], widget.val());

    widget.selectAll();

    deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: true, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: true, visible: true, tags: [], selected: false},
               {label: 'item4', value: "8",  group: undefined, help: undefined, disabled: false, readonly: true, visible: true, tags: [], selected: true}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: true},
                            {label: 'item2', value: '78', selected: false, disabled: true},
                            {label: 'item3', value: '5',  selected: false, disabled: true, readonly: true},
                            {label: 'item4', value: '8',  selected: true, disabled: true, readonly: true}]);

    deepEqual(["12", "8"], widget.val());
});

QUnit.test('creme.widget.CheckListSelect.selectAll (filtered)', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectSearch(element, 'filter');
    this.addCheckListSelectChoice(element, 'itemAD', 12);
    this.addCheckListSelectChoice(element, 'itemAB', 78);
    this.addCheckListSelectChoice(element, 'itemABC', 5);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    var counter = element.find('.checklist-counter');

    equal('&nbsp;', counter.html());
    deepEqual([{label: 'itemAD',   value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'itemAB',  value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'itemABC', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());

    element.find('.checklist-filter').val('C').trigger($.Event("keyup", {keyCode: 13}));

    equal(ngettext('%d result of %d', '%d results of %d', 1).format(1, 3) + '&nbsp;', counter.html());
    deepEqual([{label: 'itemAD',   value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: false, tags: [], selected: false},
               {label: 'itemAB',  value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: false, tags: [], selected: false},
               {label: 'itemABC', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());

    widget.selectAll();

    equal(ngettext('%d selection', '%d selections', 1).format(1) + '&nbsp;‒&nbsp;' +
          ngettext('%d result of %d', '%d results of %d', 1).format(1, 3) + '&nbsp;', counter.html());

    deepEqual(["5"], widget.val());

    widget.unselectAll();
    element.find('.checklist-filter').val('B').trigger($.Event("keyup", {keyCode: 13}));

    equal(ngettext('%d result of %d', '%d results of %d', 2).format(2, 3) + '&nbsp;', counter.html());
    deepEqual([{label: 'itemAD',   value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: false, tags: [], selected: false},
               {label: 'itemAB',  value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'itemABC', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());

    widget.selectAll();

    deepEqual(["78", "5"], widget.val());

    equal(ngettext('%d selection', '%d selections', 2).format(2) + '&nbsp;‒&nbsp;' +
          ngettext('%d result of %d', '%d results of %d', 2).format(2, 3) + '&nbsp;', counter.html());
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
                           [{label: 'item1', value: '12', selected: true},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: true}]);
    deepEqual(['12', '5'], widget.val());

    widget.unselectAll();

    deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: false}]);

    deepEqual([], widget.val());
});

QUnit.test('creme.widget.CheckListSelect.unselectAll (click)', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);
    $('select', element).val(['12', '5']);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: true},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: true}]);
    deepEqual(['12', '5'], widget.val());

    element.find('.checklist-check-none').trigger('click');

    deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: false}]);

    deepEqual([], widget.val());
});

QUnit.test('creme.widget.CheckListSelect.unselectAll (readonly options)', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5, {readonly: true});
    $('select', element).val(['12', '5']);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: true},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: true, readonly: true, disabled: true}]);
    deepEqual(['12', '5'], widget.val());

    widget.unselectAll();

    deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: true, visible: true, tags: [], selected: true}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: true, readonly: true, disabled: true}]);

    deepEqual(['5'], widget.val());
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
                           [{label: 'item1', value: '12', selected: true},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: true}]);
    deepEqual(['12', '5'], widget.val());

    widget.reset();

    deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: false}]);

    deepEqual([], widget.val());
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

    deepEqual([{label: 'itemAD',   value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'itemAB',  value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'itemABC', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());

    element.find('.checklist-filter').val('B').trigger($.Event("keyup", {keyCode: 13}));

    deepEqual([{label: 'itemAD',   value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: false, tags: [], selected: false},
               {label: 'itemAB',  value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true,  tags: [], selected: false},
               {label: 'itemABC', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true,  tags: [], selected: false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
            [{label: 'itemAD', value: '12', disabled: false, visible: false},
             {label: 'itemAB', value: '78', disabled: false, visible: true},
             {label: 'itemABC', value: '5',  disabled: false, visible: true}]);

    element.find('.checklist-filter').val('BC').trigger($.Event("keyup", {keyCode: 13}));

    deepEqual([{label: 'itemAD',   value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: false, tags: [], selected: false},
               {label: 'itemAB',  value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: false, tags: [], selected: false},
               {label: 'itemABC', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true,  tags: [], selected: false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
            [{label: 'itemAD', value: '12', disabled: false, visible: false},
             {label: 'itemAB', value: '78', disabled: false, visible: false},
             {label: 'itemABC', value: '5',  disabled: false, visible: true}]);

    element.find('.checklist-filter').val('D').trigger($.Event("keyup", {keyCode: 13}));

    deepEqual([{label: 'itemAD',  value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true,  tags: [], selected: false},
               {label: 'itemAB',  value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: false, tags: [], selected: false},
               {label: 'itemABC', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: false, tags: [], selected: false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
            [{label: 'itemAD', value: '12', disabled: false, visible: true},
             {label: 'itemAB', value: '78', disabled: false, visible: false},
             {label: 'itemABC', value: '5',  disabled: false, visible: false}]);
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

    deepEqual([{label: 'itemAD',   value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'itemAB',  value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'itemABC', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());

    element.find('.checklist-filter').val('B').trigger($.Event("keyup", {keyCode: 13}));

    deepEqual([{label: 'itemAD',   value: "12", group: undefined, help: undefined, disabled: true, readonly: false, visible: true, tags: [], selected: false},
               {label: 'itemAB',  value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'itemABC', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
            [{label: 'itemAD', value: '12', disabled: true, visible: true},
             {label: 'itemAB', value: '78', disabled: false, visible: true},
             {label: 'itemABC', value: '5',  disabled: false, visible: true}]);

    element.find('.checklist-filter').val('BC').trigger($.Event("keyup", {keyCode: 13}));

    deepEqual([{label: 'itemAD',   value: "12", group: undefined, help: undefined, disabled: true, readonly: false, visible: true, tags: [], selected: false},
               {label: 'itemAB',  value: "78", group: undefined, help: undefined, disabled: true, readonly: false, visible: true, tags: [], selected: false},
               {label: 'itemABC', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
            [{label: 'itemAD', value: '12', disabled: true, visible: true},
             {label: 'itemAB', value: '78', disabled: true, visible: true},
             {label: 'itemABC', value: '5',  disabled: false, visible: true}]);

    element.find('.checklist-filter').val('D').trigger($.Event("keyup", {keyCode: 13}));

    deepEqual([{label: 'itemAD',  value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'itemAB',  value: "78", group: undefined, help: undefined, disabled: true, readonly: false, visible: true, tags: [], selected: false},
               {label: 'itemABC', value: "5",  group: undefined, help: undefined, disabled: true, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
            [{label: 'itemAD', value: '12', disabled: false, visible: true},
             {label: 'itemAB', value: '78', disabled: true, visible: true},
             {label: 'itemABC', value: '5',  disabled: true, visible: true}]);
});

QUnit.test('creme.widget.CheckListSelect.createItem (cancel)', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    deepEqual([], this.mockBackendUrlCalls());

    element.find('.checklist-create').trigger('click');

    this.assertOpenedDialog();
    deepEqual([
        ['mock/items/create', 'GET', {}]
    ], this.mockBackendUrlCalls());

    this.closeDialog();

    deepEqual([
        ['mock/items/create', 'GET', {}]
    ], this.mockBackendUrlCalls());

    this.assertCheckListEntries(widget.content(),
            [{label: 'item1', value: '12', selected: false},
             {label: 'item2', value: '78', selected: false},
             {label: 'item3', value: '5',  selected: false}]);
});

QUnit.test('creme.widget.CheckListSelect.createItem', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    deepEqual([], this.mockBackendUrlCalls());

    element.find('.checklist-create').trigger('click');

    this.assertOpenedDialog();
    deepEqual([
        ['mock/items/create', 'GET', {}]
    ], this.mockBackendUrlCalls());

    this.submitFormDialog();
    this.assertClosedDialog();

    deepEqual([
        ['mock/items/create', 'GET', {}],
        ['mock/items/create', 'POST', {}]
    ], this.mockBackendUrlCalls());

    this.assertCheckListEntries(widget.content(),
            [{label: 'item1', value: '12', selected: false},
             {label: 'item2', value: '78', selected: false},
             {label: 'item3', value: '5',  selected: false},
             {label: 'Item A1', value: 'A1', help: 'Item A1', selected: false},
             {label: 'Item A2', value: 'A2', help: 'Item A2', selected: false}
            ]);
});

QUnit.test('creme.widget.CheckListSelect.less (initial, true)', function(assert) {
    var element = this.createCheckListSelectElement({less: true});
    var widget = creme.widget.create(element);

    equal(true, widget.less());
    equal(true, widget.isLessCollapsed());
    equal(10, widget.lessCount());

    element = this.createCheckListSelectElement();
    widget = creme.widget.create(element, {less: true});

    equal(true, widget.less());
    equal(true, widget.isLessCollapsed());
    equal(10, widget.lessCount());
});

QUnit.test('creme.widget.CheckListSelect.less (initial, false)', function(assert) {
    var element = this.createCheckListSelectElement();
    var widget = creme.widget.create(element);

    equal(false, widget.less());
    equal(false, widget.isLessCollapsed());
    equal(10, widget.lessCount());

    element = this.createCheckListSelectElement();
    widget = creme.widget.create(element, {less: false});

    equal(false, widget.less());
    equal(false, widget.isLessCollapsed());
    equal(10, widget.lessCount());
});

QUnit.test('creme.widget.CheckListSelect.less (setter)', function(assert) {
    var element = this.createCheckListSelectElement();
    var widget = creme.widget.create(element);

    equal(false, widget.less());
    equal(false, widget.isLessCollapsed());
    equal(10, widget.lessCount());

    widget.less(5);

    equal(true, widget.less());
    equal(true, widget.isLessCollapsed());
    equal(5, widget.lessCount());

    widget.less(1);

    equal(true, widget.less());
    equal(true, widget.isLessCollapsed());
    equal(10, widget.lessCount());

    widget.less(true);

    equal(true, widget.less());
    equal(true, widget.isLessCollapsed());
    equal(10, widget.lessCount());
});

QUnit.test('creme.widget.CheckListSelect.less (count < threshold)', function(assert) {
    var element = this.createCheckListSelectElement({less: 5});
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal(true, widget.less());
    equal(true, widget.isLessCollapsed());
    equal(5, widget.lessCount());

    equal(true, element.find('.checklist-content').is('.less'));
    equal(false, element.find('.checklist-toggle-less').is('.is-active'));
    equal('', element.find('.checklist-toggle-less').html());
    equal(0, element.find('.checkbox-field.more').length);
});

QUnit.test('creme.widget.CheckListSelect.less (count > threshold)', function(assert) {
    var element = this.createCheckListSelectElement({less: 3});
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);
    this.addCheckListSelectChoice(element, 'item4', 687);
    this.addCheckListSelectChoice(element, 'item5', 487);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    var counter = element.find('.checklist-counter');

    equal(true, widget.less());
    equal(true, widget.isLessCollapsed());
    equal(3, widget.lessCount());

    equal('&nbsp;', counter.html());
    equal(true, element.find('.checklist-content').is('.less'));
    equal(true, element.find('.checklist-toggle-less').is('.is-active'));
    equal(ngettext('%d hidden item', '%d hidden items', 2).format(2), element.find('.checklist-toggle-less').html());
    equal(2, element.find('.checkbox-field.more').length);

    widget.val(["12", "78", "487"]);

    equal(ngettext('%d selection', '%d selections', 3).format(3) + '&nbsp;', counter.html());
    equal(true, element.find('.checklist-content').is('.less'));
    equal(true, element.find('.checklist-toggle-less').is('.is-active'));
    equal([
           ngettext('%d hidden item', '%d hidden items', 2).format(2),
           ngettext('(with %d selection)', '(with %d selections)', 1).format(1)
       ].join(' '),
       element.find('.checklist-toggle-less').html());
    equal(2, element.find('.checkbox-field.more').length);
});

QUnit.test('creme.widget.CheckListSelect.less (count > threshold, filtered)', function(assert) {
    var element = this.createCheckListSelectElement({less: 3});
    this.addCheckListSelectSearch(element, 'filter');
    this.addCheckListSelectChoice(element, 'itemA1', 12);
    this.addCheckListSelectChoice(element, 'itemA2', 78);
    this.addCheckListSelectChoice(element, 'itemB3', 5);
    this.addCheckListSelectChoice(element, 'itemB4', 687);
    this.addCheckListSelectChoice(element, 'itemB5', 487);
    this.addCheckListSelectChoice(element, 'itemB6', 47);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    var counter = element.find('.checklist-counter');

    equal(true, widget.less());
    equal(true, widget.isLessCollapsed());
    equal(3, widget.lessCount());

    equal('&nbsp;', counter.html());
    equal(true, element.find('.checklist-content').is('.less'));
    equal(true, element.find('.checklist-toggle-less').is('.is-active'));
    equal(ngettext('%d hidden item', '%d hidden items', 3).format(3), element.find('.checklist-toggle-less').html());
    equal(3, element.find('.checkbox-field.more').length);

    // 2 visible < threshold => all shown + no toggle less
    element.find('.checklist-filter').val('A').trigger($.Event("keyup", {keyCode: 13}));

    equal(ngettext('%d result of %d', '%d results of %d', 2).format(2, 6) + '&nbsp;', counter.html());
    equal(true, element.find('.checklist-content').is('.less'));
    equal(false, element.find('.checklist-toggle-less').is('.is-active'));
    equal('', element.find('.checklist-toggle-less').html());
    equal(0, element.find('.checkbox-field.more').length);

    // 4 visible > threshold => 3 of 4 shown + toggle less
    element.find('.checklist-filter').val('B').trigger($.Event("keyup", {keyCode: 13}));

    equal(ngettext('%d result of %d', '%d results of %d', 4).format(4, 6) + '&nbsp;', counter.html());
    equal(true, element.find('.checklist-content').is('.less'));
    equal(true, element.find('.checklist-toggle-less').is('.is-active'));
    equal(ngettext('%d hidden item', '%d hidden items', 1).format(1), element.find('.checklist-toggle-less').html());
    equal(1, element.find('.checkbox-field.more').length);
});

QUnit.test('creme.widget.CheckListSelect.less (count > threshold, toggle)', function(assert) {
    var element = this.createCheckListSelectElement({less: 3});
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);
    this.addCheckListSelectChoice(element, 'item4', 687);
    this.addCheckListSelectChoice(element, 'item5', 487);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    var counter = element.find('.checklist-counter');

    equal(true, widget.less());
    equal(true, widget.isLessCollapsed());
    equal(3, widget.lessCount());

    equal(true, element.find('.checklist-content').is('.less'));
    equal(true, element.find('.checklist-toggle-less').is('.is-active'));
    equal(ngettext('%d hidden item', '%d hidden items', 2).format(2), element.find('.checklist-toggle-less').html());
    equal(2, element.find('.checkbox-field.more').length);

    element.find('.checklist-toggle-less').trigger('click');

    equal(true, widget.less());
    equal(false, widget.isLessCollapsed());
    equal(3, widget.lessCount());

    equal('&nbsp;', counter.html());
    equal(false, element.find('.checklist-content').is('.less'));
    equal(true, element.find('.checklist-toggle-less').is('.is-active'));
    equal(ngettext('Collapse %d item', 'Collapse %d items', 2).format(2), element.find('.checklist-toggle-less').html());
    equal(2, element.find('.checkbox-field.more').length);

    widget.val(["12", "78", "487"]);

    equal(ngettext('%d selection', '%d selections', 3).format(3) + '&nbsp;', counter.html());
    equal(false, element.find('.checklist-content').is('.less'));
    equal(true, element.find('.checklist-toggle-less').is('.is-active'));
    equal(ngettext('Collapse %d item', 'Collapse %d items', 2).format(2), element.find('.checklist-toggle-less').html());
    equal(2, element.find('.checkbox-field.more').length);

    widget.toggleShowLess(true);

    equal(true, widget.less());
    equal(true, widget.isLessCollapsed());
    equal(3, widget.lessCount());

    equal(ngettext('%d selection', '%d selections', 3).format(3) + '&nbsp;', counter.html());
    equal(true, element.find('.checklist-content').is('.less'));
    equal(true, element.find('.checklist-toggle-less').is('.is-active'));
    equal([
        ngettext('%d hidden item', '%d hidden items', 2).format(2),
        ngettext('(with %d selection)', '(with %d selections)', 1).format(1)
    ].join(' '),
    element.find('.checklist-toggle-less').html());
    equal(2, element.find('.checkbox-field.more').length);
});
}(jQuery));
