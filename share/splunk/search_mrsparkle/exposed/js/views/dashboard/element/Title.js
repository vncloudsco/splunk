define([
    'module',
    'jquery',
    'underscore',
    'views/dashboard/Base',
    'splunkjs/mvc',
    'splunkjs/mvc/utils',
    'splunkjs/mvc/tokenutils'
], function(module,
            $,
            _,
            BaseDashboardView,
            mvc,
            utils,
            TokenUtils) {

    var DashboardElementTitleView = BaseDashboardView.extend({
        moduleId: module.id,
        viewOptions: {
            register: false
        },
        tagName: 'h3',
        constructor: function(options) {
            BaseDashboardView.prototype.constructor.call(this, options, {retainUnmatchedTokens: true});
            this.settings._sync = utils.syncModels(this.settings, this.model, {
                auto: 'pull',
                prefix: 'dashboard.element.',
                include: ['title']
            });
            this.listenTo(this.settings, 'change:title', this.render);
        },
        render: function() {
            var title = this.settings.get('title', {"tokens": true});
            if (title) {
                title = TokenUtils.replaceTokens(
                    _(title).t(), mvc.Components, {
                        tokenNamespace: this.settings._tokenNamespace,
                        escaper: this.settings._tokenEscaper,
                        allowNoEscape: this.settings._allowNoEscape
                    });
            }
            if (title) {
                this.$el.text(_(title).t()).show();
            } else {
                this.$el.text('').hide();
            }
            return this;
        },
        remove: function() {
            if (this.settings) {
                if (this.settings._sync) {
                    this.settings._sync.destroy();
                }
            }
            BaseDashboardView.prototype.remove.apply(this, arguments);
        }
    });

    return DashboardElementTitleView;

});
