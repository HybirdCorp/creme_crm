module("creme.widgets.base.js", {
  setup: function() {},
  teardown: function() {}

});

function assertHTMLEqual(expected, value) {
    deepEqual($(expected).html(), $(value).html());
}

test('creme.widget.parseopt (no default options)', function() {
    expect(3);
    var options = creme.widget.parseopt($('<div/>'));
    deepEqual(options, {});

    options = creme.widget.parseopt($('<div attr1="val1" attr2="val2" attr3="val3"/>'));
    deepEqual(options, {});

    options = creme.widget.parseopt($('<div attr1="val1" attr2="val2" attr3="val3"/>'), {}, {}, []);
    deepEqual(options, {});
});

test('creme.widget.parseopt (default options)', function() {
    var options = creme.widget.parseopt($('<div/>'), {attr1:'default1', attr2:'default2'});
    deepEqual(options, {attr1:'default1', attr2:'default2'});

    options = creme.widget.parseopt($('<div attr1="val1" attr2="val2" attr3="val3"/>'), {attr1:'default1', attr2:'default2'});
    deepEqual(options, {attr1:'val1', attr2:'val2'});

    options = creme.widget.parseopt($('<div attr1="val1" attr3="val3"/>'), {attr1:'default1', attr2:'default2'});
    deepEqual(options, {attr1:'val1', attr2:'default2'});
});

test('creme.widget.parseopt (custom options)', function() {
    var options = creme.widget.parseopt($('<div/>'), {}, {}, ['custom1', 'custom2']);
    deepEqual(options, {});

    options = creme.widget.parseopt($('<div attr1="val1" attr2="val2" custom1="val3"/>'), {}, {}, ['custom1', 'custom2']);
    deepEqual(options, {custom1:'val3'});

    options = creme.widget.parseopt($('<div attr1="val1" custom1="val3"/>'), {attr1:'default1', attr2:'default2', custom2:'default3'}, {}, ['custom1', 'custom2']);
    deepEqual(options, {attr1:'val1', attr2:'default2', custom1:'val3', custom2:'default3'});
});

test('creme.widget.parseopt (custom values)', function() {
    var options = creme.widget.parseopt($('<div/>'), {}, {attr1:'value1'}, ['custom1', 'custom2']);
    deepEqual(options, {attr1:'value1'});

    options = creme.widget.parseopt($('<div/>'), {}, {custom1:'value1', attr1:'value2'}, ['custom1', 'custom2']);
    deepEqual(options, {custom1:'value1', attr1:'value2'});

    options = creme.widget.parseopt($('<div attr1="val1" attr2="val2" custom1="val3"/>'), {}, {custom1:'value1'}, ['custom1', 'custom2']);
    deepEqual(options, {custom1:'value1'});

    options = creme.widget.parseopt($('<div attr1="val1" custom1="val3"/>'), {attr1:'default1', attr2:'default2', custom2:'default3'}, {attr1:'value1'}, ['custom1', 'custom2']);
    deepEqual(options, {attr1:'value1', attr2:'default2', custom1:'val3', custom2:'default3'});
});

test('creme.widget.parseattr (no exclusion)', function() {
    var attrs = creme.widget.parseattr($('<div/>'))
    deepEqual(attrs, {});

    attrs = creme.widget.parseattr($('<div attr1="val1" attr2="val2" attr3="val3"/>'));
    deepEqual(attrs, {attr1:'val1', attr2:'val2', attr3:'val3'});

    attrs = creme.widget.parseattr($('<div attr1="val1" attr2="val2" attr3="val3" widget="creme.widget"/>'));
    deepEqual(attrs, {attr1:'val1', attr2:'val2', attr3:'val3', widget:"creme.widget"});
});

test('creme.widget.parseattr (with exclusion)', function() {
    var attrs = creme.widget.parseattr($('<div/>'), {'attr2':''});
    deepEqual(attrs, {});

    attrs = creme.widget.parseattr($('<div attr1="val1" attr2="val2" attr3="val3"/>'), {'attr2':''});
    deepEqual(attrs, {attr1:'val1', attr3:'val3'});

    attrs = creme.widget.parseattr($('<div attr1="val1" attr2="val2" attr3="val3"/>'), ['attr1', 'attr3']);
    deepEqual(attrs, {attr2:'val2'});
});

