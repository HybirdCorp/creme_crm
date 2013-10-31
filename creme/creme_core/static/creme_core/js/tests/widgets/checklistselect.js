function mock_checklistselect_create(options, noauto, nodelegate) {
    var options = options || {}
    var select = $('<div widget="ui-creme-checklistselect" class="ui-creme-checklistselect ui-creme-widget"/>');

    select.append($('<div class="checklist-content"/>'));
    
    if (!nodelegate)
        select.append($('<select class="ui-creme-input" multiple/>'));

    for(key in options) {
        select.attr(key, options[key]);
    }

    if (!noauto)
        select.addClass('widget-auto');

    return select;
}

function mock_checklistselect_add_choice(element, label, value) {
    var choice = $('<option value="' + (value.replace ? value.replace(/\"/g, '&quot;') : value) + '">' + label + '</option>');
    $('select.ui-creme-input', element).append(choice);
    return choice;
}

assertCheckListEntries = function(element, expected) {
    var options = $('.checkbox-field', element);

    equal(options.length, expected.length, 'checkbox count');

    options.each(function(index) {
        var expected_entry = expected[index];
        var input = $('input[type="checkbox"]', this);
        var label = $('.checkbox-label', this);

        equal(label.html(), expected_entry.label, 'checkbox %d label'.format(index));

        equal(input.val(), expected_entry.value, 'checkbox %d value'.format(index));
        equal(input.is('[disabled]'), expected_entry.disabled || false, 'checkbox %d disabled status'.format(index));
        equal(input.get()[0].checked, expected_entry.selected || false, 'checkbox %d check status'.format(index));
    });
}
module("creme.widgets.checklistselect.js", {
    setup: function() {},
    teardown: function() {}
});

test('creme.widget.CheckListSelect.create (no delegate)', function() {
    var element = mock_checklistselect_create({}, false, true);
    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal(0, widget.delegate._delegate(element).length);

    equal(0, widget.model().length());
    equal(0, $('input[type="checkbox"]', widget.content()).length);
});

test('creme.widget.CheckListSelect.create (delegate)', function() {
    var element = mock_checklistselect_create();
    mock_checklistselect_add_choice(element, 'item1', 12);
    mock_checklistselect_add_choice(element, 'item2', 78);
    mock_checklistselect_add_choice(element, 'item3', 1);

    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal(1, widget.delegate._delegate(element).length);
    equal(false, widget.disabled());

    deepEqual([{label:'item1', value:"12", disabled:false, visible:true, tags:[], selected:false},
               {label:'item2', value:"78", disabled:false, visible:true, tags:[], selected:false},
               {label:'item3', value:"1",  disabled:false, visible:true, tags:[], selected:false}], widget.model().all());

    assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12'},
                            {label:'item2', value:'78'},
                            {label:'item3', value:'1'}])
});

test('creme.widget.CheckListSelect.create (disabled)', function() {
    var element = mock_checklistselect_create({disabled:true});
    mock_checklistselect_add_choice(element, 'item1', 12);
    mock_checklistselect_add_choice(element, 'item2', 78);
    mock_checklistselect_add_choice(element, 'item3', 1);

    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    equal(1, widget.delegate._delegate(element).length);
    equal(true, widget.disabled());

    deepEqual([{label:'item1', value:"12", disabled:false, visible:true, tags:[], selected:false},
               {label:'item2', value:"78", disabled:false, visible:true, tags:[], selected:false},
               {label:'item3', value:"1",  disabled:false, visible:true, tags:[], selected:false}], widget.model().all());

    assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', disabled:true},
                            {label:'item2', value:'78', disabled:true},
                            {label:'item3', value:'1',  disabled:true}]);
});

test('creme.widget.CheckListSelect.create (initial value)', function() {
    var element = mock_checklistselect_create();
    mock_checklistselect_add_choice(element, 'item1', 12);
    mock_checklistselect_add_choice(element, 'item2', 78);
    mock_checklistselect_add_choice(element, 'item3', 1);
    $('select', element).val(['12', '1']);

    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);
    equal(false, widget.disabled());

    deepEqual([{label:'item1', value:"12", disabled:false, visible:true, tags:[], selected:true},
               {label:'item2', value:"78", disabled:false, visible:true, tags:[], selected:false},
               {label:'item3', value:"1",  disabled:false, visible:true, tags:[], selected:true}], widget.model().all());

    assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:true},
                            {label:'item2', value:'78', selected:false},
                            {label:'item3', value:'1',  selected:true}]);

    deepEqual(['12', '1'], widget.val());
});

