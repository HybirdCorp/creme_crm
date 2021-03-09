(function($) {

QUnit.module("creme.list.pager", new QUnitMixin(QUnitEventMixin, {
    createPagerElement: function(links) {
        var html = '<div>${links}</div>'.template({
            links: links || []
        });

        return $(html).appendTo(this.qunitFixture());
    }
}));

QUnit.test('creme.list.Pager.bind', function() {
    var pager = new creme.list.Pager();
    var element = this.createPagerElement();

    equal(false, pager.isBound());
    pager.bind(element);
    equal(true, pager.isBound());
});

QUnit.test('creme.list.Pager.bind (already bound)', function() {
    var pager = new creme.list.Pager();
    var element = this.createPagerElement();

    pager.bind(element);
    equal(true, pager.isBound());

    this.assertRaises(function() {
        pager.bind(element);
    }, Error, 'Error: Pager is already bound');
});

QUnit.test('creme.list.Pager (link, no data)', function() {
    var pager = new creme.list.Pager();
    var element = this.createPagerElement([
        '<a class="pager-link"></a>'
    ]);

    pager.bind(element).on('refresh', this.mockListener('refresh'));

    equal(true, pager.isBound());
    deepEqual([], this.mockListenerCalls('refresh'));

    element.find('.pager-link').trigger('click');
    deepEqual([], this.mockListenerCalls('refresh'));
});

QUnit.test('creme.list.Pager (link)', function() {
    var pager = new creme.list.Pager();
    var element = this.createPagerElement([
        '<a class="pager-link link-a" data-page="1"></a>',
        '<a class="pager-link link-b" data-page="{&quot;type&quot;: &quot;forward&quot;, &quot;value&quot;:2}"></a>'
    ]);

    pager.bind(element).on('refresh', this.mockListener('refresh'));

    equal(true, pager.isBound());
    deepEqual([], this.mockListenerCalls('refresh'));

    element.find('.link-a').trigger('click');
    deepEqual([
        ['refresh', '1']
    ], this.mockListenerCalls('refresh'));

    element.find('.link-b').trigger('click');
    deepEqual([
        ['refresh', '1'],
        ['refresh', '{"type": "forward", "value":2}']
    ], this.mockListenerCalls('refresh'));
});

QUnit.test('creme.list.Pager (link, disabled)', function() {
    var pager = new creme.list.Pager();
    var element = this.createPagerElement([
        '<a class="pager-link link-a is-disabled" data-page="1"></a>'
    ]);

    pager.bind(element).on('refresh', this.mockListener('refresh'));

    equal(true, pager.isBound());
    deepEqual([], this.mockListenerCalls('refresh'));

    element.find('.link-a').trigger('click');
    deepEqual([], this.mockListenerCalls('refresh'));
});

QUnit.test('creme.list.Pager (choose, toggle input)', function() {
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

    equal('', input.val());
    equal(false, input.is('.invalid-page'));
    equal(false, link.is('.active'));

    link.trigger('click');

    equal('2', input.val());
    equal(false, input.is('.invalid-page'));
    equal(true, link.is('.active'));

    link.trigger('click');

    equal('2', input.val());
    equal(false, input.is('.invalid-page'));
    equal(true, link.is('.active'));

    input.focusout();

    equal('2', input.val());
    equal(false, input.is('.invalid-page'));
    equal(false, link.is('.active'));

    deepEqual([], this.mockListenerCalls('refresh'));
});

QUnit.test('creme.list.Pager (choose, input value)', function() {
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

    equal('', input.val());
    equal(false, input.is('.invalid-page'));
    equal(false, element.is('.active'));

    link.trigger('click');

    equal('2', input.val());
    equal(false, input.is('.invalid-page'));
    equal(true, link.is('.active'));

    input.val('3').trigger('change');
    equal(false, input.is('.invalid-page'));

    input.val('6').trigger('change');
    equal(true, input.is('.invalid-page'));

    input.val('1').trigger('change');
    equal(false, input.is('.invalid-page'));

    input.val('zzz').trigger('change');
    equal(true, input.is('.invalid-page'));

    input.val('1').trigger('change');
    equal(false, input.is('.invalid-page'));

    input.val('0').trigger('change');
    equal(true, input.is('.invalid-page'));

    deepEqual([], this.mockListenerCalls('refresh'));
});

QUnit.test('creme.list.Pager (choose, keyup enter)', function() {
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

    equal('', input.val());
    equal(false, input.is('.invalid-page'));
    equal(false, element.is('.active'));

    link.trigger('click');

    equal('2', input.val());
    equal(false, input.is('.invalid-page'));
    equal(true, link.is('.active'));

    input.trigger($.Event("keyup", {keyCode: 13}));

    equal(true, link.is('.active'));
    deepEqual([
        ['refresh', 2]
    ], this.mockListenerCalls('refresh'));
});

QUnit.test('creme.list.Pager (choose, keyup escape)', function() {
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

    equal('', input.val());
    equal(false, input.is('.invalid-page'));
    equal(false, element.is('.active'));

    link.trigger('click');

    equal('2', input.val());
    equal(false, input.is('.invalid-page'));
    equal(true, link.is('.active'));

    input.trigger($.Event("keyup", {keyCode: 27}));

    equal(false, link.is('.active'));
    deepEqual([], this.mockListenerCalls('refresh'));
});

}(jQuery));
