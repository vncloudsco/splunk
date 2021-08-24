define(
    [
        'jquery',
        'underscore',
        'uri/route',
        'splunk.util'
    ],
    function(
        $,
        _,
        route,
        splunkUtil
    ) {
        /*
         IDs for the 3 different options of background image customization.
         */
        var BACKGROUNDOPTIONS = {
            NO_IMAGE: "none",
            DEFAULT_IMAGE: "default",
            CUSTOM_IMAGE: "custom"
        };

        /*
         IDs for the 3 different options of background image customization.
         */
        var FOOTEROPTIONS = {
            NO_FOOTER: "none",
            DEFAULT_FOOTER: "default",
            CUSTOM_FOOTER: "custom"
        };

        /*
         IDs for the 3 different options of the document title customization.
         */
        var DOCUMENT_TITLE_OPTIONS = {
            NO_SPLUNK_BRANDING: "none",
            DEFAULT_DOCUMENT_TITLE: "default",
            CUSTOM_DOCUMENT_TITLE: "custom"
        };

        /*
         CSS classes applied on the login page body element and the preview element of the login page settings page.
         The DEFAULT_IMG class works for both Enterprise and Light:
         the PCSS file defining the class has conditional to load in base 64 the appropriate background image
         given the product type.
         */
        var BODYCLASS = {
            DEFAULT: "body-default",
            DEFAULT_IMG: "body-default-img"
        };

        var setupBackgroundImage = function(root, locale, build, option, customBgImage) {
            if (option === BACKGROUNDOPTIONS.DEFAULT_IMAGE) {
                $(document.body).addClass(BODYCLASS.DEFAULT_IMG);
            } else if (option === BACKGROUNDOPTIONS.CUSTOM_IMAGE) {
                $(document.body).addClass(BODYCLASS.DEFAULT).css('backgroundImage',
                    "url(" + decodeURIComponent(route.loginPageBackground(root, locale, build, customBgImage)) + ")");
            }
            // else do nothing, the default body CSS class apply the dark background color
        };

        var getFooter = function(option, footerText) {
            if (option === FOOTEROPTIONS.DEFAULT_FOOTER) {
                return splunkUtil.sprintf("&copy; 2005-%s Splunk Inc.", _.escape(new Date().getFullYear()));
            } else if (option === FOOTEROPTIONS.CUSTOM_FOOTER) {
                return footerText;
            } else {
                return "";
            }
        };

        var getDocumentTitle = function(defaultDocumentTitleText, option, customDocumentTitleText) {
            if (option === DOCUMENT_TITLE_OPTIONS.DEFAULT_DOCUMENT_TITLE) {
                // No need to translate Splunk
                return splunkUtil.sprintf("%s %s", defaultDocumentTitleText, " | Splunk");
            } else if (option === DOCUMENT_TITLE_OPTIONS.CUSTOM_DOCUMENT_TITLE) {
                return customDocumentTitleText;
            } else {
                // Default document text should just contain the page title.
                return defaultDocumentTitleText;
            }
        };

        return ({
            BODYCLASS: BODYCLASS,
            BACKGROUNDOPTIONS: BACKGROUNDOPTIONS,
            setupBackgroundImage: setupBackgroundImage,
            getFooter: getFooter,
            getDocumentTitle: getDocumentTitle
        });
    }
);