test('creme.widget.template (template:no keys)', function() {
    var result = creme.widget.template('');
    equal(result, '');

    result = creme.widget.template('template without key');
    equal(result, 'template without key');

    result = creme.widget.template('template without key', {});
    equal(result, 'template without key');

    result = creme.widget.template('template without key', {'key1':'value1', 'key2':'value2'});
    equal(result, 'template without key');
});

test('creme.widget.template (template:keys, values: in template)', function() {
    var result = creme.widget.template('template with key1=${key1} and key2=${key2}, ${key1}');
    equal(result, 'template with key1=${key1} and key2=${key2}, ${key1}');

    result = creme.widget.template('template with key1=${key1} and key2=${key2}, ${key1}', {key1:'value1'});
    equal(result, 'template with key1=value1 and key2=${key2}, value1');

    result = creme.widget.template('template with key1=${key1} and key2=${key2}, ${key1}', {key2:'value2'});
    equal(result, 'template with key1=${key1} and key2=value2, ${key1}');

    result = creme.widget.template('template with key1=${key1} and key2=${key2}, ${key1}', {key1:'value1', key2:'value2'});
    equal(result, 'template with key1=value1 and key2=value2, value1');

    result = creme.widget.template('template with key1=${key1} and key2=${key2}, ${key1}', {key1:'value1', key2:undefined});
    equal(result, 'template with key1=value1 and key2=${key2}, value1');
});

test('creme.widget.template (template:keys, values: not in template)', function() {
    var result = creme.widget.template('template with key1=${key1} and key2=${key2}, ${key1}', {key3:'value3'});
    equal(result, 'template with key1=${key1} and key2=${key2}, ${key1}');

    result = creme.widget.template('template with key1=${key1} and key2=${key2}, ${key1}', {key1:'value1', key3:'value3'});
    equal(result, 'template with key1=value1 and key2=${key2}, value1');
});

test('creme.widget.parseval (parser: json, value: none)', function() {
    var result = creme.widget.parseval(undefined, creme.ajax.json.parse)
    equal(result, undefined);

    result = creme.widget.parseval(null, creme.ajax.json.parse)
    equal(result, null);

    result = creme.widget.parseval(undefined)
    equal(result, undefined);

    result = creme.widget.parseval(null)
    equal(result, null);
});

test('creme.widget.parseval (parser: json, value: object)', function() {
    var result = creme.widget.parseval({'a':2, 'b':3}, creme.ajax.json.parse)
    deepEqual(result, {'a':2, 'b':3});

    result = creme.widget.parseval({'a':2, 'b':3})
    deepEqual(result, {'a':2, 'b':3});

    result = creme.widget.parseval(15)
    deepEqual(result, 15);
});

test('creme.widget.parseval (parser: json, value: invalid json)', function() {
    var result = creme.widget.parseval('{"a":2, "b":3', creme.ajax.json.parse);
    equal(result, null);

    result = creme.widget.parseval('', creme.ajax.json.parse);
    equal(result, null);

    result = creme.widget.parseval('["a", 2', creme.ajax.json.parse);
    equal(result, null);

    result = creme.widget.parseval("15a335", creme.ajax.json.parse);
    equal(result, null);
});

test('creme.widget.parseval (parser: json, value: valid json)', function() {
    var result = creme.widget.parseval('{"a":2, "b":3}', creme.ajax.json.parse);
    deepEqual(result, {'a':2, 'b':3});

    result = creme.widget.parseval('""', creme.ajax.json.parse);
    deepEqual(result, "");

    result = creme.widget.parseval('["a", "b", 2]', creme.ajax.json.parse);
    deepEqual(result, ['a', 'b', 2]);

    result = creme.widget.parseval("15335", creme.ajax.json.parse);
    equal(result, 15335);
});

test('creme.widget.parseval (parser: none, value: invalid json)', function() {
    var result = creme.widget.parseval('{"a":2, "b":3}');
    equal(result, '{"a":2, "b":3}');

    result = creme.widget.parseval('["a", 2');
    equal(result, '["a", 2');
});

test('creme.widget.cleanval (parser: default, value: none)', function() {
    var result = creme.widget.cleanval(undefined);
    equal(result, undefined);

    result = creme.widget.cleanval(null);
    equal(result, null);
});

test('creme.widget.cleanval (parser: default, value: none, default value)', function() {
    var result = creme.widget.cleanval(undefined, 'default');
    equal(result, 'default');

    result = creme.widget.cleanval(null, 'default');
    equal(result, 'default');
});

