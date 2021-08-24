define([
    'jquery',
    'underscore',
    'module',
    'models/services/server/Health',
    'views/Base',
    'views/shared/Icon',
    'views/shared/splunkbar/healthmodal/Master',
    'views/shared/splunkbar/health/health_utils',
    './Master.pcssm',
    'util/keyboard'
],
function(
    $,
    _,
    module,
    HealthModel,
    BaseView,
    IconView,
    HealthModal,
    HealthUtils,
    css,
    keyboard
) {
    return BaseView.extend({
        moduleId: module.id,
        css: css,
        initialize: function() {
            BaseView.prototype.initialize.apply(this, arguments);

            this.HEALTH_POLLING_DELAY = 10000;
            this.deferreds = {};
            this.deferreds.health = $.Deferred();

            this.model.health = new HealthModel();
            this.restartHealthPolling();
            this.model.health.on('serverValidated', function() {
                this.deferreds.health.resolve();
                this.debouncedRender();
            }.bind(this));
        },

        restartHealthPolling: function() {
            this.model.health.stopPolling();
            this.model.health.startPolling({
                delay: this.HEALTH_POLLING_DELAY,
                uiInactivity: true,
                stopOnError: false,
                data: {}
            });
        },

        events: {
            'click a': function(e) {
                e.preventDefault();
                this.showHealthModal();
            },
            'keyup': function(e) {
                e.preventDefault();
                if (e.which === keyboard.KEYS.ENTER ) {
                    this.showHealthModal();
                }
            }
        },

        showHealthModal: function() {
            this.children.infoDialog = new HealthModal({
                model: {
                    application: this.model.application,
                    serverInfo: this.model.serverInfo
                },
                onHiddenRemove: true
            });
            this.children.infoDialog.render().appendTo($("body"));
            this.children.infoDialog.show();
        },

        render: function() {
            var health = this.model.health.getHealth();
            var isDisabled = this.model.health.isDisabled();

            var html = this.compiledTemplate({
                cssBadge: css.healthBadge,
                iconAltText: HealthUtils.getIconAltText(health, isDisabled)
            });
            this.$el.html(html);

            var iconName = HealthUtils.getIconName(health, isDisabled);
            var iconStyle = HealthUtils.getIconStyle(health, isDisabled);
            if (this.children.infoIcon) {
                this.children.infoIcon.$el.detach();
            }
            this.children.infoIcon = new IconView({icon: iconName, size: 1.5});
            this.children.infoIcon.render().appendTo(this.$('[data-role=health-icon]'));
            this.$('[data-role=health-icon]').attr('class', iconStyle);
        },
        template: '\
        <a class="<%- cssBadge %>" data-test="health-badge" tabindex="0" title="<%- iconAltText %>">\
            <span data-role="health-icon" />\
        </a>\
        '
    });
});