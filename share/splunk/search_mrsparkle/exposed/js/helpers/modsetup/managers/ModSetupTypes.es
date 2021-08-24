import ModSetupConfSplunkDType from './ModSetupConfType';
import ModSetupPasswordType from './ModSetupPasswordType';
import ModSetupScriptType from './ModSetupScriptType';


const ModSetupTypesConfig = {
    CONF: { name: 'conf', helper: ModSetupConfSplunkDType },
    PASSWORD: { name: 'password', helper: ModSetupPasswordType },
    SCRIPT: { name: 'script', helper: ModSetupScriptType },
};

// PRIVATE

function getConfigForType(type) {
    return ModSetupTypesConfig[type];
}

function getTypes() {
    const MODSETUP_TYPES = {};
    Object.keys(ModSetupTypesConfig).forEach((type) => {
        MODSETUP_TYPES[type] = getConfigForType(type).name;
    });

    return MODSETUP_TYPES;
}

export const TYPES = getTypes();

export function getHelperForType(type, isDMCEnabled, ...args) {
    const HelperClass = ModSetupTypesConfig[type].helper;
    return new HelperClass(...args, isDMCEnabled);
}