test('creme.widget.cleanval (parser: none (json), value: object)', function() {
    var result = creme.widget.cleanval({'a':2, 'b':3})
    deepEqual(result, {'a':2, 'b':3});

    result = creme.widget.cleanval(['a', 2, 'b', 3])
    deepEqual(result, ['a', 2, 'b', 3]);
});

test('creme.widget.cleanval (parser: none (json), value: valid json)', function() {
    var result = creme.widget.cleanval('{"a":2, "b":3}');
    deepEqual(result, {'a':2, 'b':3});

    result = creme.widget.cleanval('""');
    deepEqual(result, "");

    result = creme.widget.cleanval('["a", "b", 2]');
    deepEqual(result, ['a', 'b', 2]);

    result = creme.widget.cleanval("15335");
    equal(result, 15335);
});

test('creme.widget.cleanval (parser: none (json), value: invalid json)', function() {
    var result = creme.widget.cleanval('{"a":2, "b":3');
    equal(result, null);

    result = creme.widget.cleanval('');
    equal(result, null);

    result = creme.widget.cleanval('["a", 2');
    equal(result, null);

    result = creme.widget.cleanval("15a335");
    equal(result, null);
});

test('creme.widget.cleanval (parser: none (json), value: invalid json, default value)', function() {
    var result = creme.widget.cleanval('{"a":2, "b":3', {"a":15});
    deepEqual(result, {"a":15});

    result = creme.widget.cleanval('', "");
    equal(result, "");

    result = creme.widget.cleanval('["a", 2', []);
    deepEqual(result, []);

    result = creme.widget.cleanval("15a335", 0);
    equal(result, 0);
});

test('creme.object.invoke', function() {
    equal(undefined, creme.object.invoke());
    equal(undefined, creme.object.invoke(undefined));
    equal(undefined, creme.object.invoke(null));

    equal(undefined, creme.object.invoke(null, 5.2));
    equal(undefined, creme.object.invoke(458, 5.2));
    equal(undefined, creme.object.invoke('test', 5.2));

    equal(-458, creme.object.invoke(function() {return -458;}));
    equal(5.2, creme.object.invoke(function(a) {return a;}, 5.2));
    deepEqual([5.2, 12.5], creme.object.invoke(function(a, b) {return [b, a];}, 12.5, 5.2));
});

test('creme.object.delegate', function() {
    equal(undefined, creme.object.delegate());
    equal(undefined, creme.object.delegate(undefined));
    equal(undefined, creme.object.delegate(null));

    var instance = {
        val: function() {return 12;},
        add: function(a, b) {return a + b;}
    };

    equal(undefined, creme.object.delegate(null, 'val'));
    equal(undefined, creme.object.delegate(undefined, 'val'));
    equal(undefined, creme.object.delegate(instance, 'unknown'));

    equal(12, creme.object.delegate(instance, 'val'));
    equal(7, creme.object.delegate(instance, 'add', 3, 4));
});

test('creme.object.isnone', function() {
    equal(creme.object.isnone(undefined), true);
    equal(creme.object.isnone(null), true);
    equal(creme.object.isnone({}), false);
    equal(creme.object.isnone([]), false);
    equal(creme.object.isnone(0), false);
    equal(creme.object.isnone(''), false);
});

test('creme.object.isempty', function() {
    equal(creme.object.isempty(undefined), true);
    equal(creme.object.isempty(null), true);
    equal(creme.object.isempty({}), true);
    equal(creme.object.isempty([]), true);
    equal(creme.object.isempty(''), true);

    equal(creme.object.isempty(0), false);
    equal(creme.object.isempty({a:12}), false);
    equal(creme.object.isempty([12]), false);
    equal(creme.object.isempty('a'), false);
});

test('creme.object.deferred (finished)', function() {
    var element = $('<div/>');
    var result = [];

    var deferred = creme.object.deferred_start(element, 'overlay', function() {result.push('done');}, 400);
    deepEqual(element.data('deferred__overlay'), deferred);
    deepEqual(result, []);

    stop(2);

    setTimeout(function() {
        deepEqual(element.data('deferred__overlay'), deferred);
        deepEqual(result, []);
        start();
    }, 90);

    setTimeout(function() {
        equal(element.data('deferred__overlay'), undefined);
        deepEqual(result, ['done']);
        start();
    }, 600);
});

