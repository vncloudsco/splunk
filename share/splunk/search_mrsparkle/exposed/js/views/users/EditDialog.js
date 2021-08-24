/**
 * @author cykao
 * @date 6/19/17
 *
 * Popup dialog for editing user config
 */

define([
    'jquery',
    'underscore',
    'splunk.util',
    'backbone',
    'module',
    'views/shared/FlashMessages',
    'views/shared/PasswordFeedback',
    'views/shared/Modal',
    'views/shared/controls/ControlGroup',
    'models/account/Login',
    'views/shared/controls/TextControl',
	'views/shared/BaseUserSettings',
    'views/shared/controls/TimeZone'
],

    function(
        $,
        _,
        splunkutil,
        Backbone,
        module,
        FlashMessages,
        PasswordFeedbackView,
        Modal,
        ControlGroup,
        Login,
        TextControlView,
		BaseUserSettingsView,
        TimeZoneControl
        ) {

        return Modal.extend({
            moduleId: module.id,
            className: Modal.CLASS_NAME + ' edit-dialog-modal modal-wide',

            events: $.extend({}, Modal.prototype.events, {
                'click .btn-primary': function(e) {
                    e.preventDefault();
                    var saveOptions = {};
                    if(this.options.isNew || this.options.isClone) {
                        var app = this.canUseApps ? this.model.entity.entry.acl.get('app') : "search";
                        saveOptions.data = {app: app, owner: 'nobody'};
                    }

                    if (_.isUndefined(this.model.entity.entry.get('name'))) {
                        this.model.entity.entry.set({name:''}, {silent:true});
                    }
                    
                    this.model.entity.entry.content.set('name', this.model.entity.entry.get('name')); 

                    if (this.options.isClone) {
                        this.model.entity.set('id', undefined);
                    }

                    saveOptions.headers = {'X-Splunk-Form-Key': splunkutil.getFormKey()};

                    // PASSWORD SETTINGS 
                    // When 'password' is empty, set it to 'Undefined' so the old password will be kept
                    if (_.isEmpty(this.model.entity.entry.content.get('password'))) {
                        this.model.entity.entry.content.unset('password');
                    } 

                    // Set isNew attribute for this.model.entity.entry.content for User modal validation purposes
                    if (this.options.isNew || this.options.isClone) {
                        this.model.entity.entry.content.set('isNew', true);
                    }

                    var entryValidation = this.model.entity.entry.validate();
                    var entryContentValidation = this.model.entity.entry.content.validate();

                    if (_.isUndefined(entryValidation) && _.isUndefined(entryContentValidation)) {
                        var saveDfd = this.model.entity.save({}, saveOptions);
                        if (saveDfd) {
                            saveDfd.done(function() {
                                this.trigger("entitySaved", this.model.entity.get("name"));
                                this.hide();
                            }.bind(this))
                            .fail(function() {
                                this.$el.find('.modal-body').animate({ scrollTop: 0 }, 'fast');
                            }.bind(this));
                        }
                    } else {
                        this.model.entity.trigger("serverValidated", true, this.model.entity, []);
                    }
                }
            }),

            initialize: function(options) {
                Modal.prototype.initialize.apply(this, arguments);
                options = options || {};
                _(options).defaults({isNew:true});

                var fcpBoolFlag = (options.isNew || options.isClone) ? true : false;
                _.defaults(this.model.entity.entry.content.attributes, {'force-change-pass':fcpBoolFlag});

                this.renderDfd = new $.Deferred();
                this.deferreds = options.deferreds;

                this.children.entityName = new ControlGroup({
                    controlType: 'Text',
                    controlOptions: {
                        modelAttribute: 'name',
                        model: this.model.entity.entry
                    },
                    controlClass: 'controls-block',
                    label: _('Name').t()
                });

                var availableItems = _.map(this.collection.roles.models, function(model) {
                    return {label:model.entry.get('name'), value:model.entry.get('name')};
                });
                
                var selectedItems = this.model.entity.entry.content.get('roles');
                selectedItems = _.isUndefined(selectedItems) ? ["user"] : selectedItems;

                this.children.roles = new ControlGroup({
                    controlType: 'Accumulator',
                    tooltip: _('Assign one or more roles to this user. The user will inherit all the settings and capabilities from these roles.').t(),
                    className: 'samlgroup-roles control-group',
                    controlOptions: {
                        modelAttribute: 'roles',
                        model: this.model.entity.entry.content,
                        availableItems: availableItems,
                        selectedItems: selectedItems
                    },
                    controlClass: 'controls-block',
                    label: _('Assign roles').t()
                });

                this.children.forceChangePass = new ControlGroup({
                    controlType: 'SyntheticCheckbox',
                    controlOptions: {
                        modelAttribute: 'force-change-pass',
                        model: this.model.entity.entry.content
                    },
                    label: _('Require password change on first login').t()
                });

                this.children.createRole = new ControlGroup({
                    controlType: 'SyntheticCheckbox',
                    controlOptions: {
                        modelAttribute: 'createrole',
                        model: this.model.entity.entry.content
                    },
                    label: _('Create a role for this user').t()
                });
				
				this.children.baseUserSettings = new BaseUserSettingsView({
					model: this.model,
					collection: this.collection,
                    isNew: this.options.isNew,
                    isClone: this.options.isClone,
                    canEditUser: this.options.canEditUser
				});

                this.children.unlockButton = new ControlGroup({
                    controlType: 'SyntheticCheckbox',
                    controlOptions: {
                        modelAttribute: 'locked-out',
                        model: this.model.entity.entry.content,
                        invertValue: true // when userLocked == true, button show and is unchecked; when button checked, userLocked set to false and won't appear next time
                    },
                    label: _('Select to unlock user').t()
                });

                this.children.timeZone = new ControlGroup({
                    controls: [
                        new TimeZoneControl({
                            model: this.model.entity.entry.content,
                            modelAttribute: 'tz',
                            showDefaultLabel: false,
                            toggleClassName: 'btn',
                            popdownOptions: {
                                attachDialogTo: 'body'
                            },
                            save: false
                        })
                    ],
                    label: _('Time zone').t(),
                    tooltip: _('Set a time zone for this user.').t()
                });

                this.children.defaultApp = new ControlGroup({
                    label: _('Default app').t(),
                    controlType: 'SyntheticSelect',
                    tooltip: _('Set a default app for this user. Setting this here overrides the default app inherited from the user\'s role(s).').t(),
                    controlOptions: {
                        modelAttribute: 'defaultApp',
                        model: this.model.entity.entry.content,
                        items: [],
                        className: 'fieldAppSelect',
                        toggleClassName: 'btn',
                        popdownOptions: {
                            detachDialog: true
                        },
                        save: false
                    }
                });

                this.children.flashMessagesView = new FlashMessages({
                    model: {
                        userEntityContentModel: this.model.entity.entry.content,
                        userEntityModel: this.model.entity.entry,
                        userModel: this.model.entity
                    }
                });
                
                $.when(
                    this.deferreds.entity,
                    this.deferreds.entities
                ).done(function(){
                    this.setDefaultAppItems();
                }.bind(this));

            },

            setDefaultAppItems: function(){
                var items = this.buildAppItems();
                this.children.defaultApp.childList[0].setItems(items);
                this.children.defaultApp.childList[0].setValue(this.model.entity.entry.content.get('defaultApp') || 'launcher');
            },

            buildAppItems: function(){
                var items = [];
                this.collection.appLocals.each(function(app){
                    items.push( {
                        value: app.entry.get('name'),
                        label: app.entry.get('name') + ' (' + app.entry.content.get('label') + ')'//do not translate app names
                    });
                });
                items.push( {value: 'launcher', label: _('launcher (Home)').t()} );
                return _.sortBy(items, function(item){
                    return (item.label||'').toLowerCase();
                });
            },

            render: function() {
                this.$el.html(Modal.TEMPLATE);
                var title = (this.options.isNew || this.options.isClone) ? _('Create User').t() : (_('Edit User: ').t() + ' ' + _.escape(this.model.entity.entry.get('name')));
                this.$(Modal.HEADER_TITLE_SELECTOR).html(title);
                this.$(Modal.BODY_SELECTOR).show();
                this.$(Modal.BODY_SELECTOR).append(Modal.FORM_HORIZONTAL);
                this.$(Modal.BODY_FORM_SELECTOR).html(_(this.dialogFormBodyTemplate).template({}));
                this.children.flashMessagesView.render().prependTo(this.$('.modal-body'));
                if (this.options.isNew || this.options.isClone) {
                    this.children.entityName.render().replaceAll(this.$(".name-placeholder"));
                    this.children.forceChangePass.render().replaceAll(this.$(".forceChangePass-placeholder"));
                    this.children.createRole.render().replaceAll(this.$(".createrole-placeholder"));
                } else {
                    // unset password attribute so the current password doesn't show 
                    this.model.entity.entry.content.unset('password');
                }
				this.children.baseUserSettings.render().replaceAll(this.$(".baseUserSettings-placeholder"));
                this.children.timeZone.render().replaceAll(this.$(".tz-placeholder"));
                this.children.defaultApp.render().replaceAll(this.$(".defaultApp-placeholder"));
                this.children.roles.render().replaceAll(this.$(".roles-placeholder"));
                if (this.model.entity.entry.content.get('locked-out')) {
                     this.children.unlockButton.render().replaceAll(this.$(".unlockButton-placeholder"));
                }

                this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CANCEL);
                this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_SAVE);

                this.renderDfd.resolve();

                return this;
            },

            dialogFormBodyTemplate: '\
                <div class="name-placeholder"></div>\
                <div class="baseUserSettings-placeholder"></div>\
                <div class="tz-placeholder"></div>\
                <div class="defaultApp-placeholder"></div>\
                <div class="roles-placeholder"></div>\
                <div class="createrole-placeholder"></div>\
                <div class="forceChangePass-placeholder"></div>\
                <div class="unlockButton-placeholder"></div>\
            '
        });
    });
