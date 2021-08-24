define(
    [
        'underscore',
        'module',
        'views/Base'
    ],
    function(
        _,
        module,
        Base
    ) {
        return Base.extend({
            moduleId: module.id,
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
                this.listenTo(this.model.entry.content, 'change:is_scheduled change:cron_schedule', _.debounce(this.render));
            },

            render: function() {
                this.$el.html(this.model.getScheduleString());
            }
        });
    }
);