test('creme.object.deferred (canceled)', function() {
    var element = $('<div/>');
    var result = [];

    var deferred = creme.object.deferred_start(element, 'overlay', function() {result.push['done']}, 200);
    deepEqual(deferred, element.data('deferred__overlay'));

    stop(2);

    setTimeout(function() {
        deepEqual(deferred, element.data('deferred__overlay'));
        deepEqual(result, []);
        deepEqual(deferred, creme.object.deferred_cancel(element, 'overlay'));

        equal(element.data('deferred__overlay'), undefined);
        deepEqual(result, []);
        start();
    }, 90);

    setTimeout(function() {
        equal(element.data('deferred__overlay'), undefined);
        deepEqual(result, []);
        start();
    }, 300);
});

test('creme.object.deferred (restarted)', function() {
    var element = $('<div/>');
    var result = [];

    var deferred = creme.object.deferred_start(element, 'overlay', function() {result.push('done');}, 200);
    deepEqual(deferred, element.data('deferred__overlay'));

    stop(3);

    setTimeout(function() {
        deepEqual(deferred, element.data('deferred__overlay'));
        deepEqual(result, []);
        notDeepEqual(creme.object.deferred_start(element, 'overlay', function() {result.push('done restarted');}, 500), deferred);

        notEqual(element.data('deferred__overlay'), undefined, 'replaced');
        deepEqual(result, []);
        start();
    }, 90);

    setTimeout(function() {
        notEqual(element.data('deferred__overlay'), undefined, 'replaced after first elapsed');
        deepEqual(result, []);
        start();
    }, 300);

    setTimeout(function() {
        equal(element.data('deferred__overlay'), undefined, 'replaced done');
        deepEqual(result, ['done restarted']);
        start();
    }, 700);
});

test('creme.object.build_callback (invalid script)', function() {
    raises(function() {creme.object.build_callback('...');});
    raises(function() {creme.object.build_callback('{', ['arg1', 'arg2']);});
});

test('creme.object.build_callback (function)', function() {
    var cb = function() {return 12};
    equal(cb, creme.object.build_callback(cb))
    equal(cb, creme.object.build_callback(cb, ['arg1', 'arg2']));
});

test('creme.object.build_callback (valid script, no parameter)', function() {
    var cb = creme.object.build_callback('12');
    equal(typeof cb, 'function');
    equal(cb(), 12);

    cb = creme.object.build_callback('return 15');
    equal(typeof cb, 'function');
    equal(cb(), 15);
});

test('creme.object.build_callback (valid script, parameters)', function() {
    var cb = creme.object.build_callback('arg1 * arg2', ['arg1', 'arg2']);
    equal(typeof cb, 'function');
    equal(cb(0, 0), 0);
    equal(cb(5, 2), 5*2);
    equal(cb(4.56, 2), 4.56*2);

    var cb = creme.object.build_callback('if (arg1 > arg2) {return arg1;} else {return arg2;}', ['arg1', 'arg2']);
    equal(typeof cb, 'function');
    equal(cb(0, 0), 0);
    equal(cb(5, 2), 5);
    equal(cb(4.56, 445), 445);
});

test('creme.string.Template (constructor)', function() {
    var template = new creme.string.Template();
    equal('', template.pattern);
    deepEqual({}, template.parameters);
    equal('object', typeof template.renderer);

    template = new creme.string.Template('this is a ${object}', {object:'backpipe'});
    equal('this is a ${object}', template.pattern);
    deepEqual({object:'backpipe'}, template.parameters);
    equal('object', typeof template.renderer);
});

test('creme.string.Template (tags)', function() {
    var template = new creme.string.Template();
    deepEqual([], template.tags());

    template.pattern = '${tag} ${tag2} ${last_tag}';
    deepEqual(['tag', 'tag2', 'last_tag'], template.tags());

    template.pattern = '${tag} ${tag2} ${{{last_tag}';
    deepEqual(['tag', 'tag2'], template.tags());

    template.pattern = '${tag} ${tag2} ${{last_tag}}';
    deepEqual(['tag', 'tag2'], template.tags());

    template.pattern = '${tag} ${tag2} $last_tag}';
    deepEqual(['tag', 'tag2'], template.tags());

    template.pattern = '${tag} ${tag2} ${last_tag toto';
    deepEqual(['tag', 'tag2'], template.tags());

    template.pattern = '${tag} ${tag2} ${last tag}';
    deepEqual(['tag', 'tag2'], template.tags());

    template.pattern = '${tag} ${tag2} {last_tag}';
    deepEqual(['tag', 'tag2'], template.tags());
});

