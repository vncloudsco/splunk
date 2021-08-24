define(
    [
        'jquery',
        'module',
        'views/shared/Button',
        './Button.pcssm'
    ],
    function(
        $,
        module,
        Button,
        css
    ){
        return Button.extend({
            moduleId: module.id,
            css: css,
            initialize: function(options) {
                this.className = options.isLite ? css.viewLite : css.viewEnterprise;
                Button.prototype.initialize.apply(this, arguments);
            },
            render: function() {
                Button.prototype.render.apply(this, arguments);

                var underlineColor = this.options.appColor === 'transparent' ? '#5CC05C' : this.options.appColor;
                var underline = $('<div/>', {
                    'class': this.options.isLite ? css.underlineLite : css.underline,
                    style: (this.options.active && !this.options.isLite) ? 'background-color: ' + underlineColor : undefined,
                    'data-role': 'underline'
                }).appendTo(this.$el);
            }
        });
    });