test('creme.widget.CheckListSelect.disable', function() {
    var element = mock_checklistselect_create();
    mock_checklistselect_add_choice(element, 'item1', 12);
    mock_checklistselect_add_choice(element, 'item2', 78);

    var widget = creme.widget.create(element);

    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);
    equal(false, widget.disabled());

    deepEqual([{label:'item1', value:"12", disabled:false, visible:true, tags:[], selected:false},
               {label:'item2', value:"78", disabled:false, visible:true, tags:[], selected:false}], widget.model().all());

    assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', disabled:false},
                            {label:'item2', value:'78', disabled:false}]);

    widget.disabled(true);

    equal(true, widget.disabled());

    deepEqual([{label:'item1', value:"12", disabled:false, visible:true, tags:[], selected:false},
               {label:'item2', value:"78", disabled:false, visible:true, tags:[], selected:false}], widget.model().all());

    assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', disabled:true},
                            {label:'item2', value:'78', disabled:true}]);
});

test('creme.widget.CheckListSelect.val', function() {
    var element = mock_checklistselect_create();
    mock_checklistselect_add_choice(element, 'item1', 12);
    mock_checklistselect_add_choice(element, 'item2', 78);
    mock_checklistselect_add_choice(element, 'item3', 5);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    deepEqual([{label:'item1', value:"12", disabled:false, visible:true, tags:[], selected:false},
               {label:'item2', value:"78", disabled:false, visible:true, tags:[], selected:false},
               {label:'item3', value:"5",  disabled:false, visible:true, tags:[], selected:false}], widget.model().all());
    assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:false},
                            {label:'item2', value:'78', selected:false},
                            {label:'item3', value:'5',  selected:false}]);
    equal(null, widget.val());

    widget.val(["12", "5"]);

    deepEqual([{label:'item1', value:"12", disabled:false, visible:true, tags:[], selected:true},
               {label:'item2', value:"78", disabled:false, visible:true, tags:[], selected:false},
               {label:'item3', value:"5",  disabled:false, visible:true, tags:[], selected:true}], widget.model().all());
    assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:true},
                            {label:'item2', value:'78', selected:false},
                            {label:'item3', value:'5',  selected:true}]);
});

test('creme.widget.CheckListSelect.val (select / unselect)', function() {
    var element = mock_checklistselect_create();
    mock_checklistselect_add_choice(element, 'item1', 12);
    mock_checklistselect_add_choice(element, 'item2', 78);
    mock_checklistselect_add_choice(element, 'item3', 5);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    deepEqual([{label:'item1', value:"12", disabled:false, visible:true, tags:[], selected:false},
               {label:'item2', value:"78", disabled:false, visible:true, tags:[], selected:false},
               {label:'item3', value:"5",  disabled:false, visible:true, tags:[], selected:false}], widget.model().all());
    assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:false},
                            {label:'item2', value:'78', selected:false},
                            {label:'item3', value:'5',  selected:false}]);
    equal(null, widget.val());

    $('input[type="checkbox"][value="12"]', widget.content()).attr('checked', true).change();

    deepEqual([{label:'item1', value:"12", disabled:false, visible:true, tags:[], selected:true},
               {label:'item2', value:"78", disabled:false, visible:true, tags:[], selected:false},
               {label:'item3', value:"5",  disabled:false, visible:true, tags:[], selected:false}], widget.model().all());
    assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:true},
                            {label:'item2', value:'78', selected:false},
                            {label:'item3', value:'5',  selected:false}]);
    deepEqual(["12"], widget.val());

    $('input[type="checkbox"][value="12"]', widget.content()).attr('checked', false).change();
    $('input[type="checkbox"][value="5"]', widget.content()).attr('checked', true).change();

    deepEqual([{label:'item1', value:"12", disabled:false, visible:true, tags:[], selected:false},
               {label:'item2', value:"78", disabled:false, visible:true, tags:[], selected:false},
               {label:'item3', value:"5",  disabled:false, visible:true, tags:[], selected:true}], widget.model().all());
    assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:false},
                            {label:'item2', value:'78', selected:false},
                            {label:'item3', value:'5',  selected:true}]);
    deepEqual(["5"], widget.val());
});

