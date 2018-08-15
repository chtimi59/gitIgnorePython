#!/usr/bin/python
import re
import os
import folderTree
import addRules

def _matchOneRule(path, isDir, ruleset, dbgLog=False):
    path = path.replace('\\', '/')

    if dbgLog: print "matchOnePattern on ", path

    dbgIdx = 0
    for rule in rs.ruleset:
        dbgIdx = dbgIdx + 1

        pattern = rule.pattern

        # R4
        # If the pattern ends with a slash,
        # it is removed for the purpose of the following description,
        # but it would only find a match with a directory.
        # In other words, foo/ will match a directory foo and paths underneath it,
        # but will not match a regular file or a symbolic link foo
        # (this is consistent with the way how pathspec works in general in Git).
        if rule.slash.trail:
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
        if not rule.slash.exist:
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
            if rule.slash.lead:
                tmp = lPattern[1:]
                if dbgLog: print dbgIdx, ":", "R7[", lPattern, "] - remove leading slash, local pattern becomes: [", tmp ,"]"
                lPattern = tmp
            # Note at this point there is NO leading slash (see R7), only intermediate

            if not rule.dstar.exist:

                if rule.slash.inter:
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
            if rule.dstar.lead:
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

def apply(tree):
    __apply(tree, '', tree.first())
def __apply(tree, path, parent):
    print '__apply(', path, ')'
    if parent is None: return None
    for key in tree:
        value = tree[key]
        newpath = os.path.join(path, key)
        print '--', newpath
        for rs in parent.rulesets:
            #computeMatch(value)
            value.matches = ['yo']
        print value

        if value.type == folderTree.FOLDER:
            __apply(value.content, newpath, value)

if __name__ == "__main__":
    tree = folderTree.get('test')
    addRules.addFromFile(tree, '.gitignore')
    apply(tree)
    #print tree
