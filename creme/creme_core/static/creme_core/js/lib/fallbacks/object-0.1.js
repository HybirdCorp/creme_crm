
(function() {
    function appendStatic(name, method)
    {
        if(!Object[name])
            Object[name] = method;
    };
    
    function append(name, method)
    {
        if(!Object.prototype[name])
            Object.prototype[name] = method;
    };

    appendStatic('keys', function(obj) {
        var keys = [];
        var key;

        for (key in obj) {
            if (obj.hasOwnProperty(key)) {
                keys.push(key);
            }
        }

        return keys;
    });

    appendStatic('isNone', function(obj) {
        return obj === undefined || obj === null;
    });

    appendStatic('isEmpty', function(obj) {
        if (Object.isNone(obj) || obj.length === 0)
            return true

        if (typeof obj === 'number')
            return false;

        for(var name in obj) {
            return false;
        }

        return true;
    });

    appendStatic('isType', function(obj, type) {
        return (typeof obj === type);
    });

    appendStatic('isFunc', function(obj) {
        return (typeof obj === 'function');
    });

    var cloneArguments = function(args, start) {
        var res = [];

        for(var i = start || 0; i < args.length; ++i) {
            res.push(args[i]);
        }

        return res;
    };

    appendStatic('proxy', function(delegate, context, options) {
        if (Object.isNone(delegate))
            return;

        var options = options || {};

        var proxy = context || {};
        var context = context || delegate;
        var filter = Object.isFunc(options.filter) ? options.filter : function() {return true}
        var parameters = Object.isFunc(options.arguments) ? function(args) {return options.arguments(cloneArguments(args));} : cloneArguments;

        for(key in delegate)
        {
            var value = delegate[key];

            if (!Object.isFunc(value) || filter(key, value) === false)
                continue;

            // use a function to 'keep' the current loop step context
            (function(fn, key, context) {
                proxy[key] = function() {
                    return fn.apply(context, parameters(arguments));
                };
            })(value, key, context);
        }

        return proxy;
    });

    appendStatic('_super', function(type, delegate, method) {
        var proto = Object.getPrototypeOf(type.prototype);

        if (method === undefined)
            return Object.proxy(proto, delegate);

        return proto[method].apply(delegate, cloneArguments(arguments, 3));
    });

    appendStatic('getPrototypeOf', function(object) {
        if (typeof "".__proto__ === 'object')
            return object.__proto__;

        if (Object.isNone(object) || object === Object.prototype)
            return null;

        return Object.isNone(object.constructor) ? null : object.constructor.prototype;
    });
})();