define(
    [
        'jquery',
        'underscore',
        'splunk.util',
        'backbone',
        'views/Base',
        'uri/route',
        'module',
        'views/shared/controls/ControlGroup',
        './PasswordFeedback.pcss'
    ],
    function($, _, splunkutil, Backbone, Base, route, module, ControlGroup, css) {
        return Base.extend({
            moduleId: module.id,
            className: 'alerts',
            reqToSelector: [
                {'req': 'passLengthReq', 'selector': '.min-password-length'},
                {'req': 'passDigitReq', 'selector': '.min-password-digit'},
                {'req': 'passLowercaseReq', 'selector': '.min-password-lowercase'},
                {'req': 'passUppercaseReq', 'selector': '.min-password-uppercase'},
                {'req': 'passSpecialReq', 'selector': '.min-password-special'}
            ],
            initialize: function(options){
                Base.prototype.initialize.call(this, options);

                this.firstTimeLogin = _.isUndefined(this.options.firstTimeLogin) ? false : true;
                this.children.title = new ControlGroup({
                    controlType: 'Label',
                    label: _('Password must contain at least').t(),
                    tooltip: _('All characters must be printable ASCII.').t(),
                    controlOptions: {
                        defaultValue: ''
                    }
                });
            },
            greenCheck: function(value) {
                $(value).removeClass('icon-x').addClass('icon-check')
                .removeClass('password-req-gray').removeClass('password-req-black').removeClass('password-req-red').addClass('password-req-green');
            },
            blackCircle: function(value) {
                $(value).removeClass('icon-check').removeClass('icon-x')
                .removeClass('password-req-gray').removeClass('password-req-green').removeClass('password-req-red').addClass('password-req-black');
            },
            grayCircle: function(value) {
                $(value).removeClass('icon-check').removeClass('icon-x')
                .removeClass('password-req-green').removeClass('password-req-black').removeClass('password-req-red').addClass('password-req-gray');
            },
            redCross: function(value) {
                $(value).addClass('icon-x')
                .removeClass('password-req-gray').removeClass('password-req-black').removeClass('password-req-green').addClass('password-req-red');
            },
            onInputChange: function(valResults) {
                var parent = this;
                if (this.firstTimeLogin) {
                    _.map(this.reqToSelector, this.warn = function(pair) {
                        valResults[pair['req']] ? parent.greenCheck(pair['selector']) : parent.grayCircle(pair['selector']);
                    });
                } else {
                    _.map(this.reqToSelector, this.warn = function(pair) {
                        valResults[pair['req']] ? parent.greenCheck(pair['selector']) : parent.blackCircle(pair['selector']);
                    });
                }
            },
            onPasswordMismatch: function() {
                $(".mismatch-msg").show();
            },
            onPasswordMatch: function() {
                $(".mismatch-msg").hide();
            },
            onRemoveFocus: function(valResults) {
                var parent = this;
                _.map(this.reqToSelector, this.error = function(pair) {
                    valResults[pair['req']] ? parent.greenCheck(pair['selector']) : parent.redCross(pair['selector']);
                });
            },
			resetIcons: function() {
				var parent = this;
                if (this.firstTimeLogin) {
                    _.map(this.reqToSelector, this.error = function(pair) {
                        parent.grayCircle(pair['selector']);
                    });
                } else {
                    _.map(this.reqToSelector, this.error = function(pair) {
                        parent.blackCircle(pair['selector']);
                    });
                }
			},

            render: function() {
                this.$el.empty();

                var minPasswordLength, minPasswordDigit, minPasswordLowercase, minPasswordUppercase, minPasswordSpecial;

                if (this.firstTimeLogin) {
                    minPasswordLength = this.options.minPasswordLength;
                    minPasswordDigit = this.options.minPasswordDigit;
                    minPasswordLowercase = this.options.minPasswordLowercase;
                    minPasswordUppercase = this.options.minPasswordUppercase;
                    minPasswordSpecial = this.options.minPasswordSpecial;
                } else {
                    minPasswordLength = this.model.splunkAuth.entry.content.attributes.minPasswordLength;
                    minPasswordDigit = this.model.splunkAuth.entry.content.attributes.minPasswordDigit;
                    minPasswordLowercase = this.model.splunkAuth.entry.content.attributes.minPasswordLowercase;
                    minPasswordUppercase = this.model.splunkAuth.entry.content.attributes.minPasswordUppercase;
                    minPasswordSpecial = this.model.splunkAuth.entry.content.attributes.minPasswordSpecial;
                }

                var lengthStr = (minPasswordLength === 1) ? _(' %s character').t() : _(' %s characters').t();
                var digitStr = (minPasswordDigit === 1) ? _(' %s numeral').t() : _(' %s numerals').t();
                var lowercaseStr = (minPasswordLowercase === 1) ? _(' %s lowercase').t() : _(' %s lowercases').t();
                var uppsercaseStr = (minPasswordUppercase === 1) ? _(' %s uppercase').t() : _(' %s uppercases').t();
                var specialStr = (minPasswordSpecial === 1) ? _(' %s special character').t() : _(' %s special characters').t();


                this.$el.append(this.compiledTemplate({
                    minPasswordLength: minPasswordLength,
                    minPasswordDigit: minPasswordDigit,
                    minPasswordLowercase: minPasswordLowercase,
                    minPasswordUppercase: minPasswordUppercase,
                    minPasswordSpecial: minPasswordSpecial,
                    minPasswordLengthStr: splunkutil.sprintf(lengthStr, minPasswordLength),
                    minPasswordDigitStr: splunkutil.sprintf(digitStr, minPasswordDigit),
                    minPasswordLowercaseStr: splunkutil.sprintf(lowercaseStr, minPasswordLowercase),
                    minPasswordUppercaseStr: splunkutil.sprintf(uppsercaseStr, minPasswordUppercase),
                    minPasswordSpecialStr: splunkutil.sprintf(specialStr, minPasswordSpecial)
                }));

                this.children.title.render().appendTo(this.$(".password-req-title"));

                return this;
            },
            template: '\
                <div class="password-req-title"></div>\
                <ul class="password-req-section">\
                <% if (minPasswordLength > 0) { %> \
                    <li class="min-password-length"><%- minPasswordLengthStr %></li>\
                <% } %>\
                <% if (minPasswordDigit > 0) { %> \
                    <li class="min-password-digit"><%- minPasswordDigitStr %></li>\
                <% } %>\
                <% if (minPasswordLowercase > 0) { %> \
                    <li class="min-password-lowercase"><%- minPasswordLowercaseStr %></li>\
                <% } %>\
                <% if (minPasswordUppercase > 0) { %> \
                    <li class="min-password-uppercase"><%- minPasswordUppercaseStr %></li>\
                <% } %>\
                <% if (minPasswordSpecial > 0) { %> \
                    <li class="min-password-special"><%- minPasswordSpecialStr %></li>\
                <% } %>\
                </ul>\
                <div class="mismatch-msg password-req-red"><%- _("Passwords don\'t match").t() %></div>\
            '
        });
    }
);
