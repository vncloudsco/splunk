define(
    [
        'underscore',
        'module',
        'views/Base'
    ],
    function(_, module, Base) {
        
        return Base.extend({
            moduleId: module.id,
            /**
             * Module to display the formatted last modified/updated time.
             * @param {Object} options {
             *     model: {
             *         document: extends <models.SplunkDBase>
             *     }
             * }
             */
            tagName: 'span',
            initialize: function() {
                Base.prototype.initialize.apply(this, arguments);
                this.activate();
            },
            activate: function(options) {
                if (this.active) {
                    return Base.prototype.activate.call(this, options);
                }
                Base.prototype.activate.call(this, options);
                if (this.el.innerHTML) {
                    this.render();
                }
                return this;
            },
            startListening: function() {
                this.listenTo(this.model.document.entry, 'change:updated', _.debounce(this.render));
            },
            render: function() {
                this.$el.html(this.model.document.getFormattedUpdatedTime());
            }
        });
    }
);