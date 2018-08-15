import os

FILE = 1
FOLDER = 2

# A folder tree is actually a list of BaseItem, each defined by
# - type : file or folder
# - matches : A set of RulesSet name, that succeed
class _BaseItem:
    def __init__(self, type, matches = None):
        self.type = type
        self.matches = {} if matches is None else matches
    def __str__(self):
        if len(self.matches) == 0: return ''
        s = 'matches: ['
        coma = ''
        for key in self.matches:
            s = s + coma + key
            coma = ', '
        s = s + ']'
        return s

# A FileItem is a superset of BaseItem, to describe a file
class FileItem(_BaseItem):
    def __init__(self, matches = None):
        _BaseItem.__init__(self, FILE, matches)

# A FolderItem is a superset of BaseItem, to describe a folder
# - content : Provides a list of BaseItem (which means we get a nested definition of folders)
# - rulesets : A list of ruleset, related to the current Folder and subsequent
class FolderItem(_BaseItem):
    def __init__(self, matches = None, content = None):
        _BaseItem.__init__(self, FOLDER, matches)
        self.content = [] if content is None else content
        self.rulesets = {}
    def __str__(self):
        s = _BaseItem.__str__(self)
        if s: s = s + '\n'
        if len(self.rulesets) > 0:
            s = s + 'rulesets: ['
            coma = ''
            for key in self.rulesets:
                value = self.rulesets[key]
                s = s + coma + '"' + key + '"(' + str(len(value)) + ' rules)'
                coma = ', '
            s = s + ']\n'
        return s

# A Tree is actually a wrapper on
# a Dictionnary of FileItem or FolderItem
# the keys for file or folder basename
class Tree():
    def __init__(self):
        self.items = {}
    def __str__(self):
        s = ''
        keys = self.items.keys()
        keycount = len(keys)
        for i in range(0, keycount):
            key = keys[i]
            value = self.items[key]
            islast = i == keycount-1
            head_mark = '\xc0' if islast else '\xc3'
            cont_mark = ' ' if islast else '\xb3'
            if value.type == FOLDER:
                s = s + head_mark + '\xc4\xc4 "' + key + '/"\n'
            elif value.type == FILE:
                s = s + head_mark + '\xc4\xc4 "' + key + '"\n'
            for csline in str(value).splitlines():
                s = s + cont_mark + '   \xb3 - ' + csline + '\n'
            if value.type == FOLDER:
                for csline in str(value.content).splitlines():
                    s = s + cont_mark + '   ' + csline + '\n'
            if islast:
                s = s + '\n'
        return s
    def __iter__(self):
        return self.items.__iter__()
    def __getitem__(self, i):
        return self.items.__getitem__(i)
    def __setitem__(self, i, v):
        self.items.__setitem__(i, v)
        return self
    def __len__(self):
        return len(self.items)
    def first(self):
        for key in self.items:
            return self.items[key]
        return None

# Returns a new Tree Object based on its content
# - initialMatches : An optional param to prefed .matches (mainly used for test)
def get(path, initialMatches = None):
    initialMatches = [] if initialMatches is None else initialMatches
    out = Tree()
    out[path] = FolderItem(initialMatches, __get(path, initialMatches))
    return out
def __get(path, initialMatches = None):
    initialMatches = [] if initialMatches is None else initialMatches
    out = Tree()
    for item in os.listdir(path):
        subpath = os.path.join(path, item)
        if os.path.isdir(subpath):
            out[item] = FolderItem(initialMatches, __get(subpath, initialMatches))
        else:
            out[item] = FileItem(initialMatches)
    return out

# Convert a dictionary of BaseItem into a list of path (based on filters options)
def __tolist(tree, filters, base):
    out = []
    for key in tree:
        value = tree[key]
        # filters
        ok = True
        for filter in filters:
            if not filter:
                continue
            if filter[0] == '!':
                filter = filter[1:]
                if not (filter in value.matches):
                    continue
            else:
                if filter in value.matches:
                    continue
            ok = False
            break
        if not ok:
            continue
        # append path
        newbase = os.path.join(base, key)
        if value.type == FOLDER:
            out.append(newbase)
            out = out + __tolist(value.content, filters, newbase)
        elif value.type == FILE:
            out.append(newbase)
    return out

# Convert a dictionary of BaseItem into a list of path (based on filters options)
def tolist(tree, filters = None):
    filters = [] if filters is None else filters
    item = tree.first()
    if item:
        return __tolist(item.content, filters, '')
    else:
        return []

#Unitary Tests
if __name__ == "__main__":
    tree = get('test', ['foo', 'bar'])
    if not len(tree) == 1: raise Exception('invalid lenght')
    if not len(tree.first().content) == 15: raise Exception('invalid lenght')
    folders = tolist(tree, ['foo'])
    for l in folders: print l
    print "files count:", len(folders)
    if not len(folders) == 66: raise Exception('files count should be 66')
    print "filter need 'foo'"
    folders = tolist(tree, ['foo'])
    print "files count:", len(folders)
    if not len(folders) == 66: raise Exception('files count should be 66')
    print "filter need 'foo' AND 'bar'"
    folders = tolist(tree, ['foo', 'bar'])
    print "files count:", len(folders)
    if not len(folders) == 66: raise Exception('files count should be 66')
    print "filter need 'foo' AND '!bar'"
    folders = tolist(tree, ['foo', '!bar'])  
    print "files count:", len(folders)
    if not len(folders) == 0: raise Exception('files count should be 0')
    print "filter need 'foo' AND 'hi'"
    folders = tolist(tree, ['foo', 'hi'])  
    print "files count:", len(folders)
    if not len(folders) == 0: raise Exception('files count should be 0')
    print tree
    print ""
    print "utests ends with success"