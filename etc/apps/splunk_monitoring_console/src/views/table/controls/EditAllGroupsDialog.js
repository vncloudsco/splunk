define(
    [
        'jquery',
        'underscore',
        'backbone',
        'module',
        'collections/shared/FlashMessages',
        'views/shared/Modal',
        'views/shared/controls/ControlGroup',
        'splunk_monitoring_console/views/table/controls/MultiInputControl',
        'splunk_monitoring_console/views/table/controls/EditAllSuccessFailureDialog',
        'views/shared/FlashMessagesLegacy'
    ],
    function(
        $,
        _,
        Backbone,
        module,
        FlashMessagesCollection,
        Modal,
        ControlGroup,
        MultiInputControl,
        EditAllSuccessFailureDialog,
        FlashMessagesView
    ) {
        return Modal.extend({
            moduleId: module.id,
            initialize: function() {
                Modal.prototype.initialize.apply(this, arguments);

                this.model.working = new Backbone.Model({
                    'tags': ''
                });

                this._warningMessageIsShowing = false;

                this.collection = this.collection || {};
                this.collection.flashMessages = new FlashMessagesCollection();

                this.groupTagsInputControl = new MultiInputControl({
                    model: this.model.working,
                    collection: this.collection.peers,
                    modelAttribute: 'tags',
                    attributeType: 'array',
                    placeholder: _('Choose groups').t(),
                    collectionMethod: 'getAllTags'
                });

                this.children.groupTags = new ControlGroup({
                    label: _("Group Tags").t(),
                    controlClass: 'controls-block',
                    controls: [this.groupTagsInputControl]
                });

                this.children.flashMessage = new FlashMessagesView({
                    collection: this.collection.flashMessages
                });

            },
            events: $.extend({}, Modal.prototype.events, {
                'click .btn-primary': function(e) {
                    e.preventDefault();

                    if(!this._warningMessageIsShowing) {
                        this._warningMessageIsShowing = true;
                        this.collection.flashMessages.reset([{
                            type: 'warning',
                            html: _("Saving group tags will overwrite all existing group tags.").t()
                        }]);
                        return;
                    }

                    var tags = this.model.working.get('tags');
                    tags = $.trim(tags) ? tags.split(',') : [];

                    this.collection.flashMessages.reset();

                    var selected_peers = this.collection.peers.filter(function(peer){
                        return peer.get('bulk-selected');
                    });

                    var error = _.chain(selected_peers).map(function(peer){
                        return peer.entry.content.validate({'tags': tags});
                    }).filter(function(message){
                        return message;
                    }).first().value();

                    if (error) {
                        this.collection.flashMessages.reset([{
                            type: 'error',
                            html: error
                        }]);
                        return;
                    }

                    _(selected_peers).each(function(peer) {
                        peer.entry.content.set('tags', tags);
                    }.bind(this));

                    $(e.target).prop('disabled', true);
                    $.when(this.collection.peers.saveSelected()).done(function() {
                        this.model.state.set('changesMade', true);
                        this.hide();
                        var dialog = new EditAllSuccessFailureDialog({
                            title: _("Set Custom Groups").t(),
                            message: _("Selected instances successfully updated.").t()
                        });
                        $('body').append(dialog.render().el);
                        dialog.show();
                    }.bind(this)).fail(function() {
                        this.model.state.set('changesMade', true);
                        this.hide();
                        var dialog = new EditAllSuccessFailureDialog({
                            title: _("Set Custom Groups").t(),
                            message: _("Failed to update selected instances. Please try again later").t()
                        });
                        $('body').append(dialog.render().el);
                        dialog.show();
                    }.bind(this));
                }
            }),
            render: function() {
                this.$el.html(Modal.TEMPLATE);
                this.$(Modal.HEADER_TITLE_SELECTOR).html(_("Set Group Tags").t());
                this.$(Modal.BODY_SELECTOR).prepend(this.children.flashMessage.render().el);
                this.$(Modal.BODY_SELECTOR).append(Modal.FORM_HORIZONTAL);
                this.$(Modal.BODY_FORM_SELECTOR).append(this.children.groupTags.render().el);
                this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CANCEL);
                this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_SAVE);
                return this;
            }
        });
    }
);