define([
    'underscore',
    'module',
    'views/Base',
    './Empty.pcss',
    'util/keyboard',
    'uri/route'
],
function (
    _,
    module,
    BaseView,
    css,
    keyboardUtil,
    route
) {
    return BaseView.extend({
        moduleId: module.id,
        initialize: function() {
            BaseView.prototype.initialize.apply(this, arguments);
            this.listenTo(this.model.dashboard, 'change:id', this.render);
        },
        events: {
            'click a': function(e) {
                this.trigger('showDashboardSelector');
            },
            'keyup a': function(e) {
                if (e.which === keyboardUtil.KEYS['ENTER']) {
                    this.trigger('showDashboardSelector');
                }
            }
        },
        render: function() {
            this.$el.html(this.compiledTemplate({
                _: _,
               dashboard: this.model.dashboard,
               isSimpleXML: !this.model.dashboard.isNew() && this.model.dashboard.isSimpleXML(),
               isValidXML: !this.model.dashboard.isNew() && this.model.dashboard.isValidXML()
            }));
            return this;
        },
        template: '\
            <% if (!dashboard.isNew() && (!isSimpleXML || !isValidXML)) { %>\
                <div class="alert alert-error"><i class="icon-alert"></i>Could not load dashboard.</div>\
            <%}%>\
            <a tabindex="0" class="add-dashboard-link">\
            <svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"\
                width="72px" height="60px" viewBox="0 0 72 60" enable-background="new 0 0 72 60" xml:space="preserve">\
                <path id="XMLID_831_" d="M68,0H4C1.8,0,0,1.8,0,4v44c0,2.2,1.8,4,4,4h27v6H19v2h34v-2H41v-6h27c2.2,0,4-1.8,4-4V4\
                    C72,1.8,70.2,0,68,0z M39,58h-6v-6h6V58z M70,48c0,1.1-0.9,2-2,2H4c-1.1,0-2-0.9-2-2V4c0-1.1,0.9-2,2-2h64c1.1,0,2,0.9,2,2V48z"/>\
                <path id="XMLID_1058_" d="M67,47H5V5h62V47z M7,45h58V7H7V45z"/>\
                <polygon id="XMLID_521_" points="54,13.9 45.1,17.8 35.9,10.7 26.9,19.7 17.9,13.7 10,20.8 10,23.4 18.1,16.3 27.1,22.3 36.1,13.3 \
                    44.9,20.2 54,16.1 61,19.2 61,17 "/>\
                <g id="XMLID_1031_">\
                    <rect id="XMLID_1030_" x="35" y="29" width="2" height="12"/>\
                </g>\
                <g id="XMLID_1029_">\
                    <rect id="XMLID_1028_" x="59" y="29" width="2" height="12"/>\
                </g>\
                <g id="XMLID_1027_">\
                    <rect id="XMLID_1026_" x="31" y="33" width="2" height="8"/>\
                </g>\
                <g id="XMLID_1025_">\
                    <rect id="XMLID_1024_" x="39" y="25" width="2" height="16"/>\
                </g>\
                <g id="XMLID_1023_">\
                    <rect id="XMLID_1022_" x="43" y="27" width="2" height="14"/>\
                </g>\
                <g id="XMLID_1021_">\
                    <rect id="XMLID_1020_" x="55" y="27" width="2" height="14"/>\
                </g>\
                <g id="XMLID_1019_">\
                    <rect id="XMLID_1018_" x="51" y="30" width="2" height="11"/>\
                </g>\
                <g id="XMLID_1017_">\
                    <rect id="XMLID_836_" x="47" y="31" width="2" height="10"/>\
                </g>\
                <path id="XMLID_843_" d="M17.8,26.2c-4.1,0-7.5,3.4-7.5,7.5s3.4,7.5,7.5,7.5s7.5-3.4,7.5-7.5S21.9,26.2,17.8,26.2z M23.2,33H19v-4.7\
                    C21.2,28.8,23,30.7,23.2,33z M17.8,39.2c-3,0-5.5-2.5-5.5-5.5c0-2.8,2.1-5.1,4.7-5.4V35h6.1C22.5,37.4,20.4,39.2,17.8,39.2z"/>\
            </svg>\
            <span class="choose-a-dashboard"><%- _("Choose a home dashboard").t() %></span>\
            </a>\
        '
    });
});
