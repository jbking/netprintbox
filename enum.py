# source from http://code.activestate.com/recipes/67107/#c6

import types, exceptions

class EnumException(exceptions.Exception):
    pass

class Enumeration:
    def __init__(self, doc, enumList):
        self.__doc__ = doc
        lookup = { }
        reverseLookup = { }
        uniqueNames = [ ]
        self._uniqueValues = uniqueValues = [ ]
        self._uniqueId = 0
        for x in enumList:
            if type(x) == types.TupleType:
                x, i = x
                if type(x) != types.StringType:
                    raise EnumException, "enum name is not a string: " + x
                if type(i) != types.IntType:
                    raise EnumException, "enum value is not an integer: " + i
                if x in uniqueNames:
                    raise EnumException, "enum name is not unique: " + x
                if i in uniqueValues:
                    raise EnumException, "enum value is not unique for " + x
                uniqueNames.append(x)
                uniqueValues.append(i)
                lookup[x] = i
                reverseLookup[i] = x
                setattr(self, x, i)
        for x in enumList:
            if type(x) != types.TupleType:
                if type(x) != types.StringType:
                    raise EnumException, "enum name is not a string: " + x
                if x in uniqueNames:
                    raise EnumException, "enum name is not unique: " + x
                uniqueNames.append(x)
                i = self.generateUniqueId()
                uniqueValues.append(i)
                lookup[x] = i
                reverseLookup[i] = x
                setattr(self, x, i)
        self.lookup = lookup
        self.reverseLookup = reverseLookup
    def generateUniqueId(self):
        while self._uniqueId in self._uniqueValues:
            self._uniqueId += 1
        n = self._uniqueId
        self._uniqueId += 1
        return n
    def __getattr__(self, attr):
        if not self.lookup.has_key(attr):
            raise AttributeError
        return self.lookup[attr]
    def whatis(self, value):
        return self.reverseLookup[value]

# alias
Enum = Enumeration
