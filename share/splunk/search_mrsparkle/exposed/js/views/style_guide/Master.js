define(
    [
        'underscore',
        'jquery',
        'module',
        'views/Base',
        'prettify',
        'views/shared/timerangepicker/Master',
        'views/shared/jobstatus/SearchMode',
        'views/shared/eventsviewer/Master',
        'views/shared/searchbar/Master',
        'views/search/results/eventspane/controls/Master',
        'contrib/text!./Master.html',
        'contrib/google-code-prettify/prettify.css',
        'views/style_guide/Buttons/Master',
        'views/style_guide/Forms/Master',
        'views/style_guide/Navigation/Master',
        'views/style_guide/TimePicker/Master',
        './Master.pcss'
    ],
    function(
        _,
        $,
        module,
        BaseView,
        prettyPrint,
        TimeRangePicker,
        JobStatus,
        SearchMode,
        EventsViewer,
        SearchBar,
        template,
        cssPrettify,
        ButtonsView,
        FormsView,
        NavigationView,
        TimePickerView,
        css
    ) {
        return BaseView.extend({
            moduleId: module.id,
            events: {
                'click .content a': function(e) {
                    e.preventDefault();
                }
            },
            template: template,
            onAddedToDocument: function() {
                prettyPrint();
                var that = this;
                _.defer(function() {
                    this.$('.color-list li').each(function(index, el){
                        var $el = $(el);

                        $el.html('<span class="name">' + $el.attr('class') +  '</span><span class="hex">' + that.convertRGB($el.css('backgroundColor')) + '<span>');

                        if (that.luminosity($el.css('backgroundColor')) > 0.5) {
                            $el.addClass('light-color');
                        }
                    });
                });

                $(document.location.hash).show();
            },
            luminosity: function(rgb) {
                var rgbparse = rgb.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/);
                function hex(x) {
                    return ("0" + parseInt(x, 10).toString(16)).slice(-2);
                }
                if (rgbparse && rgbparse[1]) {
                    return (0.299*rgbparse[1]/255 + 0.587*rgbparse[2]/255 + 0.114*rgbparse[3]/255);
                }
                return;
            },
            convertRGB: function rgb2hex(rgb) {
                var rgbparse = rgb.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/);
                function hex(x) {
                    return ("0" + parseInt(x, 10).toString(16)).slice(-2);
                }
                if (rgbparse && rgbparse[1]) {
                    var hexValue = "#" + hex(rgbparse[1]) + hex(rgbparse[2]) + hex(rgbparse[3]);
                    return hexValue.toUpperCase();
                }
                return rgb;
            },
            initialize: function() {
                 BaseView.prototype.initialize.apply(this,arguments);
                 this.formsView = new FormsView();
                 this.buttonsView = new ButtonsView();
                 this.navigationView = new NavigationView();
                 this.timePickerView = new TimePickerView();
            },
            render: function() {
                this.$el.html(this.compiledTemplate());

                if (document.location.pathname.slice(-9) === 'lite.html') {
                    this.$('[data-nav=lite]').addClass('active');
                } else {
                    this.$('[data-nav=enterprise]').addClass('active');
                }

                this.formsView.render().appendTo(this.$('#form_template'));
                this.buttonsView.render().appendTo(this.$('#button_template'));
                this.navigationView.render().appendTo(this.$('#navigation_template'));
                this.timePickerView.render().appendTo(this.$('#time_template'));
                return this;
            }
        });
    }
);
