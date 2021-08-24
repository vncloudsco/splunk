define([
        'jquery',
        'underscore',
		'splunk.util',
        'backbone',
        'module',
		'views/shared/FlashMessages',
		'views/shared/PasswordFeedback',
        'views/Base',
        'uri/route',
        'views/shared/controls/ControlGroup',
		'views/shared/BaseUserSettings',
		'./ChangePassword.pcss',
        'util/splunkd_utils'
    ],
    function(
        $,
        _,
		splunkutil,
        Backbone,
        module,
        FlashMessages,
        PasswordFeedbackView,
        Base,
        route,
		ControlGroup,
		BaseUserSettingsView,
		css, 
		splunkDUtils
    ) {
        return Base.extend({
            moduleId: module.id,

			events: {
                'click .btn.save-button': function(e) {
                    e.preventDefault();

					this.children.flashMessagesView.flashMsgHelper.removeGeneralMessage("saved");
					if (_.isEmpty(this.model.entity.entry.content.get('password'))) {
                        this.model.entity.entry.content.unset('password');
                    } 

                    var saveOptions = {};
					saveOptions.headers = {'X-Splunk-Form-Key': splunkutil.getFormKey()};

                    var entryValidation = this.model.entity.entry.validate();
                    var entryContentValidation = this.model.entity.entry.content.validate();

                    if (_.isUndefined(entryValidation) && _.isUndefined(entryContentValidation)) {
                        var saveDfd = this.model.entity.save({}, saveOptions);
                        if (saveDfd) {
                            saveDfd.done(function() {
                                this.children.baseUserSettings.resetFields();
								var savedMessage = {};
								savedMessage = {
									type: 'success',
									html: _('User settings saved.').t()
								};
								this.children.flashMessagesView.flashMsgHelper.addGeneralMessage("saved", savedMessage);
                            }.bind(this));
                        }
                    } else {
                        this.model.entity.trigger("serverValidated", true, this.model.entity, []);
                    }
                }
            },
			
            initialize: function(options) {
                Base.prototype.initialize.call(this, options);
				
                this.renderDfd = new $.Deferred();
				
				this.children.baseUserSettings = new BaseUserSettingsView({
					model: this.model,
					children: this.children,
					collection: this.collection
				});
				
				this.children.flashMessagesView = new FlashMessages({
                    model: {
                        userEntityContentModel: this.model.entity.entry.content,
                        userEntityModel: this.model.entity.entry,
                        userModel: this.model.entity
                    }
                });
            },

			render: function() {
				this.$el.html(this.compiledTemplate({
                    _: _
                }));
				this.children.flashMessagesView.render().prependTo(this.$('.form-wrapper'));          
				this.children.baseUserSettings.render().replaceAll(this.$(".baseUserSettings-placeholder"));
				this.model.entity.entry.content.unset('password');
				
				return this;
			},
			
			template: '\
				<div class="section-padded section-header"> \
                    <h1 class="section-title"><%- _("Account Settings").t() %></h1> \
                </div>\
				<div class="edit-form-wrapper"> \
                    <div class="form-wrapper form-horizontal"> \
						<h2><%- _("Personal").t() %></h2>\
						<div class="baseUserSettings-placeholder"></div>\
					</div> \
                    <div class="jm-form-actions"> \
                    	<a href="#" class="btn btn-primary save-button"><%- _("Save").t() %></a> \
                    </div> \
                </div> \
			'	
        });
    });
	
