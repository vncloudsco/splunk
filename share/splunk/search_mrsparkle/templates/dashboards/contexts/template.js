<%page args="ctx,runOnSubmit=True,globalSearch=False,cancelOnUnload=False" />\
<%
options = dict()
for key,opt in {'searchEarliestTime':'earliest_time','searchLatestTime':'latest_time','earliest_time':'earliest_time','latest_time':'latest_time', 'earliestTime': 'earliest_time', 'latestTime': 'latest_time', 'sampleRatio': 'sample_ratio'}.items():
    if hasattr(ctx,key):
        options[opt] = getattr(ctx,key)
options['search'] = ctx.normalizedSearchCommand()
if hasattr(ctx, 'statusBuckets'):
    options['status_buckets'] = ctx.statusBuckets
else:
    options['status_buckets'] = 0
if getattr(ctx, 'refresh') is not None:
    options['refresh'] = ctx.refresh
if getattr(ctx, 'refreshType') is not None:
    options['refreshType'] = ctx.refreshType
options['cancelOnUnload'] = cancelOnUnload
%>\

var ${ctx.id} = new SearchManager({
            "id": ${ctx.id|json_decode},
        % if globalSearch:
            "metadata": { "global": true },
        % endif
        % for k,v in options.items():
<%
if k == 'earliest_time' and v is None:
    v = '$earliest$'
if k == 'latest_time' and v is None:
    v = '$latest$'
%>\
            ${k|json_decode}: ${json_decode(v)|n},
        % endfor
            "app": utils.getCurrentApp(),
            "auto_cancel": 90,
            "preview": true,
            "tokenDependencies": {
            % if hasattr(ctx.tokenDeps, 'depends') and hasattr(ctx.tokenDeps, 'rejects'):
                "depends": ${ctx.tokenDeps.depends|json_decode},
                "rejects": ${ctx.tokenDeps.rejects|json_decode}
            % elif hasattr(ctx.tokenDeps, 'depends'):
                "depends": ${ctx.tokenDeps.depends|json_decode}
            % elif hasattr(ctx.tokenDeps, 'rejects'):
                "rejects": ${ctx.tokenDeps.rejects|json_decode}
            % endif
            },
            "runWhenTimeIsUndefined": false
<%
optionsSuffix = ', tokenNamespace: "submitted"' if runOnSubmit else ''
%>\
        }, {tokens: true${optionsSuffix}});
