
import os, tarfile, sys
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-x", "--exclude", dest="exclude", default="", help="file to exclude")
(opts, args) = parser.parse_args()

excludes = opts.exclude

excludesMap = {}

for i in excludes.split(','):
    excludesMap[i] = i

if len(sys.argv) < 2:
    print("Usage: %s <file to untar> [destination path]" % sys.argv[0])
    print("       Untars a file into destination path directory.")
    sys.exit(1)
    
def main():
    fullyQualifiedTarFileName = sys.argv[1]

    #get a tuple which has the directory and filenames split into a tuple.
    t = os.path.split(fullyQualifiedTarFileName)
    tarFileDir = t[0]
    tarFileName = t[1]

    if len(sys.argv) == 3:
        #the user supplied a destination directory to untar my stuff.
        destPath = sys.argv[2]
    else:
        #the user didnot supply a dest folder - dervie it removing the extension after the dot ('.')
        destPath = os.path.join(tarFileDir, tarFileName.rsplit('.',1)[0])
    
    tf = tarfile.open(fullyQualifiedTarFileName, 'r')
    tf.extractall(destPath)
    
if __name__ == "__main__":
  main()
