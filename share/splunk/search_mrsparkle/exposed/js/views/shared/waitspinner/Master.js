define(['underscore', 'module', 'views/Base', './Master.pcssm'], function(_, module, BaseView, css) {


    return BaseView.extend({
        moduleId: module.id,
        useLocalClassNames: false,
        constructor: function(options) {
            _.extend(this, _.pick(options || {}, 'useLocalClassNames'));

            if (this.useLocalClassNames && this.css === undefined) {
                this.css = css;
            }

            BaseView.apply(this, arguments);
        },
        initialize: function(){
            BaseView.prototype.initialize.apply(this, arguments);

            var defaults = {
              size: 'small',
              color: 'gray', // Deprecated
              frameWidth: 14, //px
              frameCount: 20,
              fps: 20
            };

            _.defaults(this.options, defaults);

            if (this.useLocalClassNames) {
                this.$el.attr('class', this.css['spinner' + this.options.size]);
            } else {
                this.$el.addClass('spinner-' + this.options.size);
            }
            this.frame=0;
        },
        stop:  function() {
            this.active=false;
            this.interval && window.clearInterval(this.interval);
            return this;
        },
        start:  function() {
            this.active=true;
            this.interval && window.clearInterval(this.interval);
            this.interval=setInterval(this.step.bind(this), 1000/this.options.fps);
            return this;
        },
        step:  function() {
            this.$el.css('backgroundPosition', '-' + (this.frame * this.options.frameWidth) + 'px top ');

            this.frame++;
            this.frame = this.frame == this.options.frameCount ? 0 : this.frame;

            return this;
        },
        remove: function() {
            this.stop();
            BaseView.prototype.remove.apply(this, arguments);
        },
        render: function() {
            return this;
        }
    });
});
