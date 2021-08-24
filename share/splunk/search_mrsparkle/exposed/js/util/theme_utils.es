import { themes as reactUIThemes } from '@splunk/react-ui/themes';
import { themes as reactTimeRangeThemes } from '@splunk/react-time-range/themes';
import { defaultTheme as defaultReactThemeId } from '@splunk/splunk-utils/themes';

const defaultPageTheme = 'light';

export function getCurrentTheme() {
    // eslint-disable-next-line no-underscore-dangle
    return window.__splunk_page_theme__ || defaultPageTheme;
}

export function getXmlEditorTheme() {
    const pageTheme = getCurrentTheme();
    return pageTheme === 'dark' ? 'ace/theme/xml-dark' : 'ace/theme/chrome';
}

export function getSearchEditorTheme() {
    const pageTheme = getCurrentTheme();
    return pageTheme === 'dark' ? 'dark' : 'light';
}

export function getReactUITheme() {
    const themeId = defaultReactThemeId();
    return reactUIThemes[themeId];
}

export function getReactTimeRangeTheme() {
    const themeId = defaultReactThemeId();
    return reactTimeRangeThemes[themeId];
}

export function normalizeToDefaultTheme(theme) {
    if (theme == null || theme === '') {
        return defaultPageTheme;
    }
    return theme;
}

export { defaultReactThemeId };
export { ThemeProvider } from 'styled-components';
