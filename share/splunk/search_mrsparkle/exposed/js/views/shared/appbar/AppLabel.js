define([
    'jquery',
    'underscore',
    'module',
    'views/Base',
    'contrib/text!views/shared/appbar/AppLabel.html',
    './AppLabel.pcssm'
],
function(
    $,
    _,
    module,
    BaseView,
    templateAppLabel,
    css
){
    return BaseView.extend({
        moduleId: module.id,
        css: css,
        initialize: function() {
            BaseView.prototype.initialize.apply(this, arguments);
            this.model.appNav.on('change', this.render, this);
        },
        showLogo: function(){
            this.$el.find('[data-role=app-logo]').show();
            this.$el.find('[data-role=app-name]').hide();
        },
        showName: function(){
            this.$el.find('[data-role=app-name]').show();
            this.$el.find('[data-role=app-logo]').hide();
            if (this.model.appNav.get('icon')) {
                var img = new Image();
                img.onload = function(){
                    this.$el.find('[data-role=app-icon]').empty().append(img);
                    if (this.options.getAppColor) {
                        this.$el.find('[data-role=app-icon] img').css('background-color', this.options.getAppColor());
                    }
                }.bind(this);
                img.src = this.model.appNav.get('icon');
                img.alt = '';
            }
        },
        render: function(){
            var label = this.model.appNav.get('label') || '';

            var html = _.template(templateAppLabel, {
                appLink: this.model.appNav.get('link'),
                appLabel: label,
                appLogo: this.model.appNav.get('logo'),
                css: css
            });
            this.$el.html(html);

            this.setAppLabelDisplay();

            return this;
        },
        setAppLabelDisplay: function(){
            if (this.model.appNav.get('logo')) {
                var img = new Image();
                img.onload = function(){
                    if(parseInt(img.width, 10) < 2){
                        this.showName();
                    }else{
                        this.$el.find('[data-role=app-logo]').empty().append(img);
                        $(img).attr('class', css.image).attr('data-role=app-logo');
                        this.$('[data-role=app-home-link]').prepend(img);
                        this.showLogo();
                    }
                }.bind(this);

                img.onerror = function(){
                    this.showName();
                }.bind(this);

                img.src = this.model.appNav.get('logo');
                img.alt = '';
            }
        }
    });
});
