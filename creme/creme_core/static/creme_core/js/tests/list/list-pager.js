(function($) {

QUnit.module("creme.list.pager", new QUnitMixin(QUnitEventMixin, {
    createPagerElement: function(links) {
        var html = '<div>${links}</div>'.template({
            links: links || []
        });

        return $(html).appendTo(this.qunitFixture());
    }
}));

QUnit.test('creme.list.Pager.bind', function(assert) {
    var pager = new creme.list.Pager();
    var element = this.createPagerElement();

    assert.equal(false, pager.isBound());
    pager.bind(element);
    assert.equal(true, pager.isBound());
});

QUnit.test('creme.list.Pager.bind (already bound)', function(assert) {
    var pager = new creme.list.Pager();
    var element = this.createPagerElement();

    pager.bind(element);
    assert.equal(true, pager.isBound());

    this.assertRaises(function() {
        pager.bind(element);
    }, Error, 'Error: Pager is already bound');
});

QUnit.test('creme.list.Pager (link, no data)', function(assert) {
    var pager = new creme.list.Pager();
    var element = this.createPagerElement([
        '<a class="pager-link"></a>'
    ]);

    pager.bind(element).on('refresh', this.mockListener('refresh'));

    assert.equal(true, pager.isBound());
    assert.deepEqual([], this.mockListenerCalls('refresh'));

    element.find('.pager-link').trigger('click');
    assert.deepEqual([], this.mockListenerCalls('refresh'));
});

QUnit.test('creme.list.Pager (link)', function(assert) {
    var pager = new creme.list.Pager();
    var element = this.createPagerElement([
        '<a class="pager-link link-a" data-page="1"></a>',
        '<a class="pager-link link-b" data-page="{&quot;type&quot;: &quot;forward&quot;, &quot;value&quot;:2}"></a>'
    ]);

    pager.bind(element).on('refresh', this.mockListener('refresh'));

    assert.equal(true, pager.isBound());
    assert.deepEqual([], this.mockListenerCalls('refresh'));

    element.find('.link-a').trigger('click');
    assert.deepEqual([
        ['refresh', '1']
    ], this.mockListenerCalls('refresh'));

    element.find('.link-b').trigger('click');
    assert.deepEqual([
        ['refresh', '1'],
        ['refresh', '{"type": "forward", "value":2}']
    ], this.mockListenerCalls('refresh'));
});

QUnit.test('creme.list.Pager (link, disabled)', function(assert) {
    var pager = new creme.list.Pager();
    var element = this.createPagerElement([
        '<a class="pager-link link-a is-disabled" data-page="1"></a>'
    ]);

    pager.bind(element).on('refresh', this.mockListener('refresh'));

    assert.equal(true, pager.isBound());
    assert.deepEqual([], this.mockListenerCalls('refresh'));

    element.find('.link-a').trigger('click');
    assert.deepEqual([], this.mockListenerCalls('refresh'));
});

QUnit.test('creme.list.Pager (choose, toggle input)', function(assert) {
    var pager = new creme.list.Pager();
    var element = this.createPagerElement([
        '<span class="pager-link-choose">' +
            '<span>…</span>' +
            '<input type="text" min="1" max="5" data-initial-value="2" />' +
        '</span>'
    ]);

    pager.bind(element).on('refresh', this.mockListener('refresh'));

    var link = element.find('.pager-link-choose');
    var input = link.find('input');

    assert.equal('', input.val());
    assert.equal(false, input.is('.invalid-page'));
    assert.equal(false, link.is('.active'));

    link.trigger('click');

    assert.equal('2', input.val());
    assert.equal(false, input.is('.invalid-page'));
    assert.equal(true, link.is('.active'));

    link.trigger('click');

    assert.equal('2', input.val());
    assert.equal(false, input.is('.invalid-page'));
    assert.equal(true, link.is('.active'));

    input.trigger('focusout');

    assert.equal('2', input.val());
    assert.equal(false, input.is('.invalid-page'));
    assert.equal(false, link.is('.active'));

    assert.deepEqual([], this.mockListenerCalls('refresh'));
});

QUnit.test('creme.list.Pager (choose, input value)', function(assert) {
    var pager = new creme.list.Pager({
        debounceDelay: 0
    });
    var element = this.createPagerElement([
        '<span class="pager-link-choose">' +
            '<span>…</span>' +
            '<input type="text" min="1" max="5" data-initial-value="2" />' +
        '</span>'
    ]);

    pager.bind(element).on('refresh', this.mockListener('refresh'));

    var link = element.find('.pager-link-choose');
    var input = link.find('input');

    assert.equal('', input.val());
    assert.equal(false, input.is('.invalid-page'));
    assert.equal(false, element.is('.active'));

    link.trigger('click');

    assert.equal('2', input.val());
    assert.equal(false, input.is('.invalid-page'));
    assert.equal(true, link.is('.active'));

    input.val('3').trigger('change');
    assert.equal(false, input.is('.invalid-page'));

    input.val('6').trigger('change');
    assert.equal(true, input.is('.invalid-page'));

    input.val('1').trigger('change');
    assert.equal(false, input.is('.invalid-page'));

    input.val('zzz').trigger('change');
    assert.equal(true, input.is('.invalid-page'));

    input.val('1').trigger('change');
    assert.equal(false, input.is('.invalid-page'));

    input.val('0').trigger('change');
    assert.equal(true, input.is('.invalid-page'));

    assert.deepEqual([], this.mockListenerCalls('refresh'));
});

QUnit.test('creme.list.Pager (choose, keyup enter)', function(assert) {
    var pager = new creme.list.Pager();
    var element = this.createPagerElement([
        '<span class="pager-link-choose">' +
            '<span>…</span>' +
            '<input type="text" min="1" max="5" data-initial-value="2" />' +
        '</span>'
    ]);

    pager.bind(element).on('refresh', this.mockListener('refresh'));

    var link = element.find('.pager-link-choose');
    var input = link.find('input');

    assert.equal('', input.val());
    assert.equal(false, input.is('.invalid-page'));
    assert.equal(false, element.is('.active'));

    link.trigger('click');

    assert.equal('2', input.val());
    assert.equal(false, input.is('.invalid-page'));
    assert.equal(true, link.is('.active'));

    input.trigger($.Event("keyup", {keyCode: 13}));

    assert.equal(true, link.is('.active'));
    assert.deepEqual([
        ['refresh', 2]
    ], this.mockListenerCalls('refresh'));
});

QUnit.test('creme.list.Pager (choose, keyup escape)', function(assert) {
    var pager = new creme.list.Pager();
    var element = this.createPagerElement([
        '<span class="pager-link-choose">' +
            '<span>…</span>' +
            '<input type="text" min="1" max="5" data-initial-value="2" />' +
        '</span>'
    ]);

    pager.bind(element).on('refresh', this.mockListener('refresh'));

    var link = element.find('.pager-link-choose');
    var input = link.find('input');

    assert.equal('', input.val());
    assert.equal(false, input.is('.invalid-page'));
    assert.equal(false, element.is('.active'));

    link.trigger('click');

    assert.equal('2', input.val());
    assert.equal(false, input.is('.invalid-page'));
    assert.equal(true, link.is('.active'));

    input.trigger($.Event("keyup", {keyCode: 27}));

    assert.equal(false, link.is('.active'));
    assert.deepEqual([], this.mockListenerCalls('refresh'));
});

}(jQuery));
