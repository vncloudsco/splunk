define(
    [
        'module',
        'contrib/text!views/account/mfa_rsa/Master.html',
        'underscore',
        'splunk.util',
        'uri/route',
        'views/Base',
        'views/shared/controls/TextControl',
        'views/shared/FlashMessages',
        './mfa_rsa.pcss'
    ],
    function(module, template, _, splunkutil, route, BaseView, TextControlView, FlashMessagesView, css) {
        return BaseView.extend({
            moduleId: module.id,
            template: template,
            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);
                this.children.passcode = new TextControlView({
                    model: this.model.rsa,
                    modelAttribute: 'passcode',
                    elementId: 'passcode',
                    placeholder: _('RSA passcode').t(),
                    password: true
                });
                this.children.tokencode = new TextControlView({
                    model: this.model.rsa,
                    modelAttribute: 'tokencode',
                    elementId: 'tokencode',
                    placeholder: _('RSA next tokencode').t(),
                    password: true
                });
                this.children.flashMessages = new FlashMessagesView({
                    model: this.model.rsa,
                    template: '\
                        <% flashMessages.each(function(flashMessage){ %>\
                            <% if (flashMessage.get(\'type\') !== \'mfa_unknown_error\') {%>\
                                <p class="error"><%= flashMessage.get("html") %></p>\
                            <% } %>\
                        <% }); %>\
                    '
                });
                this.listenTo(this.model.login, 'change:tokenmode', this.visibility);
            },
            events: {
                'submit form': function(e) {
                    e.preventDefault();
                    if (this.model.login.get('tokenmode') === true) {
                        this.model.rsa.save({
                            tokencode: this.model.rsa.get('tokencode'),
                            authnAttemptId: this.model.rsa.get('authnAttemptId'),
                            inResponseTo: this.model.rsa.get('inResponseTo')
                        });
                    } else {
                        this.model.rsa.save({
                            passcode: this.model.rsa.get('passcode')
                        });
                    }
                }
            },
            visibility: function() {
                if (this.model.login.get('tokenmode') === true) {
                    this.children.tokencode.$el.show();
                    this.children.passcode.$el.hide();
                } else {
                    this.children.tokencode.$el.hide();
                    this.children.passcode.$el.show();
                }
            },
            render: function() {
                var html = this.compiledTemplate({
                    _: _,
                    model: {
                        login: this.model.login,
                        rsa: this.model.rsa
                    },
                    route: route
                });
                this.$el.html(html);
                this.visibility();
                this.children.passcode.render().insertBefore(this.$('input[type=submit]'));
                this.children.tokencode.render().insertBefore(this.$('input[type=submit]'));
                this.children.flashMessages.render().appendTo(this.$el);
                return this;
            }
        });
    }
);
