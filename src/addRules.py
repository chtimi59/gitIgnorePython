#!/usr/bin/python
import re
import os
import folderTree

class _SpecialMarker:
    def __init__(self, pattern, exist, lead, inter, trail):
        self.exist = pattern.find(exist) <> -1
        self.lead = pattern[0:len(lead)] == lead
        self.inter = re.match(inter, pattern) <> None
        self.trail = pattern[-len(trail):] == trail
    def __str__(self):
        s = 'exist:' + str(self.exist)
        s = s + ' lead:' + str(self.lead)
        s = s + ', inter:' + str(self.inter)
        s = s + ', trail:' + str(self.trail)
        return s

# A Rule is
# - pattern: a string (like "**/*") which will be used by "applyRules" module
# - ishidden: if true, they are internally generated, and can be removed
# - slash/dstar: some precomputed helpers to describ the pattern
class Rule:
    def __init__(self, pattern, ishidden = False):
        self.pattern = pattern
        self.ishidden = ishidden
        self.slash = _SpecialMarker(pattern, '/', '/',  '.+\/.+', '/')
        self.dstar = _SpecialMarker(pattern, '**', '**/', '.+\/\*\*\/.+', '/**')
    def __str__(self):
        s = '[' + self.pattern + ']'
        s = s + '\n - ishidden: ' + str(self.ishidden)
        s = s + '\n - slash: ' + str(self.slash) + ')'
        s = s + '\n - dstar: ' + str(self.dstar) + ')'
        return s

# A RuleSet is actually a wrapper on
# a List of Rule
# note: despite of regular Python List
#       append(rule) makes sure that the rule.pattern is unique
class RuleSet:
    def __init__(self, rules = None):
        self.rules = []
        if not rules is None:
            for rule in rules:
                self.append(rule)
    def __iter__(self):
        return self.rules.__iter__()
    def __setitem__(self, i, v):
        self.rules.__setitem__(i, v)
        return self
    def __getitem__(self, i):
        return self.rules.__getitem__(i)
    def __len__(self):
        return len(self.rules)
    def __str__(self):
        s = '['
        coma = ''
        for rule in self.rules:
            s = s + coma 
            if rule.ishidden:
                s = s + '(\'' + rule.pattern + '\')'
            else:
                s = s + '\'' + rule.pattern + '\''
            coma = ', '
        s = s + ']' 
        return s
    def append(self, rule):
        if not isinstance(rule, Rule):
            raise Exception('Rule type excepted !')
        notFound = True
        for idx in range(0, len(self.rules)):
            if self.rules[idx].pattern == rule.pattern:
                notFound = False
                self.rules[idx] = rule
        if notFound: self.rules.append(rule)
        return self
    def remove(self, patternOrRule):
        pattern = patternOrRule
        if isinstance(patternOrRule, Rule):
            pattern = patternOrRule.pattern
        newRules = []
        for rule in self.rules:
            if not rule.pattern == pattern:
                newRules.append(rule)
        self.rules = newRules
        return self
    def loadfromfile(self, filepath):
        self.rules = []
        if (not os.path.exists(filepath) or os.path.isdir(filepath)): return self
        f = open(filepath, "rb") 
        s = f.read()
        f.close()
        for line in s.splitlines():
            line = line.strip()
            if len(line) == 0:
                continue
            if line[0] == '#':
                continue
            if len(line) > 1 and line[0] == '\\' and line[1] == '#':
                line = line[1:]
            elif len(line) > 1 and line[0] == '\\' and line[1] == '!':
                line = line[1:]
            self.append(Rule(line))
        return self

# Add a ruleset in a folderitem
def add(folderitem, name, ruleset):
    if folderitem is None: return
    if ruleset is None: return
    if name  is None: return
    if not isinstance(folderitem, folderTree.FolderItem):
        raise Exception('FolderItem type excepted !')
    if not isinstance(ruleset, RuleSet):
        raise Exception('ruleset type excepted !')
    if len(ruleset) > 0:
        folderitem.rulesets[name] = ruleset

