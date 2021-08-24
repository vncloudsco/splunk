define(
    [
        'module',
        'underscore',
        'views/Base',
        'views/shared/FlashMessagesLegacy',
        'collections/shared/FlashMessages'
    ],
    function(
        module,
        _,
        BaseView,
        FlashMessagesLegacyView,
        FlashMessagesCollection
    ) {
        return BaseView.extend({
            moduleId: module.id,
            initialize: function() {
                BaseView.prototype.initialize.apply(this, arguments);
                if (!this.collection) {
                    this.collection = new FlashMessagesCollection();
                }
                this.children.flashMessagesLegacy = new FlashMessagesLegacyView({
                    collection: this.collection,
                    template: '\
                        <% flashMessages.each(function(flashMessage, index){ %>\
                            <p class="error">\
                                <% if (index === 0) { %>\
                                    <svg width="24px" height="24px" viewBox="465 398 24 24" version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">\
                                        <defs>\
                                            <circle id="path-1" cx="12" cy="12" r="12"></circle>\
                                            <mask id="mask-2" maskContentUnits="userSpaceOnUse" maskUnits="objectBoundingBox" x="0" y="0" width="24" height="24" fill="white">\
                                                <use xlink:href="#path-1"></use>\
                                            </mask>\
                                        </defs>\
                                        <g id="Group-2" stroke="none" stroke-width="1" fill="none" fill-rule="evenodd" transform="translate(465.000000, 398.000000)">\
                                            <use class="stroke-svg" id="Oval-5" mask="url(#mask-2)" stroke-width="4" xlink:href="#path-1"></use>\
                                            <path class="fill-svg" d="M10.2194542,7.75563395 C10.098253,6.78602409 10.7902713,6 11.7661018,6 L12.2338982,6 C13.2092893,6 13.902295,6.7816397 13.7805458,7.75563395 L13.2194542,12.244366 C13.098253,13.2139759 12.209547,14 11.2294254,14 L12.7705746,14 C11.7927132,14 10.902295,13.2183603 10.7805458,12.244366 L10.2194542,7.75563395 Z" id="Rectangle-64"></path>\
                                            <circle class="fill-svg" id="Oval-2" cx="12" cy="17" r="2"></circle>\
                                        </g>\
                                    </svg>\
                                <% } %>\
                                <%= flashMessage.get("html") %>\
                            </p>\
                        <% }); %>\
                    '
                });
                this.listenTo(this.model.tos, 'change:content', this.render);
            },
            events: {
                'click a.btn': function(e) {
					if (this.$('input[name="accept"]').is(':checked')) {
						this.model.login.set({ accept_tos: this.model.tos.get('tos_version')});
						//grabs new password if user was forced to change
						if (this.model.login.get('new_password')) {
							this.model.login.set({ password: this.model.login.get('new_password')});
						}
						this.model.login.save();
                        this.collection.reset([]);
                   } else {
                       this.collection.reset([
                            {
                                type: 'error',
                                html: _('Accept the Terms of Service to continue.').t()
                            }
                        ]);
                    }
                    e.preventDefault();
                },
                'change input#accept': function (e) {
                    if (e.target) {
                        this.$('a.accept-tos-button')[e.target.checked ? "addClass" : "removeClass"]('btn-primary');
                    }
                }
            },
            render: function() {
                var html = this.compiledTemplate({
                    _: _,
                    model: this.model.tos
                });
                this.el.innerHTML = html;
                this.children.flashMessagesLegacy.render().insertAfter(this.$('.content'));
                return this;
            },
            template: '\
                <h2 class="title"><%- _("Terms of Service").t() %></h2>\
                <div class="content"><%= model.get("content") %></div>\
                <input type="checkbox" id="accept" name="accept" value="1" /><label for="accept"><%- _("I accept these terms").t() %></label> <a href="#" class="accept-tos-button btn pull-right"><%- _("Ok").t() %></a>\
            '
        });
    }
);
