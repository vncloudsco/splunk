/**
 * Loads the Js and css files from the app . If no FormHandler.js is specified in the app then
 * the SPlunnFormHandlerBase is initialized as the handler.
 */

import $ from 'jquery';
import _ from 'underscore';
import SplunkFormHandlerBase from 'api/SplunkFormHandlerBase';
import requirejs from 'requirejs';


const SUPPORTED_EXTENSIONS = ['FormHandler.js', 'FormHandler.css'];

export default class ModHandlerHelper {

    constructor(options) {
        this.supportedExtensions = options.supportedExtensions ||
            SUPPORTED_EXTENSIONS;
        this.handler = null;
    }

    initialize(options) {
        this.bundleId = options.bundle;
        this.basePath = options.path;
        this.supportedExtensions = options.supportedExtensions ||
            this.supportedExtensions;
        return this.loadHandlers();
    }

    /**
     * Creates the js and css file paths to load them using requirejs
     * @returns {Array}
     */
    getFilePaths() {
        const paths = [];
        _.each(this.supportedExtensions, (fileName) => {
            if (fileName.endsWith('.css')) {
                paths.push(`css!${this.basePath}/${this.bundleId}/setup/${fileName}`);
            } else {
                paths.push(`${this.basePath}/${this.bundleId}/setup/${fileName}`);
            }
        });
        return paths;
    }

    /**
     * Loads the Js and css files using requirejs
     * @returns {*}
     */
    loadHandlers() {
        const paths = this.getFilePaths();
        // eslint-disable-next-line new-cap
        const $dererred = $.Deferred();

        requirejs(paths,
            (Dep) => {
                if (Dep) {
                    const instance = new Dep();
                    if (instance instanceof SplunkFormHandlerBase) {
                        this.handler = instance;
                    }
                } else {
                    this.handler = new SplunkFormHandlerBase();
                    $dererred.resolve();
                }
                $dererred.resolve();
            },
            () => {
                if (!this.handler) {
                    this.handler = new SplunkFormHandlerBase();
                    $dererred.resolve();
                }
            });
        return $dererred;
    }
}