# Add a ruleset in a tree base on filename
# The whole tree will be recursily read to find 'filename' file
def addFromFile(tree, filename = '.gitignore'):
    return __addFromFile(tree, filename, '', None)
def __addFromFile(tree, filename, path, parent):
    for key in tree:
        value = tree[key]
        newpath = os.path.join(path, key)
        if value.type == folderTree.FOLDER:
            __addFromFile(value.content, filename, newpath, value)
        elif value.type == folderTree.FILE:
            if key == filename:
                rs = RuleSet().loadfromfile(newpath)
                add(parent, key, rs)


if __name__ == "__main__":

    r = Rule("abc").slash
    if not (r.exist == False and r.lead == False and r.inter == False and r.trail == False): raise Exception(r)
    r = Rule("/abc").slash
    if not (r.exist == True and r.lead == True and r.inter == False and r.trail == False): raise Exception(r)
    r = Rule("a/b/c").slash
    if not (r.exist == True and r.lead == False and r.inter == True and r.trail == False): raise Exception(r)
    r = Rule("abc/").slash
    if not (r.exist == True and r.lead == False and r.inter == False and r.trail == True): raise Exception(r)
    r = Rule("/a/b/d/c/").slash
    if not (r.exist == True and r.lead == True and r.inter == True and r.trail == True): raise Exception(r)
    r = Rule("abc").dstar
    if not (r.exist == False and r.lead == False and r.inter == False and r.trail == False): raise Exception(r)
    r = Rule("**/abc").dstar
    if not (r.exist == True and r.lead == True and r.inter == False and r.trail == False): raise Exception(r)
    r = Rule("a/**/c").dstar
    if not (r.exist == True and r.lead == False and r.inter == True and r.trail == False): raise Exception(r)
    r = Rule("abc/**").dstar
    if not (r.exist == True and r.lead == False and r.inter == False and r.trail == True): raise Exception(r)
    r = Rule("**/a/**/d/**/**").dstar
    if not (r.exist == True and r.lead == True and r.inter == True and r.trail == True): raise Exception(r)
    
    rs1 = RuleSet()
    if not len(rs1) == 0: raise Exception()
    rs1.append(Rule("*")).append(Rule("abc")).append(Rule("abc"))
    if not len(rs1) == 2: raise Exception()
    rs1.remove(Rule("abc")).remove(Rule("abc"))
    if not len(rs1) == 1: raise Exception()
    rs1.remove("*")
    if not len(rs1) == 0: raise Exception()

    rs2 = RuleSet([Rule(".foo"), Rule("/a/a/b"), Rule("**/*", True)])
    for r in rs2: print r
    print rs2
    if not rs2[2].ishidden: raise Exception()
    rs2.append(Rule("**/*"))
    print rs2
    if rs2[2].ishidden: raise Exception()
    rs2[2] = Rule("**/*", True)
    if not rs2[2].ishidden: raise Exception()
    rs3 = RuleSet([Rule("*"), Rule("abc")])

    tree = folderTree.get('test')
    add(tree.first(), "rs1", rs1) # empty (skipped)
    add(tree.first(), "rs2", rs2)
    add(tree.first(), "rs3", rs3)
    if not len(tree.first().rulesets) == 2 : raise Exception()

    tree = folderTree.get('test')
    addFromFile(tree, '.gitignore')
    rulesets = tree.first().rulesets
    if not len(rulesets) == 1 : raise Exception()
    gitignorers = rulesets['.gitignore']
    print gitignorers
    if not len(gitignorers) == 12 : raise Exception()
    tree.first().rulesets['.gitignore'].remove('f9/**')
    if not len(gitignorers) == 11 : raise Exception(len(gitignorers))
    print tree
    print ""
    print "utests ends with success"