test('creme.string.Template (render, empty data)', function() {
    var template = new creme.string.Template('this is a template');
    equal('this is a template', template.render());

    template.pattern = '${tag} ${tag2} ${last_tag}';
    equal('${tag} ${tag2} ${last_tag}', template.render());
});

test('creme.string.Template (render, empty pattern)', function() {
    var template = new creme.string.Template('', {tag:12});
    equal('', template.render());

    template.pattern = undefined;
    equal('', template.render());

    template.pattern = null;
    equal('', template.render());
});

test('creme.string.Template (render, dict)', function() {
    var data = {tag:12,
                tag2:'string',
                last_tag:{toString:function() {return 'yo';}}};

    var template = new creme.string.Template('this is a template', data);
    equal('this is a template', template.render());

    template.pattern = '${tag} ${tag2} ${last_tag}';
    equal('12 string yo', template.render());

    data.tag2 = undefined;
    equal('12 ${tag2} yo', template.render());

    data.tag3 = 'string3';
    equal('12 ${tag2} yo', template.render());
});

test('creme.string.Template (render, array)', function() {
    data = [12, 13, 14];

    var template = new creme.string.Template('this is a template', data);
    equal('this is a template', template.render());

    template.pattern = '${0} ${1} ${2}';
    equal('12 13 14', template.render());

    template.pattern = '${0} ${1} ${3}';
    equal('12 13 ${3}', template.render());
});

test('creme.string.Template (render, function)', function() {
    var data = function(key) {return key + "_rendered";};

    var template = new creme.string.Template('this is a template', data);
    equal('this is a template', template.render());

    template.pattern = '${tag} ${tag2} ${last_tag}';
    equal('tag_rendered tag2_rendered last_tag_rendered', template.render());

    template.pattern = '${tag} ${tag2} ${last_tag} ${last_tag2}';
    equal('tag_rendered tag2_rendered last_tag_rendered last_tag2_rendered', template.render());
});

test('creme.string.Template (render, object getters)', function() {
    var data = {
        firstname: function() {return 'John';},
        lastname: function() {return 'Doe';},
        fullname: function() {return 'JohnDoe';},
        address: '13 rue des plantes en pot'
    };

    var template = new creme.string.Template('this is a template', data);
    equal('this is a template', template.render());

    template.pattern = 'Mr ${firstname} ${lastname} (${fullname}), living at ${address}';
    equal('Mr John Doe (JohnDoe), living at 13 rue des plantes en pot', template.render());
});

test('creme.object.JSON.encode (null)', function() {
    var codec = new creme.object.JSON();

    equal("null", codec.encode(null));
});

test('creme.object.JSON.encode', function() {
    var codec = new creme.object.JSON();

    equal(codec.encode('test'), '"test"');
    equal(codec.encode(12), '12');
    equal(codec.encode(['a', 12, 'c', null, undefined]), '["a",12,"c",null,null]');
    equal(codec.encode({'a': ['a', 'b', 150],
                        'b': 'test',
                        'c': 12
                       }), '{"a":["a","b",150],"b":"test","c":12}');
});

test('creme.object.JSON.decode (null)', function() {
    var codec = new creme.object.JSON();

    raises(function() {codec.decode(null);});
});

test('creme.object.JSON.decode (invalid)', function() {
    var codec = new creme.object.JSON();

    raises(function() {codec.decode('{"a\':1}');});
    raises(function() {codec.decode('{"a":1,}');});
    raises(function() {codec.decode('{a:1}');});
});


test('creme.object.JSON.decode (invalid or null, default)', function() {
    var codec = new creme.object.JSON();

    equal(codec.decode('{"a\':1}', 'fail'), 'fail');
    equal(codec.decode('{"a":1,}', 'fail'), 'fail');
    equal(codec.decode('{a:1}', 'fail'), 'fail');
    equal(codec.decode(null, 'fail'), 'fail');
});


test('creme.object.JSON.decode (valid)', function() {
    var codec = new creme.object.JSON();

    deepEqual(codec.decode('{"a":1, "b":true, "c":[1, 2, 3]}'), {a: 1, b: true, c: [1, 2, 3]});
});
