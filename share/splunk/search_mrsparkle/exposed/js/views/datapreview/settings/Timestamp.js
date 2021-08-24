define(
    [
        'underscore',
        'backbone',
        'module',
        'views/Base',
        'collections/shared/TimeZones',
        'contrib/text!views/datapreview/settings/Timestamp.html',
        'views/shared/controls/ControlGroup',
        'uri/route',
        'strftime' //no import
    ],
    function(
        _,
        Backbone,
        module,
        BaseView,
        TimeZones,
        timestampTemplate,
        ControlGroup,
        route
    ){
        return BaseView.extend({
            className: 'form form-horizontal timestamp',
            moduleId: module.id,
            template: timestampTemplate,
            events: {
                'change .timezoneSelect': 'onChangeTimezone'
            },
            initialize: function() {
                this.label = _('Presets').t();
                var timeZones = new TimeZones();
                this.timeZonesSelectOptions = _.map(timeZones.models, function(item) {
                    return {label: _.unescape(_(item.get('label')).t()), value: item.get('id')};
                });
                BaseView.prototype.initialize.apply(this, arguments);
                var self = this;

                this.children.timestampMode = new ControlGroup({
                    label: _("Extraction").t(),
                    controlType: 'SyntheticRadio',
                    className: 'control-group timestamp-mode',
                    controlOptions: {
                        modelAttribute: 'ui.timestamp.mode',
                        model: this.model.sourcetypeModel,
                        items: [
                            { label: _("Auto").t(), value: 'auto', tooltip: _("Auto").t()},
                            { label: _("Current time").t(), value: 'current', tooltip: _("Current time").t()},
                            { label: _("Advanced...").t(), value: 'advanced', tooltip: _("Advanced...").t()},
                            { label: _("Configuration file...").t(), value: 'filename', tooltip: _("Configuration file...").t()}
                        ],
                        elastic: true,
                        save: false
                    }
                });
                this.model.sourcetypeModel.on('change:ui.timestamp.mode', function(){
                    self.onSelectMode(self.model.sourcetypeModel.get('ui.timestamp.mode'));
                });

                this.children.timestampZone = new ControlGroup({
                    label: _("Time Zone").t(),
                    controlType: 'SyntheticSelect',
                    controlOptions: {
                        modelAttribute: 'ui.timestamp.timezone',
                        model: this.model.sourcetypeModel,
                        items: this.timeZonesSelectOptions,
                        additionalClassNames: 'timezoneSelect',
                        toggleClassName: 'btn',
                        menuWidth: 'wide',
                        popdownOptions: {
                            attachDialogTo: 'body'
                        },
                        save: false
                    }
                });

                var timeformatHelpLink = route.docHelp(
                    this.model.application.get('root'),
                    this.model.application.get('locale'),
                    'timeformat.preview'
                );

                var helpLinkString = _('A string in strptime() format that helps Splunk recognize timestamps. ').t() +
                    '<a class="external" target="_blank" href="' + timeformatHelpLink + '">' + _('Learn More').t() + '</a>';

                this.children.timestampFormat = new ControlGroup({
                    label: _("Timestamp format").t(),
                    controlType: 'Text',
                    help: helpLinkString,
                    controlOptions: {
                        modelAttribute: 'ui.timestamp.format',
                        model: this.model.sourcetypeModel,
                        save: false
                    }
                });

                this.children.timestampPrefix = new ControlGroup({
                    label: _("Timestamp prefix").t(),
                    controlType: 'Text',
                    help: _('Timestamp is always prefaced by a regex pattern eg: \\d+abc123\\d[2,4]').t(),
                    controlOptions: {
                        modelAttribute: 'ui.timestamp.prefix',
                        model: this.model.sourcetypeModel,
                        save: false
                    }
                });

                this.children.timestampLookahead = new ControlGroup({
                    label: _("Lookahead").t(),
                    controlType: 'Text',
                    help: _('Timestamp never extends more than this number of characters into the event, or past the Regex if specified above.').t(),
                    controlOptions: {
                        modelAttribute: 'ui.timestamp.lookahead',
                        model: this.model.sourcetypeModel,
                        save: false
                    }
                });

                this.children.timestampFields = new ControlGroup({
                    label: _("Timestamp fields").t(),
                    controlType: 'Text',
                    help: _('Specify all the fields which constitute the timestamp. ex: field1,field2,...,fieldn').t(),
                    controlOptions: {
                        modelAttribute: 'ui.timestamp.fields',
                        model: this.model.sourcetypeModel,
                        save: false
                    }
                });

                this.children.filename = new ControlGroup({
                    label: _("Configuration file").t(),
                    controlType: 'Text',
                    help: _('Configuration file for custom timestamp extractions from event data. File must reside in $SPLUNK_HOME and have .xml extension').t(),
                    controlOptions: {
                        modelAttribute: 'ui.timestamp.filename',
                        model: this.model.sourcetypeModel,
                        save: false
                    }
                });

                if(this.model.sourcetypeModel && this.model.sourcetypeModel.get('ui.timestamp.mode')){
                    this.onSelectMode(this.model.sourcetypeModel.get('ui.timestamp.mode'));
                }else{
                    this.onSelectMode('auto');
                }


            },
            render: function() {
                _.each(this.children, function(child){
                    child.detach();
                });

                this.$el.html(this.compiledTemplate({_:_}));
                var formBody = this.$el.find('.form-body');

                _.each(this.children, function(child){
                    formBody.append(child.render().el);
                });

                return this;
            },

            onSelectMode: function(mode){
                if(!mode){mode = 'auto';}

                switch(mode){
                    case 'auto':
                        this.children.timestampZone.$el.hide();
                        this.children.timestampFormat.$el.hide();
                        this.children.timestampPrefix.$el.hide();
                        this.children.timestampLookahead.$el.hide();
                        this.children.timestampFields.$el.hide();
                        this.children.filename.$el.hide();

                    break;
                    case 'current':
                        this.children.timestampZone.$el.hide();
                        this.children.timestampFormat.$el.hide();
                        this.children.timestampPrefix.$el.hide();
                        this.children.timestampLookahead.$el.hide();
                        this.children.timestampFields.$el.hide();
                        this.children.filename.$el.hide();

                    break;
                    case 'advanced':
                        this.children.timestampZone.$el.show();
                        this.children.timestampFormat.$el.show();
                        this.children.timestampPrefix.$el.show();
                        this.children.timestampLookahead.$el.show();
                        this.children.timestampFields.$el.show();
                        this.children.filename.$el.hide();

                    break;
                    case 'filename':
                        this.children.timestampZone.$el.hide();
                        this.children.timestampFormat.$el.hide();
                        this.children.timestampPrefix.$el.hide();
                        this.children.timestampLookahead.$el.hide();
                        this.children.timestampFields.$el.hide();
                        this.children.filename.$el.show();

                    break;
                    default:
                        this.children.timestampZone.$el.show();
                        this.children.timestampFormat.$el.show();
                        this.children.timestampPrefix.$el.show();
                        this.children.timestampLookahead.$el.show();
                        this.children.timestampFields.$el.show();
                        this.children.filename.$el.hide();
                    break;
                }

                if(this.model.sourcetypeModel.shouldUiExposeTimestampFieldSetting()){
                    this.children.timestampPrefix.$el.hide();
                    this.children.timestampLookahead.$el.hide();
                }else{
                    this.children.timestampFields.$el.hide();
                }

            }
        });
    }
);
