define([
    'underscore',
    'module',
    'uri/route',
    'views/Base',
    'views/home/gettingstarted/shared/Item',
    'views/shared/tour/ProductTours/Master',
    'splunk.util'
],
function (
    _,
    module,
    route,
    BaseView,
    ItemView,
    ProductTours,
    splunkUtil
) {
    return BaseView.extend({
        moduleId: module.id,
        initialize: function() {
            BaseView.prototype.initialize.apply(this, arguments);
            var showDocsButton = true;

            var showAddDataButton = this.collection.managers.findByEntryName('adddata') && this.model.user.canAddData(),
                showExploreDataButton =  this.collection.managers.findByEntryName('explore_data') && this.model.user.canExploreData(),
                hasTours = (this.collection && this.collection.tours) ? this.collection.tours.checkTours(this.model.user.serverInfo) : false;

            // For layout reasons remove docs when showing explore and adddata.
            if(showAddDataButton && showExploreDataButton) {
                showDocsButton = false;
            }

            if (showAddDataButton) {
                var extractFieldsUrl = route.page(this.model.application.get('root'), this.model.application.get('locale'), 'search', 'field_extractor'),
                    extractFieldsLink = "<a href='" + extractFieldsUrl + "'>" + _("extract fields").t() + "</a>";
                this.children.addData = new ItemView({
                    url: route.addData(this.model.application.get('root'), this.model.application.get('locale')),
                    title: _("Add Data").t(),
                    icon: '\
                        <svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"\
                            width="72px" height="62px" viewBox="0 0 72 62" enable-background="new 0 0 72 62" xml:space="preserve" class="fill-svg">\
                            <path id="XMLID_654_" d="M44,54H4.3C3.1,54,2,53.1,2,52.3V39.7C2,38.9,3.1,38,4.3,38H44c0.4-0.7,1-1.4,1.5-2H4.3\
                                C3.1,36,2,35.1,2,34.3V21.7C2,20.9,3.1,20,4.3,20h52.1c1.2,0,1.7,0.9,1.7,1.7V30c0.3,0,0.7-0.1,1-0.1s0.7,0,1,0.1v-8.3\
                                c0-1.1-0.4-2.1-1.1-2.7c0.7-0.7,1.1-1.6,1.1-2.7V3.7C60,1.6,58.5,0,56.3,0H4.3C2,0,0,1.7,0,3.7v12.5c0,1.1,0.6,2,1.4,2.7\
                                C0.6,19.7,0,20.7,0,21.7v12.5c0,1.1,0.6,2,1.4,2.7C0.6,37.7,0,38.7,0,39.7v12.5c0,2,2,3.7,4.3,3.7h41.2C45,55.4,44.4,54.7,44,54z\
                                M2,3.7C2,2.9,3.1,2,4.3,2h52.1C57.6,2,58,2.9,58,3.7v12.5c0,0.8-0.4,1.7-1.7,1.7H4.3C3.1,18,2,17.1,2,16.3V3.7z"/>\
                            <polygon id="XMLID_818_" points="65,45 60,45 60,40 58,40 58,45 53,45 53,47 58,47 58,52 60,52 60,47 65,47 "/>\
                            <rect id="XMLID_817_" x="6" y="5" width="4" height="2"/>\
                            <rect id="XMLID_816_" x="12" y="5" width="4" height="2"/>\
                            <rect id="XMLID_815_" x="6" y="23" width="4" height="2"/>\
                            <rect id="XMLID_814_" x="12" y="23" width="4" height="2"/>\
                            <rect id="XMLID_813_" x="6" y="41" width="4" height="2"/>\
                            <rect id="XMLID_812_" x="12" y="41" width="4" height="2"/>\
                            <path id="XMLID_661_" d="M59,59c-7.2,0-13-5.8-13-13s5.8-13,13-13s13,5.8,13,13S66.2,59,59,59z M59,35.3c-5.9,0-10.7,4.8-10.7,10.7\
                                S53.1,56.7,59,56.7S69.7,51.9,69.7,46S64.9,35.3,59,35.3z"/>\
                        </svg>\
                    ',
                    external: false,
                    description: splunkUtil.sprintf(_("Add or forward data to %s. Afterwards, you may %s.").t(), this.getProductName(), extractFieldsLink)
                });
            }
            if (showExploreDataButton) {
                this.children.exploreData = new ItemView({
                    url: route.exploreData(this.model.application.get('root'), this.model.application.get('locale')),
                    title: _("Explore Data").t(),
                    icon: '\
                        <svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"\
                            width="62px" height="62px" viewBox="0 0 62 62" enable-background="new 0 0 62 62" xml:space="preserve" class="fill-svg">\
                            <g id="XMLID_702_">\
                                <rect id="XMLID_713_" x="46" y="0" width="3" height="2"/>\
                                <rect id="XMLID_712_" x="31" y="0" width="7" height="2"/>\
                                <rect id="XMLID_711_" x="44" y="18" width="7" height="2"/>\
                                <rect id="XMLID_710_" x="41" y="0" width="2" height="2"/>\
                                <rect id="XMLID_709_" x="47" y="6" width="3" height="2"/>\
                                <rect id="XMLID_708_" x="37" y="6" width="7" height="2"/>\
                                <rect id="XMLID_707_" x="31" y="6" width="3" height="2"/>\
                                <rect id="XMLID_706_" x="49" y="12" width="5" height="2"/>\
                                <rect id="XMLID_704_" x="37" y="12" width="3" height="2"/>\
                                <rect id="XMLID_703_" x="43" y="12" width="3" height="2"/>\
                            </g>\
                            <g id="XMLID_686_">\
                                <rect id="XMLID_701_" x="25" y="0" width="3" height="2"/>\
                                <rect id="XMLID_700_" x="8" y="0" width="9" height="2"/>\
                                <rect id="XMLID_699_" x="7" y="18" width="10" height="2"/>\
                                <rect id="XMLID_698_" x="20" y="0" width="2" height="2"/>\
                                <rect id="XMLID_697_" x="26" y="6" width="3" height="2"/>\
                                <rect id="XMLID_696_" x="16" y="6" width="7" height="2"/>\
                                <rect id="XMLID_695_" x="7" y="6" width="6" height="2"/>\
                                <rect id="XMLID_694_" x="10" y="30" width="4" height="2"/>\
                                <rect id="XMLID_693_" x="3" y="30" width="4" height="2"/>\
                                <rect id="XMLID_692_" x="5" y="24" width="8" height="2"/>\
                                <rect id="XMLID_691_" x="0" y="12" width="5" height="2"/>\
                                <rect id="XMLID_690_" x="9" y="12" width="3" height="2"/>\
                                <rect id="XMLID_689_" x="15" y="12" width="3" height="2"/>\
                                <polygon id="XMLID_494_" points="25,12 22,12 21,12 21,14 22,14 25,14 27,14 27,12"/>\
                                <rect id="XMLID_687_" x="10" y="36" width="3" height="2"/>\
                            </g>\
                            <path id="XMLID_639_" d="M57.5,52.6l-10-10C49.7,39.6,51,36,51,32c0-9.9-8.1-18-18-18s-18,8.1-18,18s8.1,18,18,18\
                                c3.4,0,6.6-1,9.4-2.7l10.2,10.2c0.7,0.7,1.6,1,2.5,1c0.9,0,1.8-0.3,2.5-1C58.9,56.2,58.9,53.9,57.5,52.6z M17,32c0-8.8,7.2-16,16-16\
                                s16,7.2,16,16c0,3.8-1.4,7.4-3.6,10.1c-0.1,0.1-0.1,0.1-0.2,0.2c-0.3,0.3-0.5,0.6-0.8,0.9c-0.1,0.1-0.2,0.2-0.3,0.2\
                                c-0.3,0.3-0.6,0.5-0.9,0.8c-0.1,0-0.1,0.1-0.2,0.1C40.4,46.6,36.8,48,33,48C24.2,48,17,40.8,17,32z M56.1,56.1\
                                c-0.6,0.6-1.5,0.6-2.1,0l-9.9-9.9c0.1-0.1,0.2-0.2,0.3-0.2c0.1-0.1,0.2-0.2,0.3-0.3c0.3-0.3,0.6-0.5,0.9-0.8\
                                c0.1-0.1,0.2-0.2,0.4-0.4c0.1-0.1,0.2-0.2,0.4-0.4l9.8,9.8C56.7,54.6,56.7,55.5,56.1,56.1z"/>\
                            <g id="XMLID_499_">\
                                <path id="XMLID_527_" d="M31.5,26h8c0.3,0,0.5-0.2,0.5-0.5v-2c0-0.3-0.2-0.5-0.5-0.5h-8c-0.3,0-0.5,0.2-0.5,0.5v2C31,25.8,31.2,26,31.5,26z"/>\
                                <path id="XMLID_526_" d="M34.5,38h-3c-0.3,0-0.5-0.2-0.5-0.5v-2c0-0.3,0.2-0.5,0.5-0.5h3c0.3,0,0.5,0.2,0.5,0.5v2C35,37.8,34.8,38,34.5,38z"/>\
                                <path id="XMLID_525_" d="M27.5,38h-5c-0.3,0-0.5-0.2-0.5-0.5v-2c0-0.3,0.2-0.5,0.5-0.5h5c0.3,0,0.5,0.2,0.5,0.5v2C28,37.8,27.8,38,27.5,38z"/>\
                                <path id="XMLID_524_" d="M40.5,38h-2c-0.3,0-0.5-0.2-0.5-0.5v-2c0-0.3,0.2-0.5,0.5-0.5h2c0.3,0,0.5,0.2,0.5,0.5v2C41,37.8,40.8,38,40.5,38z"/>\
                                <path id="XMLID_523_" d="M46.5,32h-3c-0.3,0-0.5-0.2-0.5-0.5v-2c0-0.3,0.2-0.5,0.5-0.5h3c0.3,0,0.5,0.2,0.5,0.5v2C47,31.8,46.8,32,46.5,32z"/>\
                                <path id="XMLID_522_" d="M24,23.5v2c0,0.3,0.2,0.5,0.5,0.5h3c0.3,0,0.5-0.2,0.5-0.5v-2c0-0.3-0.2-0.5-0.5-0.5h-3C24.3,23.2,24.2,23.3,24,23.5z"/>\
                                <path id="XMLID_506_" d="M20.3,29.4c-0.1,0.9-0.2,1.1-0.2,2.1c0,0.3,0.2,0.5,0.5,0.5c1.7,0,7.3,0,9,0c0.3,0,0.5-0.2,0.5-0.5v-2c0-0.3-0.2-0.5-0.5-0.5c-1.7,0-7.2,0-8.8,0C20.5,29,20.3,29.2,20.3,29.4z"/>\
                            </g>\
                            <path id="XMLID_498_" d="M39.5,32h-6c-0.3,0-0.5-0.2-0.5-0.5v-2c0-0.3,0.2-0.5,0.5-0.5h6c0.3,0,0.5,0.2,0.5,0.5v2C40,31.8,39.8,32,39.5,32z"/>\
                        </svg>\
                    ',
                    external: false,
                    description: _("Explore data and define how Hunk parses that data.").t()
                });
            }
            if (this.model.user.canViewRemoteApps()) {
                this.children.apps = new ItemView({
                    url: route.manager(this.model.application.get('root'), this.model.application.get('locale'), 'system', 'appsremote'),
                    title: _("Splunk Apps").t(),
                    icon: '\
                        <svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"\
                            width="72px" height="62px" viewBox="0 0 72 62" enable-background="new 0 0 72 62" xml:space="preserve" class="fill-svg">\
                            <g id="XMLID_820_">\
                                <path id="XMLID_985_" d="M54.4,42.8c0,0-0.1,0.1-0.1,0.1C54.3,42.9,54.4,42.8,54.4,42.8z"/>\
                                <path id="XMLID_996_" d="M54.3,42.9c-0.1,0.1-0.1,0.2-0.2,0.2C54.1,43.1,54.2,43,54.3,42.9z"/>\
                                <path id="XMLID_997_" d="M54.1,43.1c-0.1,0.1-0.2,0.2-0.4,0.3C53.8,43.3,54,43.2,54.1,43.1z"/>\
                                <path id="XMLID_998_" d="M54.6,42.3c0,0,0,0.1-0.1,0.1C54.6,42.4,54.6,42.4,54.6,42.3z"/>\
                                <path id="XMLID_999_" d="M53.7,43.4c-0.1,0-0.1,0.1-0.2,0.1C53.6,43.5,53.7,43.5,53.7,43.4z"/>\
                                <path id="XMLID_1090_" d="M54.6,42.5c-0.1,0.1-0.1,0.2-0.2,0.3C54.5,42.7,54.5,42.6,54.6,42.5z"/>\
                                <g id="XMLID_988_">\
                                    <path id="XMLID_993_" d="M68.9,24H55v2h13.9c0.6,0,1.1,0.5,1.1,1.1v11.9c0,0.6-0.5,1.1-1.1,1.1H63v2h5.9c1.7,0,3.1-1.4,3.1-3.1\
                                        V27.1C72,25.4,70.6,24,68.9,24z"/>\
                                </g>\
                                <path id="XMLID_1092_" d="M52.5,43.9C52.4,44,52.2,44,52,44C52.2,44,52.4,44,52.5,43.9z"/>\
                                <path id="XMLID_1093_" d="M53.5,43.5c-0.1,0.1-0.2,0.1-0.3,0.2C53.3,43.7,53.4,43.6,53.5,43.5z"/>\
                                <path id="XMLID_1094_" d="M52.7,43.9c-0.1,0-0.1,0-0.2,0C52.6,43.9,52.7,43.9,52.7,43.9z"/>\
                                <path id="XMLID_1095_" d="M54.6,42.3c0.1-0.1,0.1-0.2,0.2-0.3l0,0C54.8,42.1,54.7,42.2,54.6,42.3z"/>\
                                <path id="XMLID_1096_" d="M53.2,43.7c-0.1,0-0.1,0.1-0.2,0.1C53.1,43.8,53.2,43.7,53.2,43.7z"/>\
                                <path id="XMLID_1097_" d="M53.1,43.8c-0.1,0-0.2,0.1-0.3,0.1C52.8,43.9,52.9,43.8,53.1,43.8z"/>\
                            </g>\
                            <path id="XMLID_991_" d="M25,44v15c0,1.7,1.4,3,3,3H60c1.7,0,3-1.4,3-3V36c0-1.7-1.4-3-3-3h-5v2h5c0.6,0,1,0.5,1,1V59\
                                c0,0.6-0.5,1-1,1H28c-0.6,0-1-0.5-1-1V44H25z"/>\
                            <rect id="XMLID_822_" x="55" y="28" width="15" height="2"/>\
                            <rect id="XMLID_992_" x="55" y="37" width="7" height="2"/>\
                            <path id="XMLID_990_" d="M52,0H3C1.3,0,0,1.4,0,3.1v37.8C0,42.6,1.3,44,3,44h49c1.7,0,3-1.4,3-3.1V3.1C55,1.4,53.7,0,52,0z M53,40.9\
                                c0,0.6-0.4,1.1-1,1.1H3c-0.6,0-1-0.5-1-1.1V3.1C2,2.5,2.4,2,3,2h49c0.6,0,1,0.5,1,1.1V40.9z"/>\
                            <g id="XMLID_983_">\
                                <rect id="XMLID_811_" x="1" y="6" width="53" height="2"/>\
                            </g>\
                        </svg>\
                    ',
                    external: true,
                    description: splunkUtil.sprintf(_("Apps and add-ons extend the capabilities of %s.").t(), this.getProductName())
              });
            }

            if (showDocsButton) {
                this.children.docs = new ItemView({
                    url: route.docHelp(this.model.application.get("root"), this.model.application.get("locale"), "docs.help"),
                    title: _("Splunk Docs").t(),
                    icon: '\
                        <svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"\
                            width="50px" height="62px" viewBox="0 0 50 62" enable-background="new 0 0 50 62" xml:space="preserve" class="fill-svg">\
                        <g id="XMLID_637_">\
                            <path id="XMLID_638_" d="M7.9,50c-0.9,0-2.3,1-2.3,2H47v-2H7.9z"/>\
                        </g>\
                        <g id="XMLID_628_">\
                            <path id="XMLID_633_" d="M7.9,57c-0.9,0-2.3-1-2.3-2H47v2H7.9z"/>\
                        </g>\
                        <path id="XMLID_571_" d="M49,62H8.5C4,62,0.3,58.4,0,54h0V10C0,4.5,4.5,0,10,0h37c1.7,0,3,1.3,3,3v41c0,1.7-1.3,3-3,3H8.5\
                            C4.9,47,2,49.9,2,53.5S4.9,60,8.5,60H49V62z M10,2c-4.4,0-8,3.6-8,8v38c1.5-1.8,3.8-3,6.4-3v0H47c0.6,0,1-0.4,1-1V3c0-0.6-0.4-1-1-1H10z"/>\
                        <g id="XMLID_897_">\
                            <path id="XMLID_896_" d="M13.6,31.2l-1.2-2.4l11.3-5.6v-0.3l-11.3-5.6l1.2-2.4L25,20.5c0.8,0.4,1.3,1.2,1.3,2.1v0.8\
                                c0,0.9-0.5,1.7-1.3,2.1L13.6,31.2z"/>\
                        </g>\
                        <g id="XMLID_895_">\
                            <rect id="XMLID_894_" x="26" y="29" width="13" height="2"/>\
                        </g>\
                        </svg>\
                    ',
                    external: true,
                    description: splunkUtil.sprintf(_("Comprehensive documentation for %s and for all other Splunk products.").t(), this.getProductName())
                });
            }

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
        getProductName: function(){
            if (this.model.user && this.model.user.serverInfo){
                return this.model.user.serverInfo.getProductName();
            }
            return "Splunk";
        },
        render: function() {
            this.$el.html(this.template);
            if (this.children.tours) {
                this.children.tours.render().appendTo(this.$el);
            }
            if (this.children.addData) {
                this.children.addData.render().appendTo(this.$el);
            }
            if (this.children.exploreData) {
                this.children.exploreData.render().appendTo(this.$el);
            }
            if (this.children.apps) {
              this.children.apps.render().appendTo(this.$el);
            }
            if (this.children.docs) {
                this.children.docs.render().appendTo(this.$el);
            }
            return this;
        },
        template: '\
        '
    });
});
