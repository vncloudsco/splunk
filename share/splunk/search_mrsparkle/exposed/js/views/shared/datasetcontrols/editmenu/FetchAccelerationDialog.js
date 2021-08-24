define([
        'jquery',
        'underscore',
        'backbone',
        'module',
        'collections/services/data/vix/Indexes',
        'collections/services/data/vix/Archives',
        'views/shared/Modal',
        'views/shared/FlashMessages',
        'views/shared/dialogs/TextDialog',
        'views/data_model_manager/components/AccelerationDialog',
        'views/data_model_manager/components/PermissionsDialog',
        'uri/route',
        'splunk.util'
    ],
    function(
        $,
        _,
        Backbone,
        module,
        VixIndexCollection,
        ArchivesCollection,
        Modal,
        FlashMessages,
        TextDialog,
        AccelerationDialog,
        PermissionsDialog,
        route,
        splunkUtil
    ) {
        return Modal.extend({
            moduleId: module.id,

            initialize: function(options) {
                Modal.prototype.initialize.apply(this, arguments);

                this.collection.vix = new VixIndexCollection();
                this.collection.archives = new ArchivesCollection();

                this.children.flashMessages = new FlashMessages({
                    model: this.model.dataset
                });
            },

            events: $.extend({}, Modal.prototype.events, {
                'click a.edit-permissions': function(e) {
                    this.hide();
                    
                    this.children.permissionsDialog = new PermissionsDialog({
                        model: {
                            document: this.model.dataset,
                            nameModel: this.model.dataset.entry,
                            user: this.model.user,
                            serverInfo: this.model.serverInfo,
                            application: this.model.application
                        },
                        collection: this.collection.roles,
                        onHiddenRemove: true,
                        nameLabel: this.model.dataset.getDatasetDisplayType()
                    });

                    this.children.permissionsDialog.render().appendTo($("body"));
                    this.children.permissionsDialog.show();
                    e.preventDefault();
                    
                    this.listenTo(this.children.permissionsDialog, 'hidden', function() {
                        this.remove();
                    }.bind(this));
                }
            }),

            handleFetchDataset: function() {
                var $loadingMessage = this.$('.loading-message'),
                    datasetDeferred = this.model.dataset.fetch();

                $.when(datasetDeferred).then(function() {
                    var accelerationHelpLink = route.docHelp(
                        this.model.application.get('root'),
                        this.model.application.get('locale'),
                        'learnmore.datasets.acceleration'
                    );
                    
                    // The REST API determines if the datamodel can be accelerated based on its configuration and returns this flag
                    if (!this.model.dataset.canAccelerate()) {
                        $loadingMessage.hide();
                        
                        this.$(Modal.BODY_SELECTOR).append(_(this.accelerationWarningTemplate).template({
                            datasetType: this.model.dataset.getType(),
                            accelerationHelpLink: accelerationHelpLink,
                            _: _
                        }));
                        this.on('hidden', this.remove, this);
                        
                    } else if (this.model.dataset.isPrivate()) {
                        $loadingMessage.hide();
                        
                        this.$(Modal.BODY_SELECTOR).append(_(this.permissionsWarningTemplate).template({
                            datasetType: this.model.dataset.getType(),
                            _: _
                        }));
                        this.$(Modal.FOOTER_SELECTOR).empty();
                        this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CANCEL);
                        this.$(Modal.FOOTER_SELECTOR).append(_(this.editPermissionsButtonTemplate).template({
                            _: _
                        }));
                        
                    } else {
                        this.collection.vix.fetchData.set({'count': 0}, {silent:true});
                        var vixFetch = this.collection.vix.fetch();
                        
                        this.collection.archives.fetchData.set({'count': 0}, {silent:true});
                        var archiveFetch = this.collection.archives.fetch();
                        
                        $.when(vixFetch, archiveFetch).then(function() {
                            this.hide();
                            
                            this.children.accelerationDialog = new AccelerationDialog({
                                model: {
                                    dataModel: this.model.dataset,
                                    application: this.model.application
                                },
                                collection: {
                                    vix: this.collection.vix,
                                    archives: this.collection.archives
                                },
                                onHiddenRemove: true,
                                nameLabel: this.model.dataset.getDatasetDisplayType()
                            });
                            
                            this.children.accelerationDialog.render().appendTo($("body"));
                            this.children.accelerationDialog.show();
                            
                            this.listenTo(this.children.accelerationDialog, 'hide', function() {
                                this.remove();
                                this.model.dataset.trigger('updateCollection');
                            }.bind(this));
                            
                            this.listenTo(this.children.accelerationDialog, 'action:saveModel', function() {
                                var accelerated = this.model.dataset.entry.content.acceleration.get("enabled");
                                this.model.dataset.entry.content.set('accelerated',  !!accelerated);
                                
                                this.model.dataset.save({}, {
                                    success: function(model, response) {
                                        this.children.accelerationDialog.hide();
                                        this.children.accelerationDialog.cleanup();
                                        this.children.accelerationDialog.remove();
                                    }.bind(this)
                                });
                            }.bind(this));
                        }.bind(this));
                    }
                   
                }.bind(this));
            },

            render: function() {
                this.$el.html(Modal.TEMPLATE);
                this.children.flashMessages.render().prependTo(this.$(Modal.BODY_SELECTOR));
                this.$(Modal.HEADER_TITLE_SELECTOR).html(_("Edit Dataset Acceleration").t());
                this.$(Modal.BODY_SELECTOR).append(_(this.loadingTemplate).template({
                    _: _
                }));
                this.$(Modal.FOOTER_SELECTOR).append(Modal.BUTTON_CLOSE);

                this.handleFetchDataset();

                return this;
            },

            loadingTemplate: '\
                <span class="loading-message"><%- _("Loading...").t() %></span>\
            ',

            accelerationWarningTemplate: '\
                <% if (datasetType === "table") { %>\
                    <span class="acceleration-warning"><%= _("This table dataset cannot be accelerated because its search includes streaming commands.").t() %></span>\
                    <a class="external datasets-help-link" href="<%- accelerationHelpLink %>" target="_blank"><span><%- _("Learn more.").t() %></span></a>\
                <% } else { %>\
                    <span class="acceleration-warning"><%= _("You can only accelerate data models that include at least one event-based dataset or one search-based dataset that does not include streaming commands.").t() %></span>\
                <% } %>\
            ',

            permissionsWarningTemplate: '\
                <% if (datasetType === "table") { %>\
                    <span class="acceleration-warning"><%= _("Private table datasets cannot be accelerated. Edit the permissions before enabling acceleration.").t() %></span>\
                <% } else { %>\
                    <span class="acceleration-warning"><%= _("Private data models cannot be accelerated. Edit the permissions before enabling acceleration.").t() %></span>\
                <% } %>\
            ',

            editPermissionsButtonTemplate: '\
                <a href="#" class="btn edit-permissions"><%- _("Edit Permissions").t() %></a>\
            '
        });
    });
