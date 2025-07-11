(function($) {

QUnit.module("creme.model.CheckListRenderer.js", new QUnitMixin({
    assertOptions: function(element, expected) {
        var assert = this.assert;
        var options = $('option', element);

        assert.equal(options.length, expected.length, 'option count');

        options.each(function(index) {
            assert.equal($(this).attr('value'), expected[index].value, 'option %d value'.format(index));
            assert.equal($(this).html(), expected[index].label, 'option %d label'.format(index));

            if (expected.group) {
                assert.equal($(this).parent().is('optgroup'), true, 'option %d has group'.format(index));
                assert.equal($(this).parent().attr('label'), expected.group, 'option %d group label'.format(index));
            }
        });
    },

    assertOptionGroups: function(element, expected) {
        var assert = this.assert;
        var groups = $('optgroup', element);

        assert.equal(groups.length, expected.length, 'optgroup count');

        groups.each(function(index) {
            assert.equal($(this).attr('label'), expected[index], 'optgroup %d'.format(index));
        });
    }
}));

QUnit.test('creme.model.CheckListRenderer.constructor', function(assert) {
    var model = new creme.model.Array();
    var element = $('<select><options></options></select>');
    var renderer = new creme.model.CheckListRenderer({
        target: element,
        model: model
    });

    renderer.redraw();

    assert.equal('li', renderer.itemTag());
    assert.equal(false, renderer.disabled());
    assert.equal(model, renderer.model());
    assert.equal(element, renderer.target());

    renderer =  new creme.model.CheckListRenderer({
        itemtag: 'div',
        disabled: true
    });

    assert.equal('div', renderer.itemTag());
    assert.equal(true, renderer.disabled());
    assert.equal(undefined, renderer.model());
    assert.equal(undefined, renderer.target());
});

QUnit.test('creme.model.CheckListRenderer.render', function(assert) {
    var model = new creme.model.Array([
        {value: '1', label: 'a', visible: true},
        {value: '2', label: 'b', visible: true, selected: true, tags: ['tag1']},
        {value: '3', label: 'c', visible: true, disabled: true, tags: ['tag2']},
        {value: '4', label: 'd', visible: false},
        {value: '5', label: 'e', visible: true, help: 'help !'},
        {value: '6', label: 'f', visible: true, readonly: true},
        {value: '7', label: 'g', visible: true, selected: true, readonly: true}
    ]);
    var element = $('<ul></ul>');
    var renderer = new creme.model.CheckListRenderer({
        target: element,
        model: model
    });

    renderer.redraw();

    this.equalOuterHtml(
       '<ul>' +
           '<li class="checkbox-field " checklist-index="0" tags="">' +
                '<input type="checkbox" value="1" checklist-index="0">' +
                '<div class="checkbox-label">' +
                    '<span class="checkbox-label-text">a</span>' +
                    '<span class="checkbox-label-help"></span>' +
                '</div>' +
           '</li>' +
           '<li class="checkbox-field " checklist-index="1" tags="tag1">' +
                '<input type="checkbox" value="2" checklist-index="1" checked>' +
                '<div class="checkbox-label">' +
                    '<span class="checkbox-label-text">b</span>' +
                    '<span class="checkbox-label-help"></span>' +
                '</div>' +
           '</li>' +
           '<li class="checkbox-field " checklist-index="2" tags="tag2" disabled>' +
                '<input type="checkbox" value="3" checklist-index="2" disabled>' +
                '<div class="checkbox-label">' +
                    '<span class="checkbox-label-text" disabled>c</span>' +
                    '<span class="checkbox-label-help" disabled></span>' +
                '</div>' +
           '</li>' +
           '<li class="checkbox-field hidden" checklist-index="3" tags="">' +        // ignore visibility in parse !
                '<input type="checkbox" value="4" checklist-index="3">' +
                '<div class="checkbox-label">' +
                    '<span class="checkbox-label-text">d</span>' +
                    '<span class="checkbox-label-help"></span>' +
                '</div>' +
           '</li>' +
           '<li class="checkbox-field " checklist-index="4" tags="">' +
                '<input type="checkbox" value="5" checklist-index="4">' +
                '<div class="checkbox-label">' +
                    '<span class="checkbox-label-text">e</span>' +
                    '<span class="checkbox-label-help">help !</span>' +
                '</div>' +
            '</li>' +
            '<li class="checkbox-field " checklist-index="5" tags="" disabled readonly>' +
                 '<input type="checkbox" value="6" checklist-index="5" disabled>' +
                 '<div class="checkbox-label">' +
                     '<span class="checkbox-label-text" disabled>f</span>' +
                     '<span class="checkbox-label-help" disabled></span>' +
                 '</div>' +
            '</li>' +
            '<li class="checkbox-field " checklist-index="6" tags="" disabled readonly>' +
                 '<input type="checkbox" value="7" checklist-index="6" disabled checked>' +
                 '<div class="checkbox-label">' +
                     '<span class="checkbox-label-text" disabled>g</span>' +
                     '<span class="checkbox-label-help" disabled></span>' +
                 '</div>' +
            '</li>' +
        '</ul>', element);
});

QUnit.test('creme.model.CheckListRenderer.render (data)', function(assert) {
    var model = new creme.model.Array([
        {value: true, label: 'a', visible: true},
        {value: 42, label: 'b', visible: true},
        {value: [1, 2, 3], label: 'c', visible: true},
        {value: {x: 11, y: 17}, label: 'd', visible: true},
        {value: null, label: 'e', visible: true},
        {value: undefined, label: 'f', visible: true}
    ]);
    var element = $('<ul></ul>');
    var renderer = new creme.model.CheckListRenderer({
        target: element,
        model: model
    });

    renderer.redraw();

    this.equalOuterHtml(
       '<ul>' +
           '<li class="checkbox-field " checklist-index="0" tags="">' +
                '<input type="checkbox" value="true" checklist-index="0">' +
                '<div class="checkbox-label">' +
                    '<span class="checkbox-label-text">a</span>' +
                    '<span class="checkbox-label-help"></span>' +
                '</div>' +
           '</li>' +
           '<li class="checkbox-field " checklist-index="1" tags="">' +
                '<input type="checkbox" value="42" checklist-index="1">' +
                '<div class="checkbox-label">' +
                    '<span class="checkbox-label-text">b</span>' +
                    '<span class="checkbox-label-help"></span>' +
                '</div>' +
           '</li>' +
           '<li class="checkbox-field " checklist-index="2" tags="">' +
                '<input type="checkbox" value="[1,2,3]" checklist-index="2">' +
                '<div class="checkbox-label">' +
                    '<span class="checkbox-label-text">c</span>' +
                    '<span class="checkbox-label-help"></span>' +
                '</div>' +
           '</li>' +
           '<li class="checkbox-field " checklist-index="3" tags="">' +
                '<input type="checkbox" value="{&quot;x&quot;:11,&quot;y&quot;:17}" checklist-index="3">' +
                '<div class="checkbox-label">' +
                    '<span class="checkbox-label-text">d</span>' +
                    '<span class="checkbox-label-help"></span>' +
                '</div>' +
           '</li>' +
           '<li class="checkbox-field " checklist-index="4" tags="">' +
                '<input type="checkbox" value="" checklist-index="4">' +
                '<div class="checkbox-label">' +
                    '<span class="checkbox-label-text">e</span>' +
                    '<span class="checkbox-label-help"></span>' +
                '</div>' +
            '</li>' +
            '<li class="checkbox-field " checklist-index="5" tags="">' +
                 '<input type="checkbox" value="" checklist-index="5">' +
                 '<div class="checkbox-label">' +
                     '<span class="checkbox-label-text">f</span>' +
                     '<span class="checkbox-label-help"></span>' +
                 '</div>' +
            '</li>' +
        '</ul>', element);
});

QUnit.test('creme.model.CheckListRenderer.update', function(assert) {
    var model = new creme.model.Array([
        {value: '1', label: 'a', visible: true}
    ]);
    var element = $('<ul></ul>');
    var renderer = new creme.model.CheckGroupListRenderer({
        target: element,
        model: model
    });

    renderer.redraw();

    this.equalOuterHtml(
       '<ul>' +
           '<li class="checkbox-field " checklist-index="0" tags="">' +
                '<input type="checkbox" value="1" checklist-index="0">' +
                '<div class="checkbox-label">' +
                    '<span class="checkbox-label-text">a</span>' +
                    '<span class="checkbox-label-help"></span>' +
                '</div>' +
           '</li>' +
       '</ul>', element);
    assert.equal(false, element.find('input').is(':checked'));

    model.set({value: '2', label: 'b', visible: true, selected: true, help: 'help !', tags: ['tag1']}, 0);

    this.equalOuterHtml(
        '<ul>' +
            '<li class="checkbox-field" checklist-index="0" tags="tag1">' +
                '<input type="checkbox" value="2" checklist-index="0">' +
                '<div class="checkbox-label">' +
                    '<span class="checkbox-label-text">b</span>' +
                    '<span class="checkbox-label-help">help !</span>' +
                '</div>' +
            '</li>' +
        '</ul>', element);
    assert.equal(true, element.find('input').is(':checked'));
});

QUnit.test('creme.model.CheckListRenderer.remove', function(assert) {
    var model = new creme.model.Array([
        {value: '1', label: 'a', visible: true},
        {value: '2', label: 'b', visible: true}
    ]);
    var element = $('<ul></ul>');
    var renderer = new creme.model.CheckGroupListRenderer({
        target: element,
        model: model
    });

    renderer.redraw();

    this.equalOuterHtml(
       '<ul>' +
           '<li class="checkbox-field " checklist-index="0" tags="">' +
                '<input type="checkbox" value="1" checklist-index="0">' +
                '<div class="checkbox-label">' +
                    '<span class="checkbox-label-text">a</span>' +
                    '<span class="checkbox-label-help"></span>' +
                '</div>' +
           '</li>' +
           '<li class="checkbox-field " checklist-index="1" tags="">' +
               '<input type="checkbox" value="2" checklist-index="1">' +
               '<div class="checkbox-label">' +
                   '<span class="checkbox-label-text">b</span>' +
                   '<span class="checkbox-label-help"></span>' +
               '</div>' +
           '</li>' +
       '</ul>', element);

    model.removeAt(0);

    this.equalOuterHtml(
        '<ul>' +
            '<li class="checkbox-field " checklist-index="1" tags="">' +
                '<input type="checkbox" value="2" checklist-index="1">' +
                '<div class="checkbox-label">' +
                    '<span class="checkbox-label-text">b</span>' +
                    '<span class="checkbox-label-help"></span>' +
                '</div>' +
            '</li>' +
        '</ul>', element);
});

QUnit.test('creme.model.CheckListRenderer.parse', function(assert) {
    var renderer = new creme.model.CheckListRenderer();

    assert.deepEqual([
        {value: '1', label: 'a', help: undefined, disabled: false, selected: false, visible: true, readonly: false, tags: []},
        {value: '2', label: 'b', help: undefined, disabled: false, selected: true,  visible: true, readonly: false, tags: ['tag1']},
        {value: '3', label: 'c', help: undefined, disabled: true,  selected: false, visible: true, readonly: false, tags: ['tag2']},
        {value: '4', label: 'd', help: undefined, disabled: false, selected: false, visible: true, readonly: false, tags: []},
        {value: '5', label: 'e', help: 'help !', disabled: false, selected: false, visible: true, readonly: false, tags: []},
        {value: '6', label: 'f', help: undefined, disabled: false, selected: false, visible: true, readonly: true, tags: []},
        {value: '7', label: 'g', help: undefined, disabled: false, selected: true, visible: true, readonly: true, tags: []}
    ], renderer.parse($(
         '<ul>' +
              '<li class="checkbox-field" checklist-index="0">' +
                   '<input type="checkbox" value="1" checklist-index="0"/>' +
                   '<div class="checkbox-label">' +
                       '<span class="checkbox-label-text">a</span>' +
                   '</div>' +
              '</li>' +
              '<li class="checkbox-field" checklist-index="1" tags="tag1">' +
                   '<input type="checkbox" value="2" checklist-index="1" checked/>' +
                   '<div class="checkbox-label">' +
                       '<span class="checkbox-label-text">b</span>' +
                   '</div>' +
              '</li>' +
              '<li class="checkbox-field" checklist-index="2" tags="tag2" disabled>' +
                   '<input type="checkbox" value="3" checklist-index="2" disabled/>' +
                   '<div class="checkbox-label">' +
                       '<span class="checkbox-label-text" disabled>c</span>' +
                   '</div>' +
              '</li>' +
              '<li class="checkbox-field hidden" checklist-index="3">' +        // ignore visibility in parse !
                   '<input type="checkbox" value="4" checklist-index="3"/>' +
                   '<div class="checkbox-label">' +
                       '<span class="checkbox-label-text">d</span>' +
                   '</div>' +
              '</li>' +
              '<li class="checkbox-field" checklist-index="4">' +
                   '<input type="checkbox" value="5" checklist-index="4"/>' +
                   '<div class="checkbox-label">' +
                       '<span class="checkbox-label-text">e</span>' +
                       '<span class="checkbox-label-help">help !</span>' +
                   '</div>' +
               '</li>' +
               '<li class="checkbox-field" checklist-index="5" readonly>' +
                    '<input type="checkbox" value="6" checklist-index="5"/>' +
                    '<div class="checkbox-label">' +
                        '<span class="checkbox-label-text">f</span>' +
                    '</div>' +
               '</li>' +
               '<li class="checkbox-field" checklist-index="6" readonly>' +
                    '<input type="checkbox" value="7" checklist-index="6" checked/>' +
                    '<div class="checkbox-label">' +
                        '<span class="checkbox-label-text">g</span>' +
                    '</div>' +
               '</li>' +
         '</ul>')));
});

QUnit.test('creme.model.CheckGroupListRenderer.constructor', function(assert) {
    var model = new creme.model.Array();
    var element = $('<ul></ul>');
    var renderer = new creme.model.CheckGroupListRenderer({
        target: element,
        model: model
    });

    renderer.redraw();

    assert.equal('li', renderer.itemTag());
    assert.equal('ul', renderer.groupTag());
    assert.equal(false, renderer.disabled());
    assert.equal(model, renderer.model());
    assert.equal(element, renderer.target());

    renderer =  new creme.model.CheckGroupListRenderer({
        itemtag: 'div',
        grouptag: 'span',
        disabled: true
    });

    assert.equal('div', renderer.itemTag());
    assert.equal('span', renderer.groupTag());
    assert.equal(true, renderer.disabled());
    assert.equal(undefined, renderer.model());
    assert.equal(undefined, renderer.target());
});

QUnit.test('creme.model.CheckGroupListRenderer.render', function(assert) {
    var model = new creme.model.Array([
        {value: '1', label: 'a', visible: true},
        {value: '2', label: 'b', visible: true, selected: true, tags: ['tag1']},
        {group: 'group1', value: '3', label: 'c', visible: true, disabled: true, tags: ['tag2']},
        {group: 'group2', value: '4', label: 'd', visible: false},
        {group: 'group2', value: '5', label: 'e', visible: true, help: 'help !'},
        {value: '6', label: 'f', visible: true, readonly: true},
        {value: '7', label: 'g', visible: true, selected: true, readonly: true}
    ]);
    var element = $('<ul></ul>');
    var renderer = new creme.model.CheckGroupListRenderer({
        target: element,
        model: model
    });

    renderer.redraw();

    this.equalOuterHtml(
       '<ul>' +
           '<li class="checkbox-field " checklist-index="0" tags="">' +
                '<input type="checkbox" value="1" checklist-index="0">' +
                '<div class="checkbox-label">' +
                    '<span class="checkbox-label-text">a</span>' +
                    '<span class="checkbox-label-help"></span>' +
                '</div>' +
           '</li>' +
           '<li class="checkbox-field " checklist-index="1" tags="tag1">' +
                '<input type="checkbox" value="2" checklist-index="1" checked>' +
                '<div class="checkbox-label">' +
                    '<span class="checkbox-label-text">b</span>' +
                    '<span class="checkbox-label-help"></span>' +
                '</div>' +
           '</li>' +
           '<ul class="checkbox-group" label="group1">' +
               '<li class="checkbox-group-header">group1</li>' +
               '<li class="checkbox-field " checklist-index="2" tags="tag2" disabled>' +
                    '<input type="checkbox" value="3" checklist-index="2" disabled>' +
                    '<div class="checkbox-label">' +
                        '<span class="checkbox-label-text" disabled>c</span>' +
                        '<span class="checkbox-label-help" disabled></span>' +
                    '</div>' +
               '</li>' +
           '</ul>' +
           '<ul class="checkbox-group" label="group2">' +
               '<li class="checkbox-group-header">group2</li>' +
               '<li class="checkbox-field hidden" checklist-index="3" tags="">' +        // ignore visibility in parse !
                   '<input type="checkbox" value="4" checklist-index="3">' +
                   '<div class="checkbox-label">' +
                       '<span class="checkbox-label-text">d</span>' +
                       '<span class="checkbox-label-help"></span>' +
                   '</div>' +
               '</li>' +
               '<li class="checkbox-field " checklist-index="4" tags="">' +
                   '<input type="checkbox" value="5" checklist-index="4">' +
                   '<div class="checkbox-label">' +
                       '<span class="checkbox-label-text">e</span>' +
                       '<span class="checkbox-label-help">help !</span>' +
                   '</div>' +
               '</li>' +
            '</ul>' +
            '<li class="checkbox-field " checklist-index="5" tags="" disabled readonly>' +
                 '<input type="checkbox" value="6" checklist-index="5" disabled>' +
                 '<div class="checkbox-label">' +
                     '<span class="checkbox-label-text" disabled>f</span>' +
                     '<span class="checkbox-label-help" disabled></span>' +
                 '</div>' +
            '</li>' +
            '<li class="checkbox-field " checklist-index="6" tags="" disabled readonly>' +
                 '<input type="checkbox" value="7" checklist-index="6" disabled checked>' +
                 '<div class="checkbox-label">' +
                     '<span class="checkbox-label-text" disabled>g</span>' +
                     '<span class="checkbox-label-help" disabled></span>' +
                 '</div>' +
            '</li>' +
        '</ul>', element);
});

QUnit.test('creme.model.CheckGroupListRenderer.update', function(assert) {
    var model = new creme.model.Array([
        {value: '1', label: 'a', visible: true}
    ]);
    var element = $('<ul></ul>');
    var renderer = new creme.model.CheckGroupListRenderer({
        target: element,
        model: model
    });

    renderer.redraw();

    this.equalOuterHtml(
       '<ul>' +
           '<li class="checkbox-field " checklist-index="0" tags="">' +
                '<input type="checkbox" value="1" checklist-index="0">' +
                '<div class="checkbox-label">' +
                    '<span class="checkbox-label-text">a</span>' +
                    '<span class="checkbox-label-help"></span>' +
                '</div>' +
           '</li>' +
       '</ul>', element);
    assert.equal(false, element.find('input').is(':checked'));

    model.set({value: '2', label: 'b', visible: true, selected: true, help: 'help !', tags: ['tag1']}, 0);

    this.equalOuterHtml(
        '<ul>' +
            '<li class="checkbox-field" checklist-index="0" tags="tag1">' +
                '<input type="checkbox" value="2" checklist-index="0">' +
                '<div class="checkbox-label">' +
                    '<span class="checkbox-label-text">b</span>' +
                    '<span class="checkbox-label-help">help !</span>' +
                '</div>' +
            '</li>' +
        '</ul>', element);
    assert.equal(true, element.find('input').is(':checked'));
});

QUnit.test('creme.model.CheckGroupListRenderer.update (group)', function(assert) {
    var model = new creme.model.Array([
        {value: '1', label: 'a', visible: true}
    ]);
    var element = $('<ul></ul>');
    var renderer = new creme.model.CheckGroupListRenderer({
        target: element,
        model: model
    });

    renderer.redraw();

    this.equalOuterHtml(
       '<ul>' +
           '<li class="checkbox-field " checklist-index="0" tags="">' +
                '<input type="checkbox" value="1" checklist-index="0">' +
                '<div class="checkbox-label">' +
                    '<span class="checkbox-label-text">a</span>' +
                    '<span class="checkbox-label-help"></span>' +
                '</div>' +
           '</li>' +
       '</ul>', element);
    assert.equal(false, element.find('input').is(':checked'));

    model.set({group: 'group1', value: '2', label: 'b', visible: true, selected: true, help: 'help !', tags: ['tag1']}, 0);

    this.equalOuterHtml(
        '<ul>' +
            '<ul class="checkbox-group" label="group1">' +
                '<li class="checkbox-group-header">group1</li>' +
                '<li class="checkbox-field" checklist-index="0" tags="tag1">' +
                    '<input type="checkbox" value="2" checklist-index="0">' +
                    '<div class="checkbox-label">' +
                        '<span class="checkbox-label-text">b</span>' +
                        '<span class="checkbox-label-help">help !</span>' +
                    '</div>' +
                '</li>' +
            '</ul>' +
        '</ul>', element);
    assert.equal(true, element.find('input').is(':checked'));
});

QUnit.test('creme.model.CheckGroupListRenderer.remove', function(assert) {
    var model = new creme.model.Array([
        {group: 'group1', value: '1', label: 'a', visible: true},
        {group: 'group1', value: '2', label: 'b', visible: true}
    ]);
    var element = $('<ul></ul>');
    var renderer = new creme.model.CheckGroupListRenderer({
        target: element,
        model: model
    });

    renderer.redraw();

    this.equalOuterHtml(
       '<ul>' +
           '<ul class="checkbox-group" label="group1">' +
               '<li class="checkbox-group-header">group1</li>' +
               '<li class="checkbox-field " checklist-index="0" tags="">' +
                    '<input type="checkbox" value="1" checklist-index="0">' +
                    '<div class="checkbox-label">' +
                        '<span class="checkbox-label-text">a</span>' +
                        '<span class="checkbox-label-help"></span>' +
                    '</div>' +
               '</li>' +
               '<li class="checkbox-field " checklist-index="1" tags="">' +
                   '<input type="checkbox" value="2" checklist-index="1">' +
                   '<div class="checkbox-label">' +
                       '<span class="checkbox-label-text">b</span>' +
                       '<span class="checkbox-label-help"></span>' +
                   '</div>' +
               '</li>' +
           '</ul>' +
       '</ul>', element);

    model.removeAt(0);

    this.equalOuterHtml(
        '<ul>' +
            '<ul class="checkbox-group" label="group1">' +
                '<li class="checkbox-group-header">group1</li>' +
                '<li class="checkbox-field " checklist-index="1" tags="">' +
                    '<input type="checkbox" value="2" checklist-index="1">' +
                    '<div class="checkbox-label">' +
                        '<span class="checkbox-label-text">b</span>' +
                        '<span class="checkbox-label-help"></span>' +
                    '</div>' +
                '</li>' +
            '</ul>' +
        '</ul>', element);
});

QUnit.test('creme.model.CheckGroupListRenderer.remove (empty group)', function(assert) {
    var model = new creme.model.Array([
        {group: 'group1', value: '1', label: 'a', visible: true},
        {group: 'group2', value: '2', label: 'b', visible: true}
    ]);
    var element = $('<ul></ul>');
    var renderer = new creme.model.CheckGroupListRenderer({
        target: element,
        model: model
    });

    renderer.redraw();

    this.equalOuterHtml(
       '<ul>' +
           '<ul class="checkbox-group" label="group1">' +
               '<li class="checkbox-group-header">group1</li>' +
               '<li class="checkbox-field " checklist-index="0" tags="">' +
                    '<input type="checkbox" value="1" checklist-index="0">' +
                    '<div class="checkbox-label">' +
                        '<span class="checkbox-label-text">a</span>' +
                        '<span class="checkbox-label-help"></span>' +
                    '</div>' +
               '</li>' +
           '</ul>' +
           '<ul class="checkbox-group" label="group2">' +
               '<li class="checkbox-group-header">group2</li>' +
               '<li class="checkbox-field " checklist-index="1" tags="">' +
                   '<input type="checkbox" value="2" checklist-index="1">' +
                   '<div class="checkbox-label">' +
                       '<span class="checkbox-label-text">b</span>' +
                       '<span class="checkbox-label-help"></span>' +
                   '</div>' +
               '</li>' +
           '</ul>' +
       '</ul>', element);

    model.removeAt(0);

    this.equalOuterHtml(
        '<ul>' +
            '<ul class="checkbox-group" label="group2">' +
                '<li class="checkbox-group-header">group2</li>' +
                '<li class="checkbox-field " checklist-index="1" tags="">' +
                    '<input type="checkbox" value="2" checklist-index="1">' +
                    '<div class="checkbox-label">' +
                        '<span class="checkbox-label-text">b</span>' +
                        '<span class="checkbox-label-help"></span>' +
                    '</div>' +
                '</li>' +
            '</ul>' +
        '</ul>', element);
});

QUnit.test('creme.model.CheckGroupListRenderer.parse', function(assert) {
    var renderer = new creme.model.CheckGroupListRenderer();

    assert.deepEqual([
        {group: undefined, value: '1', label: 'a', help: undefined, disabled: false, selected: false, visible: true, readonly: false, tags: []},
        {group: undefined, value: '2', label: 'b', help: undefined, disabled: false, selected: true,  visible: true, readonly: false, tags: ['tag1']},
        {group: 'group1', value: '3', label: 'c', help: undefined, disabled: true,  selected: false, visible: true, readonly: false, tags: ['tag2']},
        {group: 'group2', value: '4', label: 'd', help: undefined, disabled: false, selected: false, visible: true, readonly: false, tags: []},
        {group: 'group2', value: '5', label: 'e', help: 'help !', disabled: false, selected: false, visible: true, readonly: false, tags: []},
        {group: undefined, value: '6', label: 'f', help: undefined, disabled: false, selected: false, visible: true, readonly: true, tags: []},
        {group: undefined, value: '7', label: 'g', help: undefined, disabled: false, selected: true, visible: true, readonly: true, tags: []}
    ], renderer.parse($(
        '<ul>' +
            '<li class="checkbox-field" checklist-index="0">' +
                 '<input type="checkbox" value="1" checklist-index="0">' +
                 '<div class="checkbox-label">' +
                     '<span class="checkbox-label-text">a</span>' +
                 '</div>' +
            '</li>' +
            '<li class="checkbox-field" checklist-index="1" tags="tag1">' +
                 '<input type="checkbox" value="2" checklist-index="1" checked>' +
                 '<div class="checkbox-label">' +
                     '<span class="checkbox-label-text">b</span>' +
                 '</div>' +
            '</li>' +
            '<ul class="checkbox-group" label="group1">' +
                '<li class="checkbox-group-header">group1</li>' +
                '<li class="checkbox-field" checklist-index="2" tags="tag2" disabled>' +
                     '<input type="checkbox" value="3" checklist-index="2" disabled>' +
                     '<div class="checkbox-label">' +
                         '<span class="checkbox-label-text" disabled>c</span>' +
                     '</div>' +
                '</li>' +
            '</ul>' +
            '<ul class="checkbox-group" label="group2">' +
                '<li class="checkbox-group-header">group2</li>' +
                '<li class="checkbox-field hidden" checklist-index="3">' +        // ignore visibility in parse !
                    '<input type="checkbox" value="4" checklist-index="3">' +
                    '<div class="checkbox-label">' +
                        '<span class="checkbox-label-text">d</span>' +
                    '</div>' +
                '</li>' +
                '<li class="checkbox-field" checklist-index="4">' +
                    '<input type="checkbox" value="5" checklist-index="4">' +
                    '<div class="checkbox-label">' +
                        '<span class="checkbox-label-text">e</span>' +
                        '<span class="checkbox-label-help">help !</span>' +
                    '</div>' +
                '</li>' +
             '</ul>' +
             '<li class="checkbox-field" checklist-index="5" readonly>' +
                  '<input type="checkbox" value="6" checklist-index="5">' +
                  '<div class="checkbox-label">' +
                      '<span class="checkbox-label-text">f</span>' +
                  '</div>' +
             '</li>' +
             '<li class="checkbox-field" checklist-index="6" readonly>' +
                  '<input type="checkbox" value="7" checklist-index="6" checked>' +
                  '<div class="checkbox-label">' +
                      '<span class="checkbox-label-text">g</span>' +
                  '</div>' +
             '</li>' +
         '</ul>')));
});

}(jQuery));
