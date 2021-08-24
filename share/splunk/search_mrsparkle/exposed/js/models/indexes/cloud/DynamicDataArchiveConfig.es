import { defaultFetchInit, handleResponse, handleError } from '@splunk/splunk-utils/fetch';
import { createRESTURL } from '@splunk/splunk-utils/url';
import querystring from 'querystring';
import { normalizeBoolean } from '@splunk/ui-utils/boolean';
import { _ } from '@splunk/ui-utils/i18n';

class DynamicDataArchiveConfig {
    constructor() {
        this.enablerUrl = 'data_archive/sh_archive_manager';
        this.isEnabled = false;
        this.maxRetentionPeriod = 0;
        this.error = {
            hasError: false,
            message: '',
        };
        this.isEnabled = false;
        this.maxRetentionPeriod = 0;
    }

    fetchEnabler() {
        const data = { output_mode: 'json' };
        return fetch(createRESTURL(`${this.enablerUrl}?${querystring.encode(data)}`), {
            ...defaultFetchInit,
            method: 'GET',
        })
        .then(handleResponse(200))
        .catch(handleError(_('Unable to fetch archive enabler.')));
    }

    parseConfigSettings(response) {
        if (response && response.entry[0] && response.entry[0].content) {
            this.isEnabled = normalizeBoolean(
                response.entry[0].content['archiver.enableDataArchive']);
            this.maxRetentionPeriod = Number(
                response.entry[0].content['archiver.maxDataArchiveRetentionPeriod']);
            this.error.hasError = false;
            this.error.message = '';
        }
    }

    getConfigSettings() {
        return this.fetchEnabler()
            .then(response => this.parseConfigSettings(response))
            .catch((response) => {
                this.isEnabled = false;
                this.maxRetentionPeriod = 0;
                this.error.hasError = true;
                this.error.message = response.message;
            });
    }
}

export default DynamicDataArchiveConfig;

