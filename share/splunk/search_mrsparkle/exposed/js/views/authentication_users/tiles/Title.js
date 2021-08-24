define(function(require, exports, module) {

    var $ = require("jquery");
    var _ = require("underscore");
    var i18n = require("splunk.i18n");
    var SplunkUtil = require("splunk.util");
    var BaseView = require("views/Base");
    var route = require("uri/route");

    var template = require("contrib/text!views/authentication_users/tiles/Title.html");

    return BaseView.extend({

        moduleId: module.id,
        template: template,
        className: 'section-header page-heading clearfix',

        initialize: function() {
            BaseView.prototype.initialize.apply(this, arguments);
        },

        render: function() {
            // count number of users that are using "Splunk" authentication
            var numUsers = 0;
            this.collection.users.each(function(user) {
                if (user.entry.content.get("type") === "Splunk") {
                    numUsers++;
                }
            }, this);

            var passwordManagementUrl = route.manager(
                            this.model.application.get("root"),
                            this.model.application.get("locale"),
                            this.model.application.get("app"),
                            ['password', 'management']);

            this.$el.html(this.compiledTemplate({
                _: _,
                sprintf: SplunkUtil.sprintf,
                ungettext: i18n.ungettext,
                canEditUsers: this.model.user.canEditUsers(),
                isSplunkAuth: (this.model.user.entry.content.get("type") === "Splunk"),
                maxUsers: this.model.serverInfo.entry.content.get("max_users"),
                numUsers: numUsers,
                passwordManagementUrl: passwordManagementUrl
            }));
            return this;
        }

    });

});
