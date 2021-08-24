define(
[
    'jquery',
    'underscore',
    'backbone',
    'module',
    'views/Base',
    'views/shared/controls/TextareaControl',
    '../Pane.pcss'
],
function(
    $,
    _,
    Backbone,
    module,
    BaseView,
    TextareaControl,
    css
){
    /**
     * @constructor
     * @memberOf views
     * @name MetricsField
     * @extends {views.BaseView}
     * @description Generic view for creating metric fields
     *
     * @param {Object} options
     * @param {String} options.name The name of the view
     * @param {String} options.targetAttributeName The name of the attribute field to listen to
     * @param {String} options.heading The heading of the view
     * @param {String} options.description The description of the view
     * @param {String} options.footer The description of the textarea
     * @param {String} options.placeholderText Textarea optional placeholder text
     */
    return BaseView.extend( /** @lends views.MetricsField.prototype */ {
        moduleId: module.id,
        initialize: function(options) {
            BaseView.prototype.initialize.call(this, options);
            this.state = new Backbone.Model();
            this.children.textarea = new TextareaControl({
                    spellcheck: false,
                    modelAttribute: this.options.name,
                    model: this.state,
                    placeholder: this.options.placeholderText || ""
                }
            );
            this.startListening();
            this.setValue();
        },
        startListening: function() {
            this.listenTo(this.model, 'change:' + this.options.targetAttributeName, this.setValue);
        },
        setValue: function() {
            this.value = this.model.get(this.options.targetAttributeName);
            this.state.set('text', this.value);
            $('textarea[name=' + this.options.name + ']').val(this.value);
        },
        events: {
            'keyup textarea': function(e) {
                var $target = $(e.currentTarget);
                var value = $target.val();
                this.model.set(this.options.targetAttributeName, value);
                e.preventDefault();
            }
        },
        render: function() {
            if(!this.el.innerHTML) {
                var template = _.template(this.template, {
                    _: _,
                    name: this.options.name,
                    heading: this.options.heading,
                    description: this.options.description,
                    footer: this.options.footer
                });
                this.$el.html(template);
                this.$('.text-control-placeholder').append(this.children.textarea.render().el);
            }
            return this;
        },
        template: '\
                <span id="<%- name %>-heading" class="metrics-field-label heading" for="<%- heading %>">\
                    <%- heading %>\
                </span>\
                <span id="<%- name %>-description" class="metrics-field-label description" for="<%- description %>">\
                    <%- description %>\
                </span>\
                <div class="text-control-placeholder"></div>\
                <span class="metrics-field-label footer" for="<%- footer %>">\
                    <%- footer %>\
                </label>\
                \
        '
    });
});
