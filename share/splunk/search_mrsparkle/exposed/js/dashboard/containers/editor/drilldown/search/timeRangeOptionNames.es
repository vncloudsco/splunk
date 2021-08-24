// we should use Symbol here because user can provide any value to timeRangeOption.
// But we cannot use Symbol for now because React does not support using Symbol as component key.
// ref: https://github.com/facebook/react/issues/4847
export const EXPLICIT_OPTION = '__splunk__EXPLICIT_TIME_OPTION';
export const TOKEN_OPTION = '__splunk__TOKEN_TIME_OPTION';
export const GLOBAL_OPTION = '__splunk__GLOBAL_OPTION';
