/**
 *
 * Dialog that allows the user to create a new Data Model
 *
 * events:
 *      action:uploadedDataModel (fileName) - Dispatched when the user has pressed the Save button
 */
define(
    [
        'jquery',
        'underscore',
        'backbone',
        'splunk.util',
        'views/shared/dialogs/UploadDataModelDialogBase',
        'views/shared/controls/ControlGroup',
        'views/shared/controls/SyntheticCheckboxControl',
        'views/shared/controls/SyntheticSelectControl',
        'views/shared/controls/TextControl',
        'views/data_models/FileUploadControl',
        'views/shared/FlashMessages',
        'models/datamodel/UploadDataModel',
        'models/services/datamodel/DataModel',
        'util/datamodel/form_utils',
        'module'
    ],
    function(
        $,
        _,
        Backbone,
        splunkUtil,
        DialogBase,
        ControlGroup,
        SyntheticCheckboxControl,
        SyntheticSelectControl,
        TextControl,
        FileUploadControl,
        FlashMessagesView,
        UploadDataModel,
        DataModel,
        dataModelFormUtils,
        module
        )
    {
        return DialogBase.extend({
                moduleId: module.id,
                className: "modal fade modal-narrow create-data-model-dialog form form-horizontal",
                events: {
                    'change #uploadedFile': function(e) {
                        this.handleFileSelect(e);
                        //this.children.dataModelController.trigger("action:createDataModel");
                    }
                },
                modelToControlGroupMap: {
                    displayName: "fileContents"
                },

                initialize: function(options) {
                    DialogBase.prototype.initialize.call(this, options);

                    this.settings.set("primaryButtonLabel", _("Upload").t());
                    this.settings.set("cancelButtonLabel", _("Cancel").t());
                    this.settings.set("titleLabel", _("Upload New Data Model").t());

                    var applicationApp = this.model.application.get("app");
                    var useApplicationApp = false;
                    var appItems = [];

                    this.collection.apps.each(function(model){
                        if (model.entry.acl.get("can_write")) {
                            appItems.push({
                                label: model.entry.content.get('label'),
                                value: model.entry.get('name')
                            });
                            if (model.entry.get('name') == applicationApp)
                                useApplicationApp = true;
                        }
                    }, this);

                    if (!useApplicationApp) {
                        if (appItems.length > 0)
                            applicationApp = appItems[0].value;
                        else
                            applicationApp = undefined;
                    }

                    this.model.uploadDataModel = new UploadDataModel({fileContents:"", app: applicationApp});

                    this.fileNameControl = new FileUploadControl({modelAttribute: 'fileContents',
                        model: this.model.uploadDataModel});

                    this.textModelNameControl = new TextControl({modelAttribute: 'modelName',
                        model: this.model.uploadDataModel});

                    this.children.fileName = new ControlGroup({
                        label:_("File").t(),
                        controls: this.fileNameControl,

                        controlOptions: {
                            modelAttribute:"uploadedFile",
                            model:this.model.uploadDataModel
                        }
                    });

                    this.model.uploadDataModel.on('change:fileContents', this.handleFileUploaded, this);

                    this.children.textModelName = new ControlGroup({
                        label:_("ID").t(),
                        tooltip: _('The ID is used as the filename on disk and used in the data model search command. Cannot be changed later.').t(),
                        help: _('The data model ID can only contain letters, numbers, dashes, and underscores. Do not start the data model ID with a period.').t(),
                        controls: this.textModelNameControl
                    });

                    this.children.selectApp = new ControlGroup({
                        label:_("App").t(),
                        controlType: "SyntheticSelect",

                        controlOptions: {
                            modelAttribute:"app",
                            model:this.model.uploadDataModel,
                            toggleClassName: 'btn',
                            items: appItems,
                            popdownOptions: {
                                attachDialogTo: '.modal:visible',
                                scrollContainer: '.modal:visible .modal-body:visible'
                            }
                        }
                    });

                    this.model.newDataModel = new DataModel();
                    this.children.flashMessagesView = new FlashMessagesView({model: [this.model.uploadDataModel, this.model.newDataModel]});
                    this.model.uploadDataModel.set('dashPerm', 'private');
                },

                handleFileUploaded: function() {
                    this.model.uploadDataModel.clearErrors();
                    var stringifiedJSON = this.model.uploadDataModel.get('fileContents');
                    var json;
                    try {
                        json = JSON.parse(stringifiedJSON);
                        json.description = stringifiedJSON;
                        var wrappedContents = {};
                        wrappedContents.entry = [];
                        wrappedContents.entry.push({content: json});
                        this.model.newDataModel.parseFile(wrappedContents);
                        var modelID = dataModelFormUtils.normalizeForID(this.model.newDataModel.entry.content.get('displayName'));
                        this.model.uploadDataModel.set('modelName', modelID);

                    } catch (e) {
                        this.model.uploadDataModel.trigger('error', this.model.uploadDataModel, 'File contains invalid json');
                        return;
                    }

                },

                primaryButtonClicked: function() {
                    DialogBase.prototype.primaryButtonClicked.apply(this, arguments);

                    if (this.model.uploadDataModel.set({}, {validate:true}))
                    {

                        var dashPerm = this.model.uploadDataModel.get("dashPerm");
                        var data = this.model.application.getPermissions(dashPerm);
                        data.app = this.model.uploadDataModel.get("app");
                        this.model.newDataModel.entry.content.set('name', this.model.uploadDataModel.get('modelName'));

                        this.model.newDataModel.entry.content.isCreating = true;

                        var resultXHR = this.model.newDataModel.save({}, {data: data});
                        if (resultXHR) {
                            resultXHR.done(_(function() {
                                this.hide();
                                this.model.newDataModel.entry.content.isCreating = false;
                                this.trigger("action:uploadedDataModel", this.model.newDataModel);
                            }).bind(this));
                        }

                    }
                },

                renderBody : function($el) {
                    var html = _(this.bodyTemplate).template({});
                    $el.html(html);
                    $el.find(".flash-messages-view-placeholder").append(this.children.flashMessagesView.render().el);
                    $el.find(".data-model-file-name-placeholder").append(this.children.fileName.render().el);
                    $el.find(".data-model-model-name-placeholder").append(this.children.textModelName.render().el);
                    $el.find(".data-model-app-placeholder").append(this.children.selectApp.render().el);
                },


                bodyTemplate: '\
                    <div class="flash-messages-view-placeholder"></div>\
                    <div class="data-model-file-name-placeholder"></div>\
                    <div class="data-model-model-name-placeholder"></div>\
                    <div class="data-model-app-placeholder"></div>\
                '
            }
        );}
);
