# generate Yuml (both text and png)

from core_parser import HandleModuleLevelDefsAndAttrs

class Klass:
    def __init__(self, name, parent=None, connectsto=None, connectorstyle=None, attrs="", defs=""):
        self.name = name
        self.parent = parent
        self.connectsto = connectsto
        self.connectorstyle = connectorstyle
        self.attrs = attrs
        self.defs = defs

    def MoveAttrsDefsInto(self, klass):
        klass.attrs = self.attrs
        klass.defs = self.defs
        self.attrs = self.defs = ""

    def IsRich(self):
        return (self.attrs <> "" or self.defs <> "")
    
class Yuml:
    # A line of yUML which is one class or two classes in a relationship
    def __init__(self, lhsclass, connector, rhsclass, rhsattrs, rhsdefs):
        if connector == "^":
            self.klass = Klass(rhsclass, parent=Klass(lhsclass), connectorstyle=connector, attrs=rhsattrs, defs=rhsdefs)
        elif connector == "":
            assert lhsclass == ""
            self.klass = Klass(rhsclass, attrs=rhsattrs, defs=rhsdefs)
        else:
            self.klass = Klass(lhsclass, connectsto=Klass(rhsclass, attrs=rhsattrs, defs=rhsdefs), connectorstyle=connector)
            
    def _getrhs(self):
        # if alone then rhs is N/A - interpret as self
        # if have parent then rhs is self
        # if have connector then rhs is connectsto
        if self.klass.connectsto:
            return self.klass.connectsto
        else:
            return self.klass

    def _getlhs(self):
        # if alone then lhs is N/A - interpret as self
        # if have parent then lhs is parent
        # if have connector then lhs is self
        if self.klass.parent:
            return self.klass.parent
        else:
            return self.klass

    rhs = property(_getrhs)
    lhs = property(_getlhs)

    def OneClassAlone(self):
        return self.klass.parent == None and self.klass.connectsto == None
    
    def __str__(self):
        if self.OneClassAlone():
            s = "[%s|%s|%s]" % (self.klass.name, self.klass.attrs, self.klass.defs)
        else:
            l = self.lhs
            r = self.rhs
            s = "[%s|%s|%s]%s[%s|%s|%s]" % (l.name, l.attrs, l.defs, self.klass.connectorstyle, r.name, r.attrs, r.defs)
        s = s.replace("||", "")
        s = s.replace("|]", "]")
        return  s

                 
