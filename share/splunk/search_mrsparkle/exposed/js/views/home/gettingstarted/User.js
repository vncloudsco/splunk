define([
    'underscore',
    'module',
    'uri/route',
    'views/Base',
    'views/home/gettingstarted/shared/Item',
    'views/shared/tour/ProductTours/Master'
],
function (
    _,
    module,
    route,
    BaseView,
    ItemView,
    ProductTours
) {
    return BaseView.extend({
        moduleId: module.id,
        initialize: function() {
            BaseView.prototype.initialize.apply(this, arguments);
            var hasTours = (this.collection && this.collection.tours) ? this.collection.tours.checkTours(this.model.user.serverInfo) : false;

            this.children.searchReference = new ItemView({
                url: route.docHelp(this.model.application.get("root"), this.model.application.get("locale"), "search.reference"),
                title: _("Search Manual").t(),
                icon:'\
                    <svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"\
                        width="50px" height="62px" viewBox="0 0 50 62" enable-background="new 0 0 50 62" xml:space="preserve" class="fill-svg">\
                        <path id="XMLID_468_" d="M39.1,32.7L32.4,26c-0.3,0.6-0.7,1.2-1.1,1.7l6.4,6.4c0.4,0.4,0.4,1,0,1.4l-0.2,0.2c-0.4,0.4-1,0.4-1.4,0\
                            l-6.4-6.4c-0.5,0.4-1.1,0.8-1.7,1.1l6.7,6.7c0.6,0.6,1.4,0.9,2.1,0.9c0.8,0,1.5-0.3,2.1-0.9l0.2-0.2C40.3,35.8,40.3,33.8,39.1,32.7z"/>\
                        <g id="XMLID_931_">\
                            <path id="XMLID_928_" d="M22.4,31.9c-6.3,0-11.4-5.1-11.4-11.4S16.2,9.1,22.4,9.1s11.4,5.1,11.4,11.4S28.7,31.9,22.4,31.9z\
                                M22.4,10.9c-5.3,0-9.6,4.3-9.6,9.6s4.3,9.6,9.6,9.6s9.6-4.3,9.6-9.6S27.7,10.9,22.4,10.9z"/>\
                        </g>\
                        <g id="XMLID_915_">\
                            <path id="XMLID_914_" d="M17.8,21h-1.8c0-4,2.9-6.9,5.9-6.9v1.8C20,15.9,17.8,18,17.8,21z"/>\
                        </g>\
                        <g id="XMLID_657_">\
                            <path id="XMLID_658_" d="M7.9,50c-0.9,0-2.3,1-2.3,2H47v-2H7.9z"/>\
                        </g>\
                        <g id="XMLID_655_">\
                            <path id="XMLID_656_" d="M7.9,57c-0.9,0-2.3-1-2.3-2H47v2H7.9z"/>\
                        </g>\
                        <path id="XMLID_653_" d="M49,62H8.5C4,62,0.3,58.4,0,54h0V10C0,4.5,4.5,0,10,0h37c1.7,0,3,1.3,3,3v41c0,1.7-1.3,3-3,3H8.5\
                            C4.9,47,2,49.9,2,53.5S4.9,60,8.5,60H49V62z M10,2c-4.4,0-8,3.6-8,8v38c1.5-1.8,3.8-3,6.4-3v0H47c0.6,0,1-0.4,1-1V3c0-0.6-0.4-1-1-1H10z"/>\
                    </svg>\
                ',
                external: true,
                description: _("Use the Splunk Search Processing Language (SPL).").t()
            });
            var pivotIcon = '\
                <svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"\
                    width="50px" height="62px" viewBox="0 0 50 62" enable-background="new 0 0 50 62" xml:space="preserve" class="fill-svg">\
                    <g id="XMLID_796_">\
                        <path id="XMLID_797_" d="M7.9,50c-0.9,0-2.3,1-2.3,2H47v-2H7.9z"/>\
                    </g>\
                    <g id="XMLID_794_">\
                        <path id="XMLID_795_" d="M7.9,57c-0.9,0-2.3-1-2.3-2H47v2H7.9z"/>\
                    </g>\
                    <path id="XMLID_778_" d="M49,62H8.5C4,62,0.3,58.4,0,54h0V10C0,4.5,4.5,0,10,0h37c1.7,0,3,1.3,3,3v41c0,1.7-1.3,3-3,3H8.5\
                        C4.9,47,2,49.9,2,53.5S4.9,60,8.5,60H49V62z M10,2c-4.4,0-8,3.6-8,8v38c1.5-1.8,3.8-3,6.4-3v0H47c0.6,0,1-0.4,1-1V3c0-0.6-0.4-1-1-1H10z"/>\
                    <path id="XMLID_472_" d="M39,10H20h-2h-3c-1.1,0-2,0.9-2,2v3v2v19c0,1.1,0.9,2,2,2h3c1.1,0,2-0.9,2-2V17h19c1.1,0,2-0.9,2-2v-3\
                        C41,10.9,40.1,10,39,10z M15,12h3v3h-3V12z M18,36h-3V17h3V36z M39,15H20v-3h19V15z"/>\
                    <path id="XMLID_477_" d="M36.7,22H39l-3-3l-3,3h1.6c-1.1,4.7-4.6,7.7-9.6,8.4v-1.9l-3,3l3,3v-2.1C31.2,31.7,35.5,27.8,36.7,22z"/>\
                </svg>\
            ';

            this.children.pivotManual = new ItemView({
                url: route.docHelp(this.model.application.get("root"), this.model.application.get("locale"), "pivot.manual"),
                title: _("Pivot Manual").t(),
                icon: pivotIcon,
                external: true,
                description: _("Use Pivot to create tables and charts with SPL.").t()
            });
            var vizIcon = '\
                <svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"\
                    width="50px" height="62px" viewBox="0 0 50 62" enable-background="new 0 0 50 62" xml:space="preserve" class="fill-svg">\
                    <g id="XMLID_676_">\
                        <path id="XMLID_677_" d="M7.9,50c-0.9,0-2.3,1-2.3,2H47v-2H7.9z"/>\
                    </g>\
                    <g id="XMLID_674_">\
                        <path id="XMLID_675_" d="M7.9,57c-0.9,0-2.3-1-2.3-2H47v2H7.9z"/>\
                    </g>\
                    <path id="XMLID_672_" d="M49,62H8.5C4,62,0.3,58.4,0,54h0V10C0,4.5,4.5,0,10,0h37c1.7,0,3,1.3,3,3v41c0,1.7-1.3,3-3,3H8.5\
                        C4.9,47,2,49.9,2,53.5S4.9,60,8.5,60H49V62z M10,2c-4.4,0-8,3.6-8,8v38c1.5-1.8,3.8-3,6.4-3v0H47c0.6,0,1-0.4,1-1V3c0-0.6-0.4-1-1-1H10z"/>\
                    <polygon id="XMLID_944_" points="9.6,19.8 8.4,18.2 16.9,11.8 24.9,15.8 33,9.7 41.7,17.2 40.3,18.8 33,12.3 25.1,18.2 17.1,14.2"/>\
                    <g id="XMLID_943_">\
                        <rect id="XMLID_942_" x="31" y="25" width="2" height="12"/>\
                    </g>\
                    <g id="XMLID_941_">\
                        <rect id="XMLID_940_" x="27" y="29" width="2" height="8"/>\
                    </g>\
                    <g id="XMLID_939_">\
                        <rect id="XMLID_938_" x="35" y="21" width="2" height="16"/>\
                    </g>\
                    <g id="XMLID_937_">\
                        <rect id="XMLID_667_" x="39" y="29" width="2" height="8"/>\
                    </g>\
                        <path id="XMLID_467_" d="M16.8,22.2c-4.1,0-7.5,3.4-7.5,7.5s3.4,7.5,7.5,7.5s7.5-3.4,7.5-7.5S20.9,22.2,16.8,22.2z M22.2,29H18v-4.7\
                    C20.2,24.8,22,26.7,22.2,29z M16.8,35.2c-3,0-5.5-2.5-5.5-5.5c0-2.8,2.1-5.1,4.7-5.4V31h6.1C21.5,33.4,19.4,35.2,16.8,35.2z"/>\
                </svg>\
            ';

            this.children.dashboardVisualizations = new ItemView({
                url: route.docHelp(this.model.application.get("root"), this.model.application.get("locale"), "dashboards.visualizations"),
                title: _("Dashboards & Visualizations").t(),
                icon: vizIcon,
                external: true,
                description: _("Create and edit dashboards using interactive editors or simple XML.").t()
            });

            if (hasTours) {
                this.children.tours = new ItemView({
                    url: '#',
                    linkClass: 'product-tours',
                    title: _("Product Tours").t(),
                    icon: '\
                        <svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"\
                             width="62px" height="62px" viewBox="0 0 62 62" enable-background="new 0 0 62 62" xml:space="preserve" class="fill-svg">\
                            <g id="XMLID_854_">\
                                <g id="XMLID_855_">\
                                    <g id="XMLID_856_">\
                                        <g id="XMLID_857_">\
                                            <g id="XMLID_858_">\
                                                <path id="XMLID_1050_" d="M31,30c-2.2,0-4-1.8-4-4s1.8-4,4-4s4,1.8,4,4S33.2,30,31,30z M31,24c-1.1,0-2,0.9-2,2s0.9,2,2,2\
                                                    s2-0.9,2-2S32.1,24,31,24z"/>\
                                            </g>\
                                        </g>\
                                    </g>\
                                </g>\
                            </g>\
                            <path id="XMLID_830_" d="M60.9,49c-0.2-3-0.7-12.3-0.9-16.1c-0.2-3-1.6-5.2-2.7-6.9C56.6,25,56,24,56,23.2V9c0-1.7-1.3-3-3-3h-0.1\
                                l0.6-3.7c0.1-0.6-0.1-1.2-0.4-1.6S52.2,0,51.6,0H38c-0.6,0-1.1,0.3-1.5,0.7c-0.4,0.4-0.5,1-0.4,1.6L36.6,6H34v9h-6V6h-2.7L26,2.3\
                                c0.1-0.6-0.1-1.2-0.4-1.6C25.1,0.3,24.6,0,24,0H10.4C9.8,0,9.2,0.3,8.8,0.7c-0.4,0.4-0.5,1-0.4,1.6L9,6h0C7.3,6,6,7.3,6,9v14.2\
                                C6,24,5.4,25,4.7,26.1c-1.1,1.7-2.5,3.8-2.7,6.9C1.7,36.7,1.2,46,1.1,49H0v10c0,1.7,1.3,3,3,3h23c1.7,0,3-1.3,3-3V49h-1V36h6v13h-1\
                                v10c0,1.7,1.3,3,3,3h23c1.7,0,3-1.3,3-3V49H60.9z M51.6,2l-0.7,4H38.7L38,2H51.6z M10.4,2H24l-0.7,4H11.1L10.4,2z M27,59\
                                c0,0.6-0.4,1-1,1H3c-0.6,0-1-0.4-1-1v-8h25V59z M26,34v15H3.1C3.2,45.9,3.7,36.8,4,33.1c0.2-2.5,1.3-4.3,2.4-5.9\
                                C7.2,25.9,8,24.6,8,23.2V9c0-0.6,0.4-1,1-1h17v9h10V8h17c0.6,0,1,0.4,1,1v14.2c0,1.4,0.8,2.6,1.6,3.9c1,1.6,2.2,3.4,2.4,5.9\
                                c0.3,3.7,0.8,12.8,0.9,15.9H36V34H26z M60,59c0,0.6-0.4,1-1,1H36c-0.6,0-1-0.4-1-1v-8h25V59z"/>\
                        </svg>\
                    ',
                    external: false,
                    description: _("New to Splunk? Take a tour to help you on your way.").t()
                });
            }
        },

        events: {
            'click .product-tours': function() {
                this.children.toursModal = new ProductTours({
                    canAddData: this.model.user.canAddData(),
                    model: {
                        application: this.model.application,
                        serverInfo: this.model.user.serverInfo
                    }
                });
                this.children.toursModal.render().el;
                this.children.toursModal.show();
            }
        },

        render: function() {
            var html = this.compiledTemplate();
            this.$el.append(html);
            if (this.children.tours) {
                this.children.tours.render().appendTo(this.$el);
            }
            this.children.searchReference.render().appendTo(this.$el);
            this.children.pivotManual.render().appendTo(this.$el);
            this.children.dashboardVisualizations.render().appendTo(this.$el);
            return this;
        }, 
        template: '\
        '

    });
});

