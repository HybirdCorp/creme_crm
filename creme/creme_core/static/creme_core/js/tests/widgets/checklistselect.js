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
            selectall: 3,
            createUrl: 'mock/items/create',
            delegate: '<select class="ui-creme-input" multiple></select>',
            attrs: {},
            auto: true
        }, options || {});

        var html = (
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
                delegate: options.delegate
            });

        var select = $(html);

        for (var key in options.attrs) {
            select.attr(key, options.attrs[key]);
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
        var assert = this.assert;
        var options = $('.checkbox-field', element);
        var equalHtml = this.equalHtml.bind(this);

        assert.equal(options.length, expected.length, 'checkbox count');

        options.each(function(index) {
            var expectedEntry = expected[index];
            var input = $('input[type="checkbox"]', this);
            var label = $('.checkbox-label', this);
            var isVisible = expectedEntry.visible !== undefined ? expectedEntry.visible : true;

            var expectedLabel = (
                    '<span class="checkbox-label-text" ${disabled}>${label}</span>' +
                    '<span class="checkbox-label-help" ${disabled}></span>'
                ).template({
                     disabled: expectedEntry.disabled ? 'disabled' : '',
                     label: expectedEntry.label
                });

            equalHtml(expectedLabel, label, 'checkbox %d label'.format(index));

            assert.equal(input.val(), expectedEntry.value, 'checkbox %d value'.format(index));
            assert.equal(input.is('[disabled]'), expectedEntry.disabled || false, 'checkbox %d disabled status'.format(index));
            assert.equal($(this).is('[readonly]'), expectedEntry.readonly || false, 'checkbox %d readonly status'.format(index));
            assert.equal(input.get()[0].checked, expectedEntry.selected || false, 'checkbox %d check status'.format(index));
            assert.equal($(this).is('.hidden'), !isVisible, 'checkbox %d visible status'.format(index));
        });
    }
}));

QUnit.test('creme.widget.CheckListSelect.create (no delegate)', function(assert) {
    var element = this.createCheckListSelectElement({delegate: ''});
    var widget = creme.widget.create(element);

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal(0, widget.delegate._delegate(element).length);

    assert.equal(0, widget.model().length());
    assert.equal(0, $('input[type="checkbox"]', widget.content()).length);
});

QUnit.test('creme.widget.CheckListSelect.create (delegate)', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 1);

    var widget = creme.widget.create(element);

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal(1, widget.delegate._delegate(element).length);
    assert.equal(false, widget.disabled());
    assert.deepEqual([], widget.dependencies());

    assert.deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
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

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(element.hasClass('is-disabled'), true);

    assert.equal(1, widget.delegate._delegate(element).length);
    assert.equal(true, widget.disabled());
    assert.deepEqual([], widget.val());
    assert.deepEqual([], widget.selected());

    assert.deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "1",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());

    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', disabled: true},
                            {label: 'item2', value: '78', disabled: true},
                            {label: 'item3', value: '1',  disabled: true}]);

    widget.selectAll();
    assert.deepEqual([], widget.selected());

    element.find('.checklist-check-all').trigger('click');
    assert.deepEqual([], widget.selected());

    widget.val(['12', '1']);
    assert.deepEqual(['12', '1'], widget.selected());

    widget.unselectAll();
    assert.deepEqual(['12', '1'], widget.selected());

    element.find('.checklist-check-none').trigger('click');
    assert.deepEqual(['12', '1'], widget.selected());

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

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(false, widget.disabled());
    assert.equal(element.hasClass('is-disabled'), false);

    assert.deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "1",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true}], widget.model().all());

    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: true},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '1',  selected: true}]);

    assert.deepEqual(['12', '1'], widget.val());
});