class PySourceAsYuml(HandleModuleLevelDefsAndAttrs):
    def __init__(self):
        HandleModuleLevelDefsAndAttrs.__init__(self)
        self.result = ''
        self.aclass = None
        self.classentry = None
        self.verbose = 0
        self.yumls = []
        self.yumls_optimised = []

    def GetCompositeClassesForAttr(self, classname, classentry):
        resultlist = []
        for dependencytuple in classentry.classdependencytuples:
            if dependencytuple[0] == classname:
                resultlist.append(dependencytuple[1])
        return resultlist

    def _GetCompositeCreatedClassesFor(self, classname):
        return self.GetCompositeClassesForAttr(classname, self.classentry)

    def FindIndexRichRhsYuml(self, classname):
        index = 0
        for yuml in self.yumls:
            if yuml.rhs.name == classname and yuml.rhs.IsRich():
                return index
            index += 1            
        return None

    def AddYuml(self, lhsclass, connector, rhsclass, rhsattrs="", rhsdefs=""):
        yuml = Yuml(lhsclass, connector, rhsclass, rhsattrs, rhsdefs)
        self.yumls.append(yuml)

    def YumlOptimise(self, debug=False):
        for yuml in self.yumls:
            if not yuml.rhs.IsRich() and not yuml.rhs.name in self.yumls_optimised:
                index = self.FindIndexRichRhsYuml(yuml.rhs.name) 
                if index <> None:
                    self.yumls[index].rhs.MoveAttrsDefsInto(yuml.rhs)
                    self.yumls_optimised.append(yuml.rhs.name)
            if not yuml.lhs.IsRich() and not yuml.lhs.name in self.yumls_optimised:
                index = self.FindIndexRichRhsYuml(yuml.lhs.name)
                if index <> None:
                    self.yumls[index].rhs.MoveAttrsDefsInto(yuml.lhs)
                    self.yumls_optimised.append(yuml.lhs.name)
            
        # Now delete lone lines with one lone class that is not rich,
        # and which is not mentioned anywhere else (if its been optimised then a rich version exists somewhere else, so checking yuml.rhsclass in self.yumls_optimised is the logic)
        newyumls = []
        for yuml in self.yumls:
            if not (yuml.OneClassAlone() and not yuml.klass.IsRich() and yuml.klass.name in self.yumls_optimised):
                newyumls.append(yuml)
        self.yumls = newyumls
        
    def CalcYumls(self, optimise=True):
        self.yumls = []
        self.yumls_optimised = []
        classnames = self.classlist.keys()
        for self.aclass in classnames:
            self.classentry = self.classlist[self.aclass]

            """
            
            #TODO handle modules (but first debug method scanning, which is not under unit test see unittests_parse06.py )
            
            if self.classentry.ismodulenotrealclass:
                continue
                self.result +=  '[%s  (file)]\n' % (self.aclass,)
                if self.modulemethods:
                    self.result += '  ModuleMethods = %s\n' % `self.modulemethods`
                    self.result += "-[note: module/file's methods]"
                continue
            """
            
            attrs = ""
            for attrobj in self.classentry.attrs:
                if attrs:
                    attrs += ";"
                attrs += attrobj.attrname

                # Generate extra yUml lines showing class dependency and composition relationships - generalisation relationship not done here.
                compositescreated = self._GetCompositeCreatedClassesFor(attrobj.attrname)
                for c in compositescreated:
                    if 'many' in attrobj.attrtype:
                        line = "++-"
                        cardinality = "*"
                    else:
                        line = "-.->"
                        cardinality = ""
                    connector = "%s%s%s" % (attrobj.attrname, line, cardinality)
                    
                    self.AddYuml(self.aclass, connector, c)

            defs = ""
            for adef in self.classentry.defs:
                if defs:
                    defs += ";"
                defs += adef + "()"
                
            if self.classentry.classesinheritsfrom:
                parentclass = self.classentry.classesinheritsfrom[0]  #TODO don't throw away all the inherited classes - just grab 0 for now
                self.AddYuml(parentclass, "^", self.aclass, attrs, defs)
            else:
                parentclass = ""
                self.AddYuml("", "", self.aclass, attrs, defs)
        if optimise:
            self.YumlOptimise(debug=False)
        
    def YumlDump(self):
        for yuml in self.yumls:
            self.result += str(yuml) + "\n"
            
    def __str__(self):
        if not self.yumls:
            print "Warning, should call CalcYumls() after .Parse() and before str(p) - repairing..."
            self.CalcYumls()
        self.result = ''
        self.YumlDump()
        return self.result
    
import urllib
import urllib2
import png    # codeproject version, not the "easy_install pypng" version.

def _yuml_write_to_png(yuml, in_stream, out_stream):
    signature = png.read_signature(in_stream)
    out_stream.write(signature)
    
    for chunk in png.all_chunks(in_stream):
        if chunk.chunk_type == 'IEND':
            break
        chunk.write(out_stream)

    itxt_chunk = png.iTXtChunk.create('yuml', yuml)
    itxt_chunk.write(out_stream)

    # write the IEND chunk
    chunk.write(out_stream)

def yuml_create_png(yuml_txt, output_filename):
    #baseUrl = 'http://yuml.me/diagram/scruffy/class/'
    baseUrl = 'http://yuml.me/diagram/dir:lr;scruffy/class/'
    url = baseUrl + urllib.quote(yuml_txt)
    
    original_png = urllib2.urlopen(url)
    output_file = file(output_filename, 'wb')

    _yuml_write_to_png(yuml_txt, original_png, output_file)

    output_file.close()

if __name__ == '__main__':
    y = Yuml('a','->','b', "fielda", "doa;dob")
    print y
    print Yuml('a','^','b', "fielda", "doa;dob")
    
    