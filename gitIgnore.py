#!/usr/bin/python
import sys
import os
import fnmatch
import re
import copy

def _readGitIgnore(path):
    patterns = []
    filename = os.path.join(path, ".gitignore")
    if (os.path.exists(filename) and not os.path.isdir(filename)):
        f = open(filename, "rb") 
        s = f.read()
        f.close()
        for line in s.splitlines():

            # R3
            # Trailing spaces are ignored unless they are quoted with backslash ("\").
            line = line.strip()

            # R1
            # A blank line matches no files
            # so it can serve as a separator for readability.
            if len(line) == 0:
                continue
            
            # R2
            # A line starting with # serves as a comment.
            # Put a backslash ("\") in front of the first hash
            # for patterns that begin with a hash.
            if line[0] == '#':
                continue
            if len(line) > 1 and line[0] == '\\' and line[1] == '#':
                line = line[1:]
            elif len(line) > 1 and line[0] == '\\' and line[1] == '!':
                line = line[1:]

            patterns.append(line)

    return patterns

def _computePatterns(rawPatterns):
    out = []
    for raw in rawPatterns:
        out.append({
            'pattern': raw,
            'slash': {
                'present': raw.find('/') <> -1,
                'leading': raw[0] == '/',
                'trailing': raw[-1:] == '/',
                'intermediate': re.match(".+\/.+", raw) <> None
            },
            'dstar': {
                'present': raw.find('**') <> -1,
                'leading': raw[0:3] == '**/',
                'trailing': raw[-3:] == '/**',
                'intermediate': re.match(".+\/\*\*\/.+", raw) <> None
            }
        })
    return out

def _matchOnePattern(path, isDir, patterns, dbgLog=False):
    path = path.replace('\\', '/')

    if dbgLog: print "matchOnePattern on ", path

    dbgIdx = 0
    for p in patterns:
        dbgIdx = dbgIdx + 1

        pattern = p['pattern']

        # R4
        # If the pattern ends with a slash,
        # it is removed for the purpose of the following description,
        # but it would only find a match with a directory.
        # In other words, foo/ will match a directory foo and paths underneath it,
        # but will not match a regular file or a symbolic link foo
        # (this is consistent with the way how pathspec works in general in Git).
        if p['slash']['trailing']:
            if isDir:
                tmp = pattern[:-1]
                if dbgLog: print dbgIdx, ":", "R4[", pattern, "] - remove trailing slash, pattern becomes: [", tmp ,"]"
                pattern = tmp
            else:
                continue

        # R5
        # If the pattern does not contain a slash /,
        # Git treats it as a shell glob pattern
        # and checks for a match against the pathname relative
        # to the location of the .gitignore file
        # (relative to the toplevel of the work tree if not from a .gitignore file).
        if not p['slash']['present']:
            if fnmatch.fnmatch(path, pattern):
                if dbgLog: print dbgIdx, ":", "R5[", pattern, "] - match shell glob pattern"
                if dbgLog: print "OK"
                return True
        
        # R6
        # Otherwise, Git treats the pattern as a shell glob:
        #   "*" matches anything except "/",
        #   "?" matches any one character except "/"
        #   and "[]" matches one character in a selected range.
        #7 See fnmatch(3) and the FNM_PATHNAME flag for a more detailed description.
        # -------> i.e. NO propagation
        else:

            # Note at this point there is NO trailing slash (see R4)
            lPattern = pattern
            if dbgLog: print dbgIdx, ":", "R6[", lPattern, "] - slashes detected, switch to pattern to local pattern"

            # R7
            # A leading slash matches the beginning of the pathname.
            # For example, "/*.c" matches "cat-file.c" but not "mozilla-sha1/sha1.c".
            # -------> i.e. NO propagation
            if p['slash']['leading']:
                tmp = lPattern[1:]
                if dbgLog: print dbgIdx, ":", "R7[", lPattern, "] - remove leading slash, local pattern becomes: [", tmp ,"]"
                lPattern = tmp
            # Note at this point there is NO leading slash (see R7), only intermediate

            if not p['dstar']['present']:

                if p['slash']['intermediate']:
                    if isDir:
                        tmp = lPattern.split('/')[0]
                        if dbgLog: print dbgIdx, ":", "R.[", lPattern, "] - intermediate slash on directory, local pattern becomes: [", tmp ,"]"
                        lPattern = tmp
                    else:
                        continue
                # No more slashes at this point

                if fnmatch.fnmatch(path, lPattern):
                    if dbgLog: print dbgIdx, ":", "R6[", lPattern, "] - match shell glob on local pattern"
                    if dbgLog: print "OK"
                    return True

            # R8
            # A leading "**" followed by a slash means match in all directories.
            # For example, "**/foo" matches file or directory "foo" anywhere,
            # the same as pattern "foo".
            if p['dstar']['leading']:
                tmp = pattern[3:]
                if dbgLog: print dbgIdx, ":", "R8[", lPattern, "] - remove leading '**/', local pattern becomes: [", tmp ,"]"
                lPattern = tmp
                if not isDir and fnmatch.fnmatch(path, lPattern):
                    if dbgLog: print dbgIdx, ":", "R8[", lPattern, "] -  match shell glob on local pattern (on file)"
                    if dbgLog: print "OK"
                    return True

            # Note at this point there is NO leading dstar, so we only deals with subfolder

            if isDir:
                tmp = lPattern.split('/')[0]
                if dbgLog: print dbgIdx, ":", "R.[", lPattern, "] - intermediate slash on directory, local pattern becomes: [", tmp ,"]"
                lPattern = tmp
            else:
                continue

            # R9
            # "**/foo/bar" matches file or directory "bar" anywhere that
            # is directly under directory "foo".
            # ---------> like R6 WITH propagation
            # R10
            # A trailing "/**" matches everything inside.
            # For example, "abc/**" matches all files inside directory "abc",
            # relative to the location of the .gitignore file, with infinite depth.
            # -------> i.e. NO propagation
            if lPattern == "**":
                if dbgLog: print dbgIdx, ":", "R9[", lPattern, "] -  double dot match any folder!"
                if dbgLog: print "OK"
                return True
            else:
                if fnmatch.fnmatch(path, lPattern):
                    if dbgLog: print dbgIdx, ":", "R8[", lPattern, "] -  match shell glob on local pattern (on folder)"
                    if dbgLog: print "OK"
                    return True


    if dbgLog: print "NOK"
    return False

