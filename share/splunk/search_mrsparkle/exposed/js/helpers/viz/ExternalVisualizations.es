import $ from 'jquery';
import console from 'util/console';
import route from 'uri/route';
import requirejs from 'requirejs';
import LazyWrappedExternalVisualization from 'views/shared/viz/LazyWrappedExternalVisualization';

export function getAppBuildNumber(vizName, appName, appsLocalCollection) {
    const localApp = appsLocalCollection ?
        appsLocalCollection.find(model => model.entry.get('name') === appName) :
        null;

    if (!localApp) {
        console.warn(`Unable to look up app build number for custom visualization: ${vizName} from app: ${appName}`);
    }

    return localApp ? localApp.getBuild() : null;
}

/**
 * Base path maps to the directory where all of the viz components live. The form is
 * ../../<splunk build number>-<app build number>/app/<app name>/visualizations/<viz name>/
 *
 * @param appBuildNumber
 * @param appName
 * @param vizName
 * @returns {string}
 */
export function getBasePath(appBuildNumber, appName, vizName) {
    const cacheBuster = route.getSplunkVersion() + encodeURIComponent(appBuildNumber ? `-${appBuildNumber}` : '');
    return `../../${cacheBuster}/app/${encodeURIComponent(appName)}/visualizations/${encodeURIComponent(vizName)}/`;
}

export function getAssetPath(appBuildNumber, appName, vizName, fileName) {
    return `${getBasePath(appBuildNumber, appName, vizName)}${fileName}`;
}

export function loadFormatterHtml({ appBuildNumber, appName, vizName }) {
    const dfd = $.Deferred(); // eslint-disable-line new-cap
    const formatterPath = getAssetPath(appBuildNumber, appName, vizName, 'formatter.html');
    requirejs(
        [`contrib/text!${formatterPath}`],
        formatterHtml => dfd.resolve(formatterHtml),
        () => {
            console.debug(`No formatter found for custom visualization ${appName}.${vizName}`);
            dfd.resolve(null);
        },
    );
    return dfd.promise();
}

export function getFactory({ appName, vizName, appBuildNumber }) {
    const jsPath = getAssetPath(appBuildNumber, appName, vizName, 'visualization');
    const cssPath = `css!${getAssetPath(appBuildNumber, appName, vizName, 'visualization.css')}`;

    return LazyWrappedExternalVisualization.extend({
        vizName,
        appName,
        jsPath,
        cssPath,
    });
}
