import hou


def evalNodeParm(node, parmname):
    return node.parm(parmname).eval()


def setNodeParm(node, parmname, value, undo=False, undoname='', onlyifchanged=False):
    if onlyifchanged:
        old = node.parm(parmname).eval()
        if old == value:
            return

    if undo:
        if undoname != '':
            with hou.undos.group('brush: ' + undoname):
               node.parm(parmname).set(value)
        else:
            node.parm(parmname).set(value)
    else:
        with hou.undos.disabler():
            node.parm(parmname).set(value)


def getNodeParmTuple(node, parmname):
    return node.parmTuple(parmname).eval()


def setNodeParmTuple(node, parmname, value, undo=False, onlyifchanged=False):
    if onlyifchanged:
        old = node.parmTuple(parmname).eval()
        if old == value:
            return

    if undo:
        node.parmTuple(parmname).set(value)
    else:
        with hou.undos.disabler():
            node.parmTuple(parmname).set(value)


def incrementNodeParm(node, parmname, increment):
    value = evalNodeParm(node, parmname)
    setNodeParm(node, parmname, value + increment)


def resetNodeParm(node, parmname):
    node.parm(parmname).resetToDefaults()

