from builtins import object
class TokenDeps(object):
    def __init__(self, depends, rejects):
        self.depends = depends
        self.rejects = rejects

    def obj(self):
        res = dict()
        if self.depends:
            res['depends'] = self.depends
        if self.rejects:
            res['rejects'] = self.rejects
        return res


def parseTokenDeps(node):
    deps = TokenDeps(
        depends=node.attrib.get("depends", ""),
        rejects=node.attrib.get("rejects", "")
    )
    if _isEmpty(deps):
        return None
    else:
        return deps


def _isEmpty(deps):
    return deps.depends == "" and deps.rejects == ""    
