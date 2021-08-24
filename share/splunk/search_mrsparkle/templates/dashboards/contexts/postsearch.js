<%page args="ctx,runOnSubmit=True" />\
<%
options = dict()
options['search'] = ctx.searchCommand
options['managerid'] = ctx.baseSearchId
%>\
var ${ctx.id} = new PostProcessManager({
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
        % for k,v in options.items():
            ${k|json_decode}: ${json_decode(v)|n},
        % endfor
            "id": ${ctx.id|json_decode}
        }, {tokens: true, tokenNamespace: "submitted"});

