import os, tarfile, sys
from optparse import OptionParser

excludes = ""

parser = OptionParser()
parser.add_option("-x", "--exclude", dest="exclude", default="", help="file to exclude")
(opts, args) = parser.parse_args()

excludes = opts.exclude

excludesMap = {}

for i in excludes.split(','):
    excludesMap[i] = i

if len(args) != 2:
    print("Usage: %s <tar file to create> <dir whose contents should be tarred> [options]" % sys.argv[0])
    print("       Creates a tar file of the CONTENTS of a given directory.")
    sys.exit(1)
    
def main():

  destPath  = sys.argv[1]
  targetDir = sys.argv[2]

  # create the new tar file.
  destFile  = tarfile.open(destPath, 'w')
  # for every item INSIDE targetDir (exclude targetDir itself)...
  for dirItem in os.listdir(targetDir):
    if dirItem not in excludesMap:
        # add the directory's item (dir/file/whatever), but give it just the name of the item, not the whole path.
        destFile.add(os.path.join(targetDir, dirItem), dirItem)

if __name__ == "__main__":
  main()
