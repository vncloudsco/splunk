define([
    'jquery',
    'underscore',
    'backbone',
    'module',
    'views/Base',
    'views/shared/controls/KeyValueControl'
],
    function (
        $,
        _,
        Backbone,
        module,
        BaseView,
        KeyValueControl
        ) {

        return BaseView.extend({
            /**
            * @param {Object} options {
            *       model: <Backbone.Model>
            *       numRow: {Integer} row number of this field row.
            *       options.defaultKey Initialize the keyTextControl with this value
            *       options.defaultValue Initialize the valueTextControl with this value
            * }
            */
            moduleId: module.id,
            className: "clearfix",

            events: {
            'click .close-row': "onCloseRow",
            'keypress .close-row': function(e) {
                    if (e.keyCode === 13) //ENTER
                        this.onCloseRow(e);
                }
            },

            initialize: function(options) {
                BaseView.prototype.initialize.call(this, options);
                this.children.keyValueControl = new KeyValueControl({
                    model: this.model,
                    defaultKey: this.options.defaultKey,
                    defaultValue: this.options.defaultValue,
                    keyTextControlOptions: {
                        modelAttribute: 'summaryIndex.newField.key' + this.options.numRow
                    },
                    valueTextControlOptions: {
                        modelAttribute: 'summaryIndex.newField.value' + this.options.numRow
                    },
                    showSeparator: true
                });
            },

            onCloseRow: function(e) {
                var key = this.children.keyValueControl.getKey();
                this.children.keyValueControl.unsetKey();
                this.trigger("closeRow", this, key);
            },

            render: function() {
                // Detach children
                if (this.children.keyValueControl) {
                    this.children.keyValueControl.detach();
                }

                // Use template
                this.$el.html(this.compiledTemplate({}));

                // Attach children and render them
                this.children.keyValueControl.render().appendTo(this.$(".key-value-control-placeholder"));

                return this;
            },

            template: '\
                <span class="key-value-control-placeholder" ></span>\
                <span tabindex="0" class="close-row"><i class="icon-x-circle"></i></span>\
            '
        });

    });