QUnit.test('creme.widget.CheckListSelect.create (initial value, json)', function(assert) {
    var element = this.createCheckListSelectElement({attrs: {datatype: 'json'}}).appendTo(this.qunitFixture());
    this.addCheckListSelectChoice(element, 'item1', '{"a": 12}');
    this.addCheckListSelectChoice(element, 'item2', '{"b": 78}');
    this.addCheckListSelectChoice(element, 'item3', "1");

    $('select', element).val(['{"a": 12}', '1']);

    var widget = creme.widget.create(element);

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(false, widget.disabled());
    assert.equal(element.hasClass('is-disabled'), false);

    assert.deepEqual([{label: 'item1', value: '{"a": 12}', group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true},
               {label: 'item2', value: '{"b": 78}', group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: '1',  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true}], widget.model().all());

    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '{"a": 12}', selected: true},
                            {label: 'item2', value: '{"b": 78}', selected: false},
                            {label: 'item3', value: '1',  selected: true}]);

    assert.deepEqual(['{"a": 12}', '1'], widget.val());
    assert.deepEqual([{a: 12}, 1], widget.cleanedval());
});

QUnit.test('creme.widget.CheckListSelect.disable', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);

    var widget = creme.widget.create(element);

    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);
    assert.equal(false, widget.disabled());

    assert.deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());

    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', disabled: false},
                            {label: 'item2', value: '78', disabled: false}]);

    widget.disabled(true);

    assert.equal(true, widget.disabled());

    assert.deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
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
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    var input = element.find('select');

    assert.deepEqual([], widget.val());
    assert.equal(false, element.is('.is-field-invalid'));

    // not required
    creme.forms.validateHtml5Field(input);
    assert.equal(false, element.is('.is-field-invalid'));

    element.find('select').attr('required', '');

    // required
    creme.forms.validateHtml5Field(input);
    assert.equal(true, element.is('.is-field-invalid'));

    widget.val(['12']);

    creme.forms.validateHtml5Field(input);
    assert.equal(false, element.is('.is-field-invalid'));
});

QUnit.test('creme.widget.CheckListSelect.val', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    var counter = element.find('.checklist-counter');

    assert.equal('&nbsp;', counter.html());
    assert.deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: false}]);
    assert.deepEqual([], widget.val());

    widget.val(["12", "5"]);

    assert.equal(ngettext('%d selection', '%d selections', 2).format(2) + '&nbsp;', counter.html());
    assert.deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: true},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: true}]);

    widget.val([]);

    assert.equal('&nbsp;', counter.html());
    this.assertCheckListEntries(widget.content(),
            [{label: 'item1', value: '12', selected: false},
             {label: 'item2', value: '78', selected: false},
             {label: 'item3', value: '5',  selected: false}]);
});

QUnit.test('creme.widget.CheckListSelect.val (select / unselect)', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    var counter = element.find('.checklist-counter');

    assert.equal('&nbsp;', counter.html());
    assert.deepEqual([], widget.val());
    assert.deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: false}]);

    $('input[type="checkbox"][value="12"]', widget.content()).prop('checked', true).trigger('change');

    assert.equal(ngettext('%d selection', '%d selections', 1).format(1) + '&nbsp;', counter.html());
    assert.deepEqual(["12"], widget.val());

    assert.deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: true},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: false}]);

    $('input[type="checkbox"][value="12"]', widget.content()).prop('checked', false).trigger('change');
    $('input[type="checkbox"][value="5"]', widget.content()).prop('checked', true).trigger('change');

    assert.equal(ngettext('%d selection', '%d selections', 1).format(1) + '&nbsp;', counter.html());
    assert.deepEqual(["5"], widget.val());

    assert.deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
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
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: false}]);
    assert.deepEqual([], widget.val());

    element.find('.checkbox-field[checklist-index="0"] .checkbox-label').trigger('click');

    assert.deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: true},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: false}]);
    assert.deepEqual(["12"], widget.val());

    element.find('.checkbox-field[checklist-index="0"] .checkbox-label').trigger('click');  // toggle => unselect
    element.find('.checkbox-field[checklist-index="2"] .checkbox-label').trigger('click');

    assert.deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: true}]);
    assert.deepEqual(["5"], widget.val());
});

QUnit.test('creme.widget.CheckListSelect.val (select / unselect, disabled / readonly)', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78, {selected: true, disabled: true});
    this.addCheckListSelectChoice(element, 'item3', 5, {selected: true, readonly: true});

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: true, readonly: false, visible: true, tags: [], selected: false},   // disabled => not selected
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: true, visible: true, tags: [], selected: true}],   // readonly => selected
              widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false, disabled: true},
                            {label: 'item3', value: '5',  selected: true, readonly: true, disabled: true}]);
    assert.deepEqual(["5"], widget.val());

    $('input[type="checkbox"][value="5"]', widget.content()).trigger('click'); // readonly

    assert.deepEqual(["5"], widget.val());

    $('input[type="checkbox"][value="78"]', widget.content()).trigger('click'); // disabled

    assert.deepEqual(["5"], widget.val());
});

QUnit.test('creme.widget.CheckListSelect.val (select / unselect, disabled / readonly, click on label)', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78, {selected: true, disabled: true});
    this.addCheckListSelectChoice(element, 'item3', 5, {selected: true, readonly: true});

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: true, readonly: false, visible: true, tags: [], selected: false},   // disabled => not selected
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: true, visible: true, tags: [], selected: true}],   // readonly => selected
              widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false, disabled: true},
                            {label: 'item3', value: '5',  selected: true, readonly: true, disabled: true}]);
    assert.deepEqual(["5"], widget.val());

    element.find('.checkbox-field[checklist-index="0"] .checkbox-label').trigger('click');
    element.find('.checkbox-field[checklist-index="1"] .checkbox-label').trigger('click'); // disabled
    element.find('.checkbox-field[checklist-index="2"] .checkbox-label').trigger('click'); // readonly

    assert.deepEqual(["12", "5"], widget.val());

    element.find('.checkbox-field[checklist-index="0"] .checkbox-label').trigger('click'); // toggle => unselect
    element.find('.checkbox-field[checklist-index="1"] .checkbox-label').trigger('click'); // disabled
    element.find('.checkbox-field[checklist-index="2"] .checkbox-label').trigger('click'); // readonly

    assert.deepEqual(["5"], widget.val());
});

QUnit.test('creme.widget.CheckListSelect.selectAll', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: false}]);
    assert.deepEqual([], widget.val());

    widget.selectAll();

    assert.deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: true},
                            {label: 'item2', value: '78', selected: true},
                            {label: 'item3', value: '5',  selected: true}]);

    assert.deepEqual(["12", "78", "5"], widget.val());
});

QUnit.test('creme.widget.CheckListSelect.selectAll (click)', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: false}]);
    assert.deepEqual([], widget.val());

    element.find('.checklist-check-all').trigger('click');

    assert.deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: true},
                            {label: 'item2', value: '78', selected: true},
                            {label: 'item3', value: '5',  selected: true}]);

    assert.deepEqual(["12", "78", "5"], widget.val());
});

QUnit.parameterize('creme.widget.CheckListSelect.selectAll (show)', [
    [undefined, 3, false],
    [3, 3, false],
    [10, 10, true]
], function(limit, expected, isHidden, assert) {
    var element = this.createCheckListSelectElement({
        attrs: {
            selectall: limit
        }
    });
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal(expected, widget.minShowSelectAll());

    assert.equal(element.find('.checklist-check-all').is('.hidden'), isHidden);
    assert.equal(element.find('.checklist-check-none').is('.hidden'), isHidden);

    widget.minShowSelectAll(5);

    assert.equal(element.find('.checklist-check-all').is('.hidden'), true);
    assert.equal(element.find('.checklist-check-none').is('.hidden'), true);

    widget.minShowSelectAll(2);

    assert.equal(element.find('.checklist-check-all').is('.hidden'), false);
    assert.equal(element.find('.checklist-check-none').is('.hidden'), false);
});

QUnit.test('creme.widget.CheckListSelect.selectAll (disabled options)', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78, {disabled: true});
    this.addCheckListSelectChoice(element, 'item3', 5);

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false, disabled: true},
                            {label: 'item3', value: '5',  selected: false}]);
    assert.deepEqual([], widget.val());

    widget.selectAll();

    assert.deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: true, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: true},
                            {label: 'item2', value: '78', selected: false, disabled: true},
                            {label: 'item3', value: '5',  selected: true}]);

    assert.deepEqual(["12", "5"], widget.val());
});


QUnit.test('creme.widget.CheckListSelect.selectAll (readonly options)', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78, {disabled: true});
    this.addCheckListSelectChoice(element, 'item3', 5, {readonly: true});
    this.addCheckListSelectChoice(element, 'item4', 8, {readonly: true, selected: true});

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false, disabled: true},
                            {label: 'item3', value: '5',  selected: false, disabled: true, readonly: true},
                            {label: 'item4', value: '8',  selected: true, disabled: true, readonly: true}]);
    assert.deepEqual(["8"], widget.val());

    widget.selectAll();

    assert.deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: true},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: true, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: true, visible: true, tags: [], selected: false},
               {label: 'item4', value: "8",  group: undefined, help: undefined, disabled: false, readonly: true, visible: true, tags: [], selected: true}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: true},
                            {label: 'item2', value: '78', selected: false, disabled: true},
                            {label: 'item3', value: '5',  selected: false, disabled: true, readonly: true},
                            {label: 'item4', value: '8',  selected: true, disabled: true, readonly: true}]);

    assert.deepEqual(["12", "8"], widget.val());
});

QUnit.parametrize('creme.widget.CheckListSelect.selectAll (filtered)', [
    [
        'C', {
            visibleSummary: ngettext('%d result of %d', '%d results of %d', 1).format(1, 3),
            selectedSummary: ngettext('%d selection', '%d selections', 1).format(1),
            visible: 1,
            total: 3,
            items: [
                {label: 'itemAD / Élément Âù',  value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: false, tags: [], selected: false},
                {label: 'itemAB / Élément Â',  value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: false, tags: [], selected: false},
                {label: 'itemABC / Élément ÂùÖ', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true,  tags: [], selected: false}
            ],
            selected: ["5"]
        }
    ],
    [
        'B', {
            visibleSummary: ngettext('%d result of %d', '%d results of %d', 2).format(2, 3),
            selectedSummary: ngettext('%d selection', '%d selections', 2).format(2),
            visible: 2,
            total: 3,
            items: [
                {label: 'itemAD / Élément Âù',  value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: false, tags: [], selected: false},
                {label: 'itemAB / Élément Â',  value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true,  tags: [], selected: false},
                {label: 'itemABC / Élément ÂùÖ', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true,  tags: [], selected: false}
            ],
            selected: ["78", "5"]
        }
    ],
    [
        'ü', {
            visibleSummary: ngettext('%d result of %d', '%d results of %d', 2).format(2, 3),
            selectedSummary: ngettext('%d selection', '%d selections', 2).format(2),
            visible: 2,
            total: 3,
            items: [
                {label: 'itemAD / Élément Âù',  value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
                {label: 'itemAB / Élément Â',  value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: false,  tags: [], selected: false},
                {label: 'itemABC / Élément ÂùÖ', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true,  tags: [], selected: false}
            ],
            selected: ["12", "5"]
        }
    ],
    [
        'element', {
            visibleSummary: '',
            selectedSummary: ngettext('%d selection', '%d selections', 3).format(3),
            visible: 3,
            total: 3,
            items: [
                {label: 'itemAD / Élément Âù',  value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
                {label: 'itemAB / Élément Â',  value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true,  tags: [], selected: false},
                {label: 'itemABC / Élément ÂùÖ', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true,  tags: [], selected: false}
            ],
            selected: ["12", "78", "5"]
        }
    ]
], function(term, expected, assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectSearch(element, 'filter');
    this.addCheckListSelectChoice(element, 'itemAD / Élément Âù', 12);
    this.addCheckListSelectChoice(element, 'itemAB / Élément Â', 78);
    this.addCheckListSelectChoice(element, 'itemABC / Élément ÂùÖ', 5);

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    var counter = element.find('.checklist-counter');

    assert.equal('&nbsp;', counter.html());
    assert.deepEqual([{label: 'itemAD / Élément Âù',  value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'itemAB / Élément Â',  value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'itemABC / Élément ÂùÖ', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());

    element.find('.checklist-filter').val(term).trigger($.Event("keyup", {keyCode: 13}));

    assert.equal(expected.visibleSummary + '&nbsp;', counter.html());
    assert.deepEqual(expected.items, widget.model().all());

    widget.selectAll();

    if (expected.visibleSummary.length > 0 && expected.selectedSummary.length > 0) {
        assert.equal(expected.selectedSummary + '&nbsp;‒&nbsp;' + expected.visibleSummary + '&nbsp;', counter.html());
    } else {
        assert.equal(expected.selectedSummary + expected.visibleSummary + '&nbsp;', counter.html());
    }

    assert.deepEqual(expected.selected, widget.val());
});

QUnit.test('creme.widget.CheckListSelect.unselectAll', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);
    $('select', element).val(['12', '5']);

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: true},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: true}]);
    assert.deepEqual(['12', '5'], widget.val());

    widget.unselectAll();

    assert.deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: false}]);

    assert.deepEqual([], widget.val());
});

QUnit.test('creme.widget.CheckListSelect.unselectAll (click)', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);
    $('select', element).val(['12', '5']);

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: true},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: true}]);
    assert.deepEqual(['12', '5'], widget.val());

    element.find('.checklist-check-none').trigger('click');

    assert.deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: false}]);

    assert.deepEqual([], widget.val());
});

QUnit.test('creme.widget.CheckListSelect.unselectAll (readonly options)', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5, {readonly: true});
    $('select', element).val(['12', '5']);

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: true},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: true, readonly: true, disabled: true}]);
    assert.deepEqual(['12', '5'], widget.val());

    widget.unselectAll();

    assert.deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: true, visible: true, tags: [], selected: true}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: true, readonly: true, disabled: true}]);

    assert.deepEqual(['5'], widget.val());
});


QUnit.test('creme.widget.CheckListSelect.reset', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);
    $('select', element).val(['12', '5']);

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: true},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: true}]);
    assert.deepEqual(['12', '5'], widget.val());

    widget.reset();

    assert.deepEqual([{label: 'item1', value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item2', value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'item3', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
                           [{label: 'item1', value: '12', selected: false},
                            {label: 'item2', value: '78', selected: false},
                            {label: 'item3', value: '5',  selected: false}]);

    assert.deepEqual([], widget.val());
});

QUnit.test('creme.widget.CheckListSelect.filter', function(assert) {
    var element = this.createCheckListSelectElement();
    this.addCheckListSelectSearch(element, 'filter');
    this.addCheckListSelectChoice(element, 'itemAD', 12);
    this.addCheckListSelectChoice(element, 'itemAB', 78);
    this.addCheckListSelectChoice(element, 'itemABC', 5);

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.deepEqual([{label: 'itemAD',   value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'itemAB',  value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'itemABC', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());

    element.find('.checklist-filter').val('B').trigger($.Event("keyup", {keyCode: 13}));

    assert.deepEqual([{label: 'itemAD',   value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: false, tags: [], selected: false},
               {label: 'itemAB',  value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true,  tags: [], selected: false},
               {label: 'itemABC', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true,  tags: [], selected: false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
            [{label: 'itemAD', value: '12', disabled: false, visible: false},
             {label: 'itemAB', value: '78', disabled: false, visible: true},
             {label: 'itemABC', value: '5',  disabled: false, visible: true}]);

    element.find('.checklist-filter').val('BC').trigger($.Event("keyup", {keyCode: 13}));

    assert.deepEqual([{label: 'itemAD',   value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: false, tags: [], selected: false},
               {label: 'itemAB',  value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: false, tags: [], selected: false},
               {label: 'itemABC', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true,  tags: [], selected: false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
            [{label: 'itemAD', value: '12', disabled: false, visible: false},
             {label: 'itemAB', value: '78', disabled: false, visible: false},
             {label: 'itemABC', value: '5',  disabled: false, visible: true}]);

    element.find('.checklist-filter').val('D').trigger($.Event("keyup", {keyCode: 13}));

    assert.deepEqual([{label: 'itemAD',  value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true,  tags: [], selected: false},
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
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.deepEqual([{label: 'itemAD',   value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'itemAB',  value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'itemABC', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());

    element.find('.checklist-filter').val('B').trigger($.Event("keyup", {keyCode: 13}));

    assert.deepEqual([{label: 'itemAD',   value: "12", group: undefined, help: undefined, disabled: true, readonly: false, visible: true, tags: [], selected: false},
               {label: 'itemAB',  value: "78", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
               {label: 'itemABC', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
            [{label: 'itemAD', value: '12', disabled: true, visible: true},
             {label: 'itemAB', value: '78', disabled: false, visible: true},
             {label: 'itemABC', value: '5',  disabled: false, visible: true}]);

    element.find('.checklist-filter').val('BC').trigger($.Event("keyup", {keyCode: 13}));

    assert.deepEqual([{label: 'itemAD',   value: "12", group: undefined, help: undefined, disabled: true, readonly: false, visible: true, tags: [], selected: false},
               {label: 'itemAB',  value: "78", group: undefined, help: undefined, disabled: true, readonly: false, visible: true, tags: [], selected: false},
               {label: 'itemABC', value: "5",  group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false}], widget.model().all());
    this.assertCheckListEntries(widget.content(),
            [{label: 'itemAD', value: '12', disabled: true, visible: true},
             {label: 'itemAB', value: '78', disabled: true, visible: true},
             {label: 'itemABC', value: '5',  disabled: false, visible: true}]);

    element.find('.checklist-filter').val('D').trigger($.Event("keyup", {keyCode: 13}));

    assert.deepEqual([{label: 'itemAD',  value: "12", group: undefined, help: undefined, disabled: false, readonly: false, visible: true, tags: [], selected: false},
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
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.deepEqual([], this.mockBackendUrlCalls());

    element.find('.checklist-create').trigger('click');

    this.assertOpenedDialog();
    assert.deepEqual([
        ['mock/items/create', 'GET', {}]
    ], this.mockBackendUrlCalls());

    this.closeDialog();

    assert.deepEqual([
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
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.deepEqual([], this.mockBackendUrlCalls());

    element.find('.checklist-create').trigger('click');

    this.assertOpenedDialog();
    assert.deepEqual([
        ['mock/items/create', 'GET', {}]
    ], this.mockBackendUrlCalls());

    this.submitFormDialog();
    this.assertClosedDialog();

    assert.deepEqual([
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

QUnit.test('creme.widget.CheckListSelect.createItem (disabled)', function(assert) {
    var element = this.createCheckListSelectElement({
        createUrl: ''
    });
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);

    creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal(element.find('.checklist-create').attr('href'), '');

    element.find('.checklist-create').trigger('click');

    this.assertClosedDialog();
    assert.deepEqual([], this.mockBackendUrlCalls());
});

QUnit.test('creme.widget.CheckListSelect.less (initial, true)', function(assert) {
    var element = this.createCheckListSelectElement({less: true});
    var widget = creme.widget.create(element);

    assert.equal(true, widget.less());
    assert.equal(true, widget.isLessCollapsed());
    assert.equal(10, widget.lessCount());

    element = this.createCheckListSelectElement();
    widget = creme.widget.create(element, {less: true});

    assert.equal(true, widget.less());
    assert.equal(true, widget.isLessCollapsed());
    assert.equal(10, widget.lessCount());
});

QUnit.test('creme.widget.CheckListSelect.less (initial, false)', function(assert) {
    var element = this.createCheckListSelectElement();
    var widget = creme.widget.create(element);

    assert.equal(false, widget.less());
    assert.equal(false, widget.isLessCollapsed());
    assert.equal(10, widget.lessCount());

    element = this.createCheckListSelectElement();
    widget = creme.widget.create(element, {less: false});

    assert.equal(false, widget.less());
    assert.equal(false, widget.isLessCollapsed());
    assert.equal(10, widget.lessCount());
});

QUnit.test('creme.widget.CheckListSelect.less (setter)', function(assert) {
    var element = this.createCheckListSelectElement();
    var widget = creme.widget.create(element);

    assert.equal(false, widget.less());
    assert.equal(false, widget.isLessCollapsed());
    assert.equal(10, widget.lessCount());

    widget.less(5);

    assert.equal(true, widget.less());
    assert.equal(true, widget.isLessCollapsed());
    assert.equal(5, widget.lessCount());

    widget.less(1);

    assert.equal(true, widget.less());
    assert.equal(true, widget.isLessCollapsed());
    assert.equal(10, widget.lessCount());

    widget.less(true);

    assert.equal(true, widget.less());
    assert.equal(true, widget.isLessCollapsed());
    assert.equal(10, widget.lessCount());
});

QUnit.test('creme.widget.CheckListSelect.less (count < threshold)', function(assert) {
    var element = this.createCheckListSelectElement({less: 5});
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    assert.equal(true, widget.less());
    assert.equal(true, widget.isLessCollapsed());
    assert.equal(5, widget.lessCount());

    assert.equal(true, element.find('.checklist-content').is('.less'));
    assert.equal(false, element.find('.checklist-toggle-less').is('.is-active'));
    assert.equal('', element.find('.checklist-toggle-less').html());
    assert.equal(0, element.find('.checkbox-field.more').length);
});

QUnit.test('creme.widget.CheckListSelect.less (count > threshold)', function(assert) {
    var element = this.createCheckListSelectElement({less: 3});
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);
    this.addCheckListSelectChoice(element, 'item4', 687);
    this.addCheckListSelectChoice(element, 'item5', 487);

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    var counter = element.find('.checklist-counter');

    assert.equal(true, widget.less());
    assert.equal(true, widget.isLessCollapsed());
    assert.equal(3, widget.lessCount());

    assert.equal('&nbsp;', counter.html());
    assert.equal(true, element.find('.checklist-content').is('.less'));
    assert.equal(true, element.find('.checklist-toggle-less').is('.is-active'));
    assert.equal(ngettext('%d hidden item', '%d hidden items', 2).format(2), element.find('.checklist-toggle-less').html());
    assert.equal(2, element.find('.checkbox-field.more').length);

    widget.val(["12", "78", "487"]);

    assert.equal(ngettext('%d selection', '%d selections', 3).format(3) + '&nbsp;', counter.html());
    assert.equal(true, element.find('.checklist-content').is('.less'));
    assert.equal(true, element.find('.checklist-toggle-less').is('.is-active'));
    assert.equal([
           ngettext('%d hidden item', '%d hidden items', 2).format(2),
           ngettext('(with %d selection)', '(with %d selections)', 1).format(1)
       ].join(' '),
       element.find('.checklist-toggle-less').html());
    assert.equal(2, element.find('.checkbox-field.more').length);
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
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    var counter = element.find('.checklist-counter');

    assert.equal(true, widget.less());
    assert.equal(true, widget.isLessCollapsed());
    assert.equal(3, widget.lessCount());

    assert.equal('&nbsp;', counter.html());
    assert.equal(true, element.find('.checklist-content').is('.less'));
    assert.equal(true, element.find('.checklist-toggle-less').is('.is-active'));
    assert.equal(ngettext('%d hidden item', '%d hidden items', 3).format(3), element.find('.checklist-toggle-less').html());
    assert.equal(3, element.find('.checkbox-field.more').length);

    // 2 visible < threshold => all shown + no toggle less
    element.find('.checklist-filter').val('A').trigger($.Event("keyup", {keyCode: 13}));

    assert.equal(ngettext('%d result of %d', '%d results of %d', 2).format(2, 6) + '&nbsp;', counter.html());
    assert.equal(true, element.find('.checklist-content').is('.less'));
    assert.equal(false, element.find('.checklist-toggle-less').is('.is-active'));
    assert.equal('', element.find('.checklist-toggle-less').html());
    assert.equal(0, element.find('.checkbox-field.more').length);

    // 4 visible > threshold => 3 of 4 shown + toggle less
    element.find('.checklist-filter').val('B').trigger($.Event("keyup", {keyCode: 13}));

    assert.equal(ngettext('%d result of %d', '%d results of %d', 4).format(4, 6) + '&nbsp;', counter.html());
    assert.equal(true, element.find('.checklist-content').is('.less'));
    assert.equal(true, element.find('.checklist-toggle-less').is('.is-active'));
    assert.equal(ngettext('%d hidden item', '%d hidden items', 1).format(1), element.find('.checklist-toggle-less').html());
    assert.equal(1, element.find('.checkbox-field.more').length);
});

QUnit.test('creme.widget.CheckListSelect.less (count > threshold, toggle)', function(assert) {
    var element = this.createCheckListSelectElement({less: 3});
    this.addCheckListSelectChoice(element, 'item1', 12);
    this.addCheckListSelectChoice(element, 'item2', 78);
    this.addCheckListSelectChoice(element, 'item3', 5);
    this.addCheckListSelectChoice(element, 'item4', 687);
    this.addCheckListSelectChoice(element, 'item5', 487);

    var widget = creme.widget.create(element);
    assert.equal(element.hasClass('widget-active'), true);
    assert.equal(element.hasClass('widget-ready'), true);

    var counter = element.find('.checklist-counter');

    assert.equal(true, widget.less());
    assert.equal(true, widget.isLessCollapsed());
    assert.equal(3, widget.lessCount());

    assert.equal(true, element.find('.checklist-content').is('.less'));
    assert.equal(true, element.find('.checklist-toggle-less').is('.is-active'));
    assert.equal(ngettext('%d hidden item', '%d hidden items', 2).format(2), element.find('.checklist-toggle-less').html());
    assert.equal(2, element.find('.checkbox-field.more').length);

    element.find('.checklist-toggle-less').trigger('click');

    assert.equal(true, widget.less());
    assert.equal(false, widget.isLessCollapsed());
    assert.equal(3, widget.lessCount());

    assert.equal('&nbsp;', counter.html());
    assert.equal(false, element.find('.checklist-content').is('.less'));
    assert.equal(true, element.find('.checklist-toggle-less').is('.is-active'));
    assert.equal(ngettext('Collapse %d item', 'Collapse %d items', 2).format(2), element.find('.checklist-toggle-less').html());
    assert.equal(2, element.find('.checkbox-field.more').length);

    widget.val(["12", "78", "487"]);

    assert.equal(ngettext('%d selection', '%d selections', 3).format(3) + '&nbsp;', counter.html());
    assert.equal(false, element.find('.checklist-content').is('.less'));
    assert.equal(true, element.find('.checklist-toggle-less').is('.is-active'));
    assert.equal(ngettext('Collapse %d item', 'Collapse %d items', 2).format(2), element.find('.checklist-toggle-less').html());
    assert.equal(2, element.find('.checkbox-field.more').length);

    widget.toggleShowLess(true);

    assert.equal(true, widget.less());
    assert.equal(true, widget.isLessCollapsed());
    assert.equal(3, widget.lessCount());

    assert.equal(ngettext('%d selection', '%d selections', 3).format(3) + '&nbsp;', counter.html());
    assert.equal(true, element.find('.checklist-content').is('.less'));
    assert.equal(true, element.find('.checklist-toggle-less').is('.is-active'));
    assert.equal([
        ngettext('%d hidden item', '%d hidden items', 2).format(2),
        ngettext('(with %d selection)', '(with %d selections)', 1).format(1)
    ].join(' '),
    element.find('.checklist-toggle-less').html());
    assert.equal(2, element.find('.checkbox-field.more').length);
});
}(jQuery));
