from __future__ import absolute_import
from __future__ import print_function
from builtins import range
import sys
import os

def scrub(bnf):
    privatefields = ['maintainer', 'appears-in', 'note']
    for attrs, val in bnf.items():
        usage = val.get("usage", [""])[0].strip().lower()
        # remove any non-public commands
        if usage != "" and ("public" not in usage or "deprecated" in usage):
            del bnf[attrs]
        # remove private fields
        for p in privatefields:
            if p in val:
                del val[p]
    
if __name__ == '__main__':
    """Notes on imports:
    scrubbnf.py is invoked during the build process.
    Ideally we would import conf with the absolute path like:
        from splunk.mining import conf
    but SPLUNK_HOME has not yet been populated, nor is PYTHONPATH set.
    Fortunately conf.py is in the same directory as scrubbnf.py, so the
    following import line works because the directory containing the script
    is added to the beginning of sys.path and conf does not import anything
    from splunk. If either of these convenient requirements change, we can
    resolve the import issue by adding the proper directories to sys.path,
    starting with __file__ to find the path to this file.
    """
    import conf
    argc = len(sys.argv)
    argv = sys.argv
    if 2 <= argc <= 3:
        filename = argv[1]
        bnf = conf.ConfParser.parse(filename)
        scrub(bnf)
        outtext = conf.ConfParser.toString(bnf)        
        if argc == 3:
            outfilename = argv[2]
            outdir = os.path.split(outfilename)[0]
            if not os.path.isdir(outdir):
                os.makedirs(outdir)
            f = open(outfilename, 'w')
            f.write(outtext)
            f.close()
        else:
            print(outtext)
    else:
        print('Usage:')
        print(argv[0] + " filename [outfilename]")
