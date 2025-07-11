/* globals QUnitConsoleMixin BigInt */

(function() {

QUnit.module("underscore-json", new QUnitMixin(QUnitConsoleMixin, {
    parseHTML: function(html) {
        var template = document.createElement('template');
        template.innerHTML = html;
        return template.content.childNodes.length > 1 ? template.content.childNodes : template.content.firstChild;
    }
}));

QUnit.test('isJSON', function(assert) {
    assert.equal(_.isJSON(''), false);
    assert.equal(_.isJSON('null'), false);
    assert.equal(_.isJSON('[a, b]'), false);
    assert.equal(_.isJSON('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]'), false);

    assert.equal(_.isJSON('""'), true);
    assert.equal(_.isJSON('{"a": 12, "b": [1, 2], "c": {"c1": 74, "c2": [8]}}'), true);
});

QUnit.test('cleanJSON', function(assert) {
    assert.equal(_.cleanJSON(''), undefined);
    assert.equal(_.cleanJSON('""'), '');
    assert.equal(_.cleanJSON('12'), 12);

    assert.deepEqual(_.cleanJSON('{"a": 12}'), {"a": 12});

    assert.deepEqual(_.cleanJSON('{"a": "2025-03-11"}', function(key, value, context) {
        return (key === 'a') ? new Date(value) : value;
    }), {a: new Date('2025-03-11')});

    assert.deepEqual(_.cleanJSON('{"a": 12345678901234567890}', function(key, value, context) {
        return (key === 'a') ? BigInt(context.source) : value;
    }), {a: BigInt('12345678901234567890')});
});

QUnit.test('readJSONScriptText (invalid)', function(assert) {
    assert.equal('', _.readJSONScriptText(''));
    assert.equal('', _.readJSONScriptText('#unknown'));

    this.resetMockConsoleWarnCalls();

    // wrong element type
    var invalidTag = this.parseHTML('<div>This not a script</div>');
    assert.equal('', _.readJSONScriptText(invalidTag));

    assert.deepEqual([
        ['This element is not a JSON script']
    ], this.mockConsoleWarnCalls().map(function(e) { return e.slice(0, 1); }));

    this.resetMockConsoleWarnCalls();

    // wrong script type
    invalidTag = this.parseHTML('<script type="application/csv">{}</script>');
    assert.equal('', _.readJSONScriptText(invalidTag));

    assert.deepEqual([
        ['This element is not a JSON script']
    ], this.mockConsoleWarnCalls().map(function(e) { return e.slice(0, 1); }));

    this.resetMockConsoleWarnCalls();

    assert.equal('<!-- ->', _.readJSONScriptText(this.parseHTML('<script type="text/json"><!-- -></script>')));
    assert.deepEqual([
        ['Please use html comment <!-- --> within JSON <script> tag to prevent some browsers to interpret it as javascript']
    ], this.mockConsoleWarnCalls());

    this.resetMockConsoleWarnCalls();

    assert.equal('<!--', _.readJSONScriptText(this.parseHTML('<script type="text/json"><!--</script>')));
    assert.deepEqual([
        ['Please use html comment <!-- --> within JSON <script> tag to prevent some browsers to interpret it as javascript']
    ], this.mockConsoleWarnCalls());

    this.resetMockConsoleWarnCalls();

    assert.equal('-->', _.readJSONScriptText(this.parseHTML('<script type="text/json">--></script>')));
    assert.deepEqual([
        ['Please use html comment <!-- --> within JSON <script> tag to prevent some browsers to interpret it as javascript']
    ], this.mockConsoleWarnCalls());

    this.resetMockConsoleWarnCalls();

    assert.equal('{}', _.readJSONScriptText(this.parseHTML('<script type="text/json">{}</script>')));
    assert.deepEqual([
        ['Please use html comment <!-- --> within JSON <script> tag to prevent some browsers to interpret it as javascript']
    ], this.mockConsoleWarnCalls());
});

QUnit.test('readJSONScriptText (ignore linebreaks)', function(assert) {
    assert.equal('', _.readJSONScriptText(this.parseHTML('<script type="text/json"></script>')));
    assert.equal('', _.readJSONScriptText(this.parseHTML('<script type="text/json"><!-- --></script>')));
    assert.equal('', _.readJSONScriptText(this.parseHTML('<script type="text/json"><!-- -->\n</script>')));

    assert.equal('<!-- ->', _.readJSONScriptText(this.parseHTML('<script type="text/json"><!-- -></script>')));

    assert.equal('{}', _.readJSONScriptText(this.parseHTML('<script type="text/json"><!-- {} --></script>')));
    assert.equal('{}', _.readJSONScriptText(this.parseHTML('<script type="text/json">\n<!-- {} -->\n\n</script>')));

    assert.equal('{}', _.readJSONScriptText(this.parseHTML('<script type="application/json"><!-- {} --></script>')));
    assert.equal('{}', _.readJSONScriptText(this.parseHTML('<script type="application/json">\n<!-- {} -->\n\n</script>')));
});

QUnit.test('readJSONScriptText (escaping)', function(assert) {
    var script = this.parseHTML(
        '<script id="mydata" type="application/json">\n<!-- {"a": 12, "b": "--\\u003ealert();\\u003cscript/\\u003e"} -->\n\n</script>'
    );

    this.qunitFixture().append(script);

    assert.equal('{"a": 12, "b": "-->alert();<script/>"}', _.readJSONScriptText(script));
    assert.equal('{"a": 12, "b": "-->alert();<script/>"}', _.readJSONScriptText('#mydata'));
});

QUnit.parameterize('cleanJSONScript', [
    ['', undefined],
    ['""', ''],
    ['{"a": 12, "today": "2025-04-11"}', {a: 12, today: new Date('2025-04-11')}],
    ['{"a": 12, "b": "--\\u003ealert();\\u003cscript/\\u003e"}', {a: 12, b: "-->alert();<script/>"}]
], function(content, expected, assert) {
    var script = this.parseHTML(
        '<script id="mydata" type="application/json">\n<!-- ${content} -->\n\n</script>'.template({
            content: content
        })
    );

    this.qunitFixture().append(script);

    assert.deepEqual(expected, _.cleanJSONScript(script, function(key, value, context) {
        return (key === 'today') ? new Date(value) : value;
    }));

    assert.deepEqual(expected, _.cleanJSONScript('#mydata', function(key, value, context) {
        return (key === 'today') ? new Date(value) : value;
    }));
});

}());