def _constructSubPatterns(patterns):
    out = []
    for p in patterns:
        pattern = p['pattern']
        folders = pattern.split('/')

        #R7: No Propagation (except if we continuing a parent rule)
        if p['slash']['leading']:
            folders.pop(1)
            if len(folders) > 0: out.append('/'.join(folders))
            continue

        if not p['dstar']['present']:
            # R6: No Propagation (except if we continuing a parent rule)
            if p['slash']['intermediate']:
                folders.pop(0)
                if len(folders) > 0: out.append('/'.join(folders))
                continue
            #R4, R5: Propagation
            else:
                out.append(pattern)
                continue
        
        #R8, R9: Propagation
        if p['dstar']['leading']:
            out.append(pattern)
            continue
        
        #R10: No Propagation (except if we continuing a parent rule)
        if p['dstar']['trailing']:
            out.append("**/*") # parent rule becomes "Take everything"
            continue

        #R11: No Propagation (except if we continuing a parent rule)
        if not p['dstar']['intermediate']:
            folders.pop(0)
            if len(folders) > 0: out.append('/'.join(folders))

    return out


def getList(path, parentPatterns=[], useGitIgnore=True, dbgLog=False):
    
    if dbgLog:
        print ""
        print "--------------------------"
        print "getList('",path,"')"
        print "--------------------------"

    matches = []
    nomatches = []
    
    # Get Patterns
    patterns = []
    if useGitIgnore:
        tmp = parentPatterns + _readGitIgnore(path)
        if dbgLog:
            print tmp
            print ""
        patterns = _computePatterns(tmp)
    else:
        patterns = _computePatterns(parentPatterns)
    if dbgLog: print str(patterns).replace('True', 'true').replace('False', 'false')

    # Travel on current Folder
    folderContent = os.listdir(path)
    for content in folderContent:
        fullPath = os.path.join(path, content)
        if dbgLog: print ""
        # Folder
        if os.path.isdir(fullPath):
            if _matchOnePattern(content, True, patterns, True):
                if dbgLog: print ' |-> Recursive call to ', fullPath
                subPatterns = _constructSubPatterns(patterns)
                print subPatterns
                return [], []
            #else:
            #    if LOG_DGB: print '(No Match) Recursive call to ', fullPath
        #file
        else:
            if _matchOnePattern(content, False, patterns, False):
                matches.append(fullPath)
            else:
                nomatches.append(fullPath)
    # Return
    return matches, nomatches

def getFolderTree(path):
    out = {}
    matches = ['hi', 'ho']
    for item in os.listdir(path):
        subpath = os.path.join(path, item)
        if os.path.isdir(subpath):
            out[item] = {
                'matches': matches,
                'type': 'folder',
                'content': getFolderTree(subpath)
            }
        else:
            out[item] = {
                'matches': matches,
                'type': 'file'
            }
    return out


def folderTree2List(tree, filters=[], base=""):
    out = []
    for key in tree:
        value = tree[key]
        ok = True
        for filter in filters:
            if not filter:
                continue
            if filter in value[matches]
                continue
            else:
                ok = False
                break
            if filter[0] == '!':
                filter = filter[1:]
                if not (filter in value[matches])
                    continue
            else:
                ok = False
                break
        if not ok:
            continue
        if value[type] = 'folder'):
            out = out + folderTree2List(value, filters, key)
        else:
            out.append(os.path.join(base, key))
        return out

if __name__ == "__main__":
    if (len(sys.argv) <= 1):
        sys.stderr.write("Missing path\n")
        sys.exit(1)
    rootPath = sys.argv[1]
    if (not os.path.exists(rootPath) or not os.path.isdir(rootPath)):
        sys.stderr.write("invalid path\n")
        sys.exit(1)
    print 'Path:', rootPath + '\\'
    if 0:
        matches, nomatches = getList(rootPath, ['.git'], True, True)
        for m in matches: print m
    else:
        tree = getFolderTree(rootPath, True, )

        #for l in sorted(folderTree2List(tree)): print l
