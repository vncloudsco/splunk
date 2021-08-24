define([
    'jquery',
    'underscore',
    'backbone',
    'document-register-element' 
], function($, _, Backbone) {

    var ATTRIBUTES = {
        required: 'required',
        pattern: 'pattern'

    };
    var InputBase = Object.create(HTMLDivElement.prototype);

    _.extend(InputBase, {

        supportedAttributes: [],

        createdCallback: function() {
            // Leading or trailing whitespace can confuse the wrapped Backbone views
            // that sub-classes will create, so remove it here.
            var $el = $(this);
            $el.html($.trim($el.html()));
            this.model = new Backbone.Model({ value: $(this).attr('value')});
            this._readAttributes();
        },

        attachedCallback: function() {
            var $el = $(this);
            this.model.on('change', function() {
                $el.attr('value', this.model.get('value'));
                $el.trigger('change');
            }, this);
        },

        detachedCallback: function() {
            this.model.off();
        },

        attributeChangedCallback: function(name, previousValue, value) {
            if (name === 'value') {
                this.model.set({ value: value });
            }
        },

        getSupportedAttributes: function() {
            return this.supportedAttributes;
        },

        _readAttributes: function() {
            var $el = $(this);
            var attributes = {};
            _.each(this.attributes, function(attr) {
                if (_.contains(this.getSupportedAttributes(), attr.name)) {
                    if (attr.name === 'required') {
                        this.model.set(attr.name, true);
                    } else {
                        this.model.set(attr.name, attr.value);
                    }
                }
            }, this);
            return attributes;
        }

    },{
        ATTRIBUTES: ATTRIBUTES
    });

    return InputBase;
    
});