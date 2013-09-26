module("creme.utils.template.js", {
  setup: function() {},
  teardown: function() {}
});

test('creme.utils.Template (constructor)', function() {
    var template = new creme.utils.Template();
    equal('', template.pattern);
    deepEqual({}, template.parameters);
    equal('object', typeof template.renderer);

    template = new creme.utils.Template('this is a ${object}', {object:'backpipe'});
    equal('this is a ${object}', template.pattern);
    deepEqual({object:'backpipe'}, template.parameters);
    equal('object', typeof template.renderer);
});

test('creme.utils.Template (tags)', function() {
    var template = new creme.utils.Template();
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

    template.pattern = '${tag.id} ${tag.name}'
    deepEqual(['tag'], template.tags());
});

test('creme.utils.Template (render, empty data)', function() {
    var template = new creme.utils.Template('this is a template');
    equal('this is a template', template.render());

    template.pattern = '${tag} ${tag2} ${last_tag}';
    equal('${tag} ${tag2} ${last_tag}', template.render());
});

test('creme.utils.Template (render, empty pattern)', function() {
    var template = new creme.utils.Template('', {tag:12});
    equal('', template.render());

    template.pattern = undefined;
    equal('', template.render());

    template.pattern = null;
    equal('', template.render());
});

test('creme.utils.Template (render, dict)', function() {
    var data = {tag:12,
                tag2:'string',
                last_tag:{toString:function() {return 'yo';}}};

    var template = new creme.utils.Template('this is a template', data);
    equal('this is a template', template.render());

    template.pattern = '${tag} ${tag2} ${last_tag}';
    equal('12 string yo', template.render());

    data.tag2 = undefined;
    equal('12 ${tag2} yo', template.render());

    data.tag3 = 'string3';
    equal('12 ${tag2} yo', template.render());
});

test('creme.utils.Template (render, array)', function() {
    data = [12, 13, 14];

    var template = new creme.utils.Template('this is a template', data);
    equal('this is a template', template.render());

    template.pattern = '${0} ${1} ${2}';
    equal('12 13 14', template.render());

    template.pattern = '${0} ${1} ${3}';
    equal('12 13 ${3}', template.render());
});

test('creme.utils.Template (render, function)', function() {
    var data = function(key) {return key + "_rendered";};

    var template = new creme.utils.Template('this is a template', data);
    equal('this is a template', template.render());

    template.pattern = '${tag} ${tag2} ${last_tag}';
    equal('tag_rendered tag2_rendered last_tag_rendered', template.render());

    template.pattern = '${tag} ${tag2} ${last_tag} ${last_tag2}';
    equal('tag_rendered tag2_rendered last_tag_rendered last_tag2_rendered', template.render());
});

test('creme.utils.Template (render, object attribute)', function() {
    var data = {
         firstname: 'John',
         lastname: 'Doe',
         address: {
             number: 13,
             roadtype: 'rue',
             road: 'des plantes en pot',
             city: {
                 postalcode: 45007,
                 name: 'Melun Sud'
             }
         }
    };

    var template = new creme.utils.Template('this is a template', data);
    equal('this is a template', template.render());

    template.pattern = 'Mr ${firstname} ${lastname}, living at ${address.number}, ${address.roadtype} ${address.road}, ${address.city.postalcode} ${address.city.name}';
    equal('Mr John Doe, living at 13, rue des plantes en pot, 45007 Melun Sud', template.render());
});

test('creme.utils.Template (render, empty object attribute)', function() {
    var data = {
         firstname: 'John',
         lastname: 'Doe',
         address: {
             number: 13,
             roadtype: 'rue',
             road: 'des plantes en pot',
             city: null
         }
    };

    var template = new creme.utils.Template('this is a template', data);
    equal('this is a template', template.render());

    template.pattern = 'Mr ${firstname} ${lastname}, living at ${address.number}, ${address.roadtype} ${address.road}, ${address.city.postalcode} ${address.city.name}';
    equal('Mr John Doe, living at 13, rue des plantes en pot, ${address.city.postalcode} ${address.city.name}', template.render());
});

test('creme.utils.Template (render, object getters)', function() {
    var data = {
        firstname: function() {return 'John';},
        lastname: function() {return 'Doe';},
        fullname: function() {return 'JohnDoe';},
        address: function() {return {
            number: function() {return 38;},
            roadtype: 'rue',
            road: 'des plantes en pot',
            city: {
                postalcode: 45007,
                name: 'Melun Sud'
            }
        };}
    };

    var template = new creme.utils.Template('this is a template', data);
    equal('this is a template', template.render());

    template.pattern = 'Mr ${firstname} ${lastname} (${fullname}), living at ${address.number}, ${address.roadtype} ${address.road}, ${address.city.postalcode} ${address.city.name}';
    equal('Mr John Doe (JohnDoe), living at 38, rue des plantes en pot, 45007 Melun Sud', template.render());
});
