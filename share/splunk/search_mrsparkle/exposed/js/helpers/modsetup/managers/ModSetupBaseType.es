/**
 * Base class for mod setup types
 */

export default class ModSetupBaseType {

    constructor(bundleId, prefix, isDMCEnabled) {
        this.options = {
            bundleId,
            prefix,
            isDMCEnabled,
        };

        this.models = [];
    }

    static getType() {
        return null;
    }

    /**
     * Return Default values
     */
    // eslint-disable-next-line class-methods-use-this
    getDefaultValues() {
    }

    /**
     * Create models/collections for configuration
     * @param config
     */
    // eslint-disable-next-line class-methods-use-this
    create(/* config */) {
    }

    /**
     * Save models/collections with the updated values
     * @param data
     * @param type
     */
    // eslint-disable-next-line class-methods-use-this
    save(/* data */) {
    }
}
