define(
    [
        'jquery',
        'underscore',
        'backbone',
        'module',
        'views/Base',
        'views/shared/controls/ControlGroup',
        'contrib/text!views/datapreview/settings/EventBreaks.html',
        '../Pane.pcss'
    ],
    function(
        $,
        _,
        Backbone,
        module,
        BaseView,
        ControlGroup,
        eventBreaksTemplate,
        css
    ){
        return BaseView.extend({
            moduleId: module.id,
            className: 'form form-horizontal eventBreaks',
            template: eventBreaksTemplate,
            initialize: function() {
                this.label = _('Presets').t();
                BaseView.prototype.initialize.apply(this, arguments);
                var model = this.model.sourcetypeModel;

                this.children.eventBreakMode = new ControlGroup({
                    label: _("Event-breaking Policy").t(),
                    controlType: 'SyntheticRadio',
                    className: 'control-group',
                    controlOptions: {
                        modelAttribute: 'ui.eventbreak.mode',
                        model: model,
                        items: [
                            { label: _("Auto").t(), value: 'auto', tooltip: _('Event breaks are auto detected based on timestamp location.').t() },
                            { label: _("Every Line").t(), value: 'everyline', tooltip: _('Every line is one event.').t() },
                            { label: _("Regex").t(), value: 'regex', tooltip: _('Use pattern to split events.').t() }
                        ],
                        save: false
                    }
                });

                var patternHelp = _('* Specifies a regex that determines how the raw text stream is broken into\
                        initial events, before line merging takes place.<br>\
                        *This sets SHOULD_LINEMERGE = false and LINE_BREAKER to the user-provided regular expression.<br>\
                        * Defaults to ([\\r\\n]+), \
                        meaning data is broken into an event for each line,\
                        delimited by any number of carriage return or newline characters.<br>\
                        * The regex must contain a capturing group -- a pair of parentheses which\
                        defines an identified subcomponent of the match.<br>\
                        * Wherever the regex matches, Splunk considers the start of the first\
                        capturing group to be the end of the previous event, and considers the end\
                        of the first capturing group to be the start of the next event.<br>\
                        * The contents of the first capturing group are discarded, and will not be\
                        present in any event. You are telling Splunk that this text comes between lines.').t();

                this.children.regexPattern = new ControlGroup({
                    label: _("Pattern").t(),
                    controlType: 'Text',
                    controlOptions: {
                        modelAttribute: 'ui.eventbreak.regex',
                        model: model,
                        save: false
                    },
                    help: patternHelp
                });

                this.setRegexDisplay();
                this.activate();
            },
            activate: function(options) {
                if (this.active) {
                    return BaseView.prototype.activate.apply(this, arguments);
                }

                this.model.sourcetypeModel.on('change:ui.eventbreak.mode', function(){
                    this.setRegexDisplay();
                }.bind(this));

                return BaseView.prototype.activate.apply(this, arguments);
            },
            deactivate: function(options) {
                if (!this.active) {
                    return BaseView.prototype.deactivate.apply(this, arguments);
                }
                BaseView.prototype.deactivate.apply(this, arguments);

                this.model.sourcetypeModel.off(null, null, this);

                return this;
            },
            setRegexDisplay: function(){
                if(this.model.sourcetypeModel.get('ui.eventbreak.mode') === 'regex'){
                    this.model.sourcetypeModel.set('ui.eventbreak.regexmode', 'linebreaker');
                    this.children.regexPattern.show();
                }else{
                    this.model.sourcetypeModel.unset('ui.eventbreak.regexmode');
                    this.children.regexPattern.hide();
                }
            },
            render: function() {
                this.$el.html(this.compiledTemplate({_:_}));
                this.$('.form-body').append(this.children.eventBreakMode.render().el);
                var indent = $('<div class="form-indent-section"></div>');
                indent.append(this.children.regexPattern.render().el);
                this.$('.form-body').append(indent);
                return this;
            }
        });
    }
);
