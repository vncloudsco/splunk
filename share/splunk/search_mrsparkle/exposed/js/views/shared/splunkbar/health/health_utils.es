/**
 * Helper functions for health modal and badge.
 */
import _ from 'underscore';
import css from './health_utils.pcssm';

export function getIconName(color, disabled) {
    if (disabled) {
        return 'questionCircle';
    }
    switch (color) {
        case 'red':
            return 'error';
        case 'yellow':
            return 'warning';
        case 'green':
            return 'infoCircle';
        default:
            return 'infoCircle';
    }
}

export function getIconStyle(color, disabled) {
    if (disabled) {
        return css.disabledColor;
    }
    switch (color) {
        case 'red':
            return css.error;
        case 'yellow':
            return css.warning;
        case 'green':
            return css.info;
        default:
            return css.defaultColor;
    }
}

export function getIconAltText(color, disabled) {
    if (disabled) {
        return _('Health: disabled').t();
    }
    switch (color) {
        case 'red':
            return _('Health: red').t();
        case 'yellow':
            return _('Health: yellow').t();
        case 'green':
            return _('Health: green').t();
        default:
            return _('Health: pending').t();
    }
}

export function getCssError() {
    return css.error;
}

export function getCssWarning() {
    return css.warning;
}

export function getCssInfo() {
    return css.info;
}

export function getCssDisabled() {
    return css.disabledColor;
}