test('creme.widget.CheckListSelect.selectAll', function() {
    var element = mock_checklistselect_create();
    mock_checklistselect_add_choice(element, 'item1', 12);
    mock_checklistselect_add_choice(element, 'item2', 78);
    mock_checklistselect_add_choice(element, 'item3', 5);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:false},
                            {label:'item2', value:'78', selected:false},
                            {label:'item3', value:'5',  selected:false}]);
    equal(null, widget.val());

    widget.selectAll();

    deepEqual([{label:'item1', value:"12", disabled:false, visible:true, tags:[], selected:true},
               {label:'item2', value:"78", disabled:false, visible:true, tags:[], selected:true},
               {label:'item3', value:"5",  disabled:false, visible:true, tags:[], selected:true}], widget.model().all());
    assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:true},
                            {label:'item2', value:'78', selected:true},
                            {label:'item3', value:'5',  selected:true}]);

    deepEqual(["12", "78", "5"], widget.val());
});

test('creme.widget.CheckListSelect.selectAll (disabled options)', function() {
    var element = mock_checklistselect_create();
    mock_checklistselect_add_choice(element, 'item1', 12);
    mock_checklistselect_add_choice(element, 'item2', 78).attr('disabled', 'disabled');
    mock_checklistselect_add_choice(element, 'item3', 5);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:false},
                            {label:'item2', value:'78', selected:false, disabled:true},
                            {label:'item3', value:'5',  selected:false}]);
    equal(null, widget.val());

    widget.selectAll();

    deepEqual([{label:'item1', value:"12", disabled:false, visible:true, tags:[], selected:true},
               {label:'item2', value:"78", disabled:true, visible:true, tags:[], selected:false},
               {label:'item3', value:"5",  disabled:false, visible:true, tags:[], selected:true}], widget.model().all());
    assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:true},
                            {label:'item2', value:'78', selected:false, disabled:true},
                            {label:'item3', value:'5',  selected:true}]);

    deepEqual(["12", "5"], widget.val());
});

test('creme.widget.CheckListSelect.unselectAll', function() {
    var element = mock_checklistselect_create();
    mock_checklistselect_add_choice(element, 'item1', 12);
    mock_checklistselect_add_choice(element, 'item2', 78);
    mock_checklistselect_add_choice(element, 'item3', 5);
    $('select', element).val(['12', '5']);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:true},
                            {label:'item2', value:'78', selected:false},
                            {label:'item3', value:'5',  selected:true}]);
    deepEqual(['12', '5'], widget.val());

    widget.unselectAll();

    deepEqual([{label:'item1', value:"12", disabled:false, visible:true, tags:[], selected:false},
               {label:'item2', value:"78", disabled:false, visible:true, tags:[], selected:false},
               {label:'item3', value:"5",  disabled:false, visible:true, tags:[], selected:false}], widget.model().all());
    assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:false},
                            {label:'item2', value:'78', selected:false},
                            {label:'item3', value:'5',  selected:false}]);

    deepEqual(null, widget.val());
});

test('creme.widget.CheckListSelect.reset', function() {
    var element = mock_checklistselect_create();
    mock_checklistselect_add_choice(element, 'item1', 12);
    mock_checklistselect_add_choice(element, 'item2', 78);
    mock_checklistselect_add_choice(element, 'item3', 5);
    $('select', element).val(['12', '5']);

    var widget = creme.widget.create(element);
    equal(element.hasClass('widget-active'), true);
    equal(element.hasClass('widget-ready'), true);

    assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:true},
                            {label:'item2', value:'78', selected:false},
                            {label:'item3', value:'5',  selected:true}]);
    deepEqual(['12', '5'], widget.val());

    widget.reset();

    deepEqual([{label:'item1', value:"12", disabled:false, visible:true, tags:[], selected:false},
               {label:'item2', value:"78", disabled:false, visible:true, tags:[], selected:false},
               {label:'item3', value:"5",  disabled:false, visible:true, tags:[], selected:false}], widget.model().all());
    assertCheckListEntries(widget.content(),
                           [{label:'item1', value:'12', selected:false},
                            {label:'item2', value:'78', selected:false},
                            {label:'item3', value:'5',  selected:false}]);

    deepEqual(null, widget.val());
});
