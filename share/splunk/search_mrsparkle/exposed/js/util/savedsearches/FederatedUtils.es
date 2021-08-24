const isDFSEnabled = serverInfoModel =>
    serverInfoModel && serverInfoModel.isDFSEnabled();
const hasFSHSearch = userModel => userModel.hasCapability('fsh_search');
const hasFSHManage = userModel => userModel.hasCapability('fsh_manage');

export const canViewFederatedSearches = (userModel, serverInfoModel) =>
    isDFSEnabled(serverInfoModel) && (hasFSHSearch(userModel) || hasFSHManage(userModel));

export const canCreateFederatedSearches = (userModel, serverInfoModel) =>
    isDFSEnabled(serverInfoModel) && (hasFSHSearch(userModel) || hasFSHManage(userModel));

export const canRunFederatedSearches = (userModel, serverInfoModel) =>
    isDFSEnabled(serverInfoModel) && hasFSHSearch(userModel);
