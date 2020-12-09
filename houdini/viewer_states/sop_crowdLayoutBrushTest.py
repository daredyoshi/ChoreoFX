import hou
import viewerstate.utils as su
from choreofx.states import node_parm_utils as pu
from choreofx.states import cursor_intersect as ci
from choreofx.states import sun_state_utils as ssu

class CrowdLayoutBrushTest(object):

    LAYOUTMODES = ("addremove", "modify", "xform")

    ADDREMOVEOPS = ("add", "remove")

    XFORMOPS = ("move", "rotate", "scale")

    MSG = "LMB to Insert Agent"

    def __init__(self, state_name, scene_viewer, parent=None):
        self._parent = parent
        self._node = None
        self._scene_viewer = scene_viewer
        self._stasherLayoutPoints = None
        self._sustainedAction = False
        self._pressed = False
        self._isSelectionEvent = False

        self._currentXformOp = 'move'
        self._currentAddRemoveOp = 'add'
        self._currentLayoutMode = 'addremove'

        self._brushPosition = hou.Vector3(0, 0, 0)
        self._brushSize = 1
        self._lastMouseX = 0
        self._lastMouseY = 0

        self._currentPrim = -1


    #def log(self, message):
    #    #print (message)
    #    self._parent.childLog("CGB_Time", message)

    ############################### LIFE CYCLE EVENTS #######################################

    def onEnter(self, kwargs):
        self.log("onEnter")
        self._node = kwargs["node"]

        self._stasherLayoutPoints = self._node.node("OUT_LAYOUT_POINTS_EDITED")


        geobrush = self._node.node("OUT_LAYOUT_BRUSH").geometry()
        self._guideBrush = hou.SimpleDrawable(self._scene_viewer, geobrush, "my_layoutbrush")
        self._guideBrush.setDisplayMode(hou.drawableDisplayMode.CurrentViewportMode)
        self._guideBrush.enable(True)

        self.showGuides(True)
        self._scene_viewer.setPromptMessage(self.MSG)

        self.updateVarsFromNodeParms()


    def onExit(self, kwargs):
        self.showGuides(False)


    def onResume(self, kwargs):
        self.showGuides(True)
        self._scene_viewer.setPromptMessage(self.MSG)


        geobrush = self._node.node("OUT_LAYOUT_BRUSH").geometry()
        self._guideBrush.setGeometry(geobrush)
        self.updateVarsFromNodeParms()

        #self.setCursorInViewport(True)

    def onInterrupt(self, kwargs):
        self.showGuides(False)
        #self.setCursorInViewport(False)

    def onDraw(self, kwargs):
        """ This callback is used for rendering the drawables
        """
        handle = kwargs["draw_handle"]


    def updateGuideTransform(self):
        pass

        #xform = hou.hmath.buildTranslate(self._brushPosition)
        #self._guideBrush.setTransform(xform)
        #self._scene_viewer.curViewport().draw()
        #sself._scene_viewer.curViewport().draw()

    def showGuides(self, visible):
        #self._guideBrush.enable(visible)
        self._guideBrush.show(visible)
        self.updateGuideTransform()

    def updateVarsFromNodeParms(self):
        ### Update the internal variables from the node parameters

        self._brushSize = pu.evalNodeParm(self._node, "brush_size")
        self._currentAddRemoveOp = self.ADDREMOVEOPS[pu.evalNodeParm(self._node, "addremove_op")]
        self._currentXformOp = self.XFORMOPS[pu.evalNodeParm(self._node, "xform_op")]
        self._currentLayoutMode = self.LAYOUTMODES[pu.evalNodeParm(self._node, "layout_mode")]


    def onSelection(self, kwargs):
        selection = kwargs["selection"]
        self.setIsSelectionEvent(True)

        ### Convert all selection types to Points Or set string to -1 for no selection
        if len(selection.selections()) > 0:
            selection.setGeometryType(hou.geometryType.Points)
            selectionString = selection.mergedSelectionString(empty_string_selects_all=False)
        else:
            selectionString = str(-1)
        pu.setNodeParm(self._node, 'selectedPointsGroup', selectionString, True, 'brush: Change Selection')


        #self.setLayoutMode("xform")
        # Must return True to accept the selection?
        return False


    def onMouseEvent(self, kwargs):
        """ Computes the cursor text position and drawable geometry
        """
        #print 'timing on onMouseEvent'
        ui_event = kwargs["ui_event"]
        device = ui_event.device()
        vp = ui_event.curViewport()

        MOUSEUP = ui_event.reason() == hou.uiEventReason.Changed
        MOUSEDOWN = ui_event.reason() == hou.uiEventReason.Start
        PICKED = ui_event.reason() == hou.uiEventReason.Picked
        MOUSEDRAG = ui_event.reason() == hou.uiEventReason.Active
        MOVED = ui_event.reason() == hou.uiEventReason.Located
        SINGLECLICK = MOUSEDOWN or PICKED
        SHIFT = device.isShiftKey()
        CTRL = device.isCtrlKey()
        LEFT_BUTTON = device.isLeftButton()
        MIDDLE_BUTTON = device.isMiddleButton()
        RIGHT_BUTTON = device.isRightButton()
        MOUSEX = device.mouseX()
        MOUSEY = device.mouseY()

        if RIGHT_BUTTON:
            return

        (rayOrigin, rayDir) = ui_event.ray()
        self._brushPosition = ci.intersectOriginPlane(rayOrigin, rayDir)



        BRUSHACTIVE = self._currentLayoutMode == 'addremove'

        if not self._sustainedAction and SHIFT and BRUSHACTIVE:
            if LEFT_BUTTON:
                self.scaleBrushSize(MOUSEX)
            elif MIDDLE_BUTTON:
                self.incMouseBrushFalloff(MOUSEX)
            else:
                self.rotateBrush(MOUSEX)

            self._lastMouseX, self._lastMouseY = MOUSEX, MOUSEY
            return

        self._lastMouseX, self._lastMouseY = MOUSEX, MOUSEY

        if not self._sustainedAction:

            self.setBrushPosition(self._brushPosition)
            self.updateGuideTransform()

            ### Update NodeParm to drive sops
            #self.setIsMouseDown((MOUSEDOWN or PICKED))
            pu.setNodeParm(self._node, "isShift", SHIFT)
            pu.setNodeParm(self._node, "isCtrl", CTRL)

            if SINGLECLICK:
                if LEFT_BUTTON:
                    if self._currentLayoutMode == 'addremove':

                        if CTRL:
                            self.opRemovePoints()
                        else:
                            self.opAddPoints()

                    elif self._currentLayoutMode == 'xform':

                        if self._currentXformOp == 'move':
                            self.opMovePoints()

                        elif self._currentXformOp == 'rotate':
                            self.opRotatePoints()

                        elif self._currentXformOp == 'scale':
                            self.opScalePoints()

                elif MIDDLE_BUTTON:
                    if not CTRL and not SHIFT:
                        self.incrementPressCount()


        ### If active action update position offsets or end action on mouseup
        if self._sustainedAction:
            self.updateSustainedAction()

            if MOUSEUP or PICKED:
                self.endSustainedAction()

        return False

    def onKeyTransitEvent(self, kwargs):
        pass

    def startSustainedAction(self, undoname):
        self.setIsReadOnlyOp(False)
        self.setIsMouseDown(True)
        self.setBrushPosition(self._brushPosition)
        self.setCursorScreenPos(self._lastMouseX, self._lastMouseY)
        self._sustainedAction = True
        self.startPress(undoname)

    def updateSustainedAction(self):
        self.setBrushPositionEnd(self._brushPosition)
        self.setCursorScreenPosEnd(self._lastMouseX, self._lastMouseY)

    def endSustainedAction(self):
        self.log("SUS_STAMP")
        self.setIsMouseDown(True)
        self.stashEditedPoints()
        self.setIsMouseDown(False)
        self._sustainedAction = False
        self.incrementPressCount()
        self.finishPress()

    def stampBrushOp(self, undoname):
        self.log("STAMP")
        with hou.undos.group('layout: ' + undoname):
            self.setIsMouseDown(True)
            self.stashEditedPoints()
            self.setIsMouseDown(False)
            self.incrementPressCount()

    def startPress(self, undoname):
        if not self._pressed:
            self._scene_viewer.beginStateUndo("layout: " + undoname)
        self._pressed = True

    def finishPress(self):
        if self._pressed:
            self._scene_viewer.endStateUndo()
        self._pressed = False


    def setIsReadOnlyOp(self, state):
        pu.setNodeParm(self._node, 'isReadOnlyOp', state)


    def stashEditedPoints(self):
        stashPoints = self._stasherLayoutPoints.geometry().freeze(True, True)
        pu.setNodeParm(self._node, 'stash_layout_points', stashPoints, True)
        #self.log(self._currentBrushOp)

        if self._isSelectionEvent:
            self.setIsSelectionEvent(False)
            #pu.setNodeParm(self._node, 'selectedPointsGroup', "")


    ###################################### OPERATIONS #################################################################

    def opAddPoints(self):
        self.setAddRemoveOp('add')
        self.startSustainedAction('add')

    def opRemovePoints(self):
        #self.setLayoutMode('addremove')
        self.setAddRemoveOp('remove')
        self.stampBrushOp('remove')

    def opMovePoints(self):
        self.setXformOp('move')
        self.startSustainedAction('move')

    def opRotatePoints(self):
        self.setXformOp('rotate')
        self.startSustainedAction('rotate')

    def opScalePoints(self):
        self.setXformOp('scale')
        self.startSustainedAction('scale')



    ###################################### BRUSH #################################################################


    def setBrushPosition(self, position):
        pu.setNodeParmTuple(self._node, 'brush_position', position)

    def setBrushPositionEnd(self, position):
        pu.setNodeParmTuple(self._node, 'brush_positionEnd', position)


    def scaleBrushSize(self, mouseX):
        # self.log("_scaleBrush")
        newscale = self._brushSize * (1 + self.getMouseDeltaX(mouseX) * 0.01)
        self._brushSize = newscale
        self.setBrushSize(newscale)

    def setBrushSize(self, size):
        size = hou.hmath.clamp(size, 0.05, 10000000)
        self._brushSize = size
        pu.setNodeParm(self._node, 'brush_size', size)

    def incMouseBrushFalloff(self, mouseX):
        value = pu.evalNodeParm(self._node, 'brush_falloff')
        value += self.getMouseDeltaX(mouseX) * -0.01
        value = hou.hmath.clamp(value, 0, 1)
        pu.setNodeParm(self._node, 'brush_falloff', value)

    def rotateBrush(self, mouseX):
        value = pu.evalNodeParm(self._node, 'brush_rot')
        newrot = value + self.getMouseDeltaX(mouseX) * 0.002
        pu.setNodeParm(self._node, 'brush_rot', newrot)


    ###################################### MOUSE AND OTHER #################################################################

    def getMouseDeltaX(self, mouseX):
        delta = mouseX - self._lastMouseX
        self._lastMouseX = mouseX
        return delta

    def setCursorScreenPos(self, mouseX, mouseY):
        pu.setNodeParmTuple(self._node, "cursorScreenPos", (mouseX, mouseY))

    def setCursorScreenPosEnd(self, mouseX, mouseY):
        pu.setNodeParmTuple(self._node, "cursorScreenPosEnd", (mouseX, mouseY))

    def setIsMouseDown(self, state):
        pu.setNodeParm(self._node, 'isMouseDown', state, onlyifchanged=True)

    def setLayoutMode(self, opname):
        value = self.LAYOUTMODES.index(opname)
        self._currentLayoutMode = opname
        pu.setNodeParm(self._node, 'layout_mode', value)

    def setAddRemoveOp(self, opname):
        value = self.ADDREMOVEOPS.index(opname)
        self._currentAddRemoveOp = opname
        pu.setNodeParm(self._node, 'addremove_op', value)

    def setXformOp(self, opname):
        # self.log(opname)
        value = self.XFORMOPS.index(opname)
        self._currentXformOp = opname
        pu.setNodeParm(self._node, 'xform_op', value)



    def incrementPressCount(self):
        self.incrementNodeParm('pressCount', 1)

    def incrementNodeParm(self, parmname, increment):
        value = pu.evalNodeParm(self._node, parmname)
        pu.setNodeParm(self._node,parmname, value+ increment)

    def setIsSelectionEvent(self, state):
        self._isSelectionEvent = state
        pu.setNodeParm(self._node, 'isSelectionEvent', state, True)


    def onMenuPreOpen(self, kwargs):
        return kwargs

    def onMenuAction(self, kwargs):
        pass



def create_menu(state_typename):
    pass


def createViewerStateTemplate():
    """ Mandatory entry point to create and return the viewer state
        template to register. """


    #state_typename = kwargs["type"].definition().sections()["DefaultState"].contents()
    state_typename = "crowdLayoutBrushTest_state"
    state_label = "Crowd Layout Brush Test"
    state_cat = hou.sopNodeTypeCategory()

    template = hou.ViewerStateTemplate(state_typename, state_label, state_cat)
    template.bindFactory(CrowdLayoutBrushTest)
    #template.bindIcon(kwargs["type"].icon())

    #template.bindMenu(create_menu())


    # selector #1
    template.bindGeometrySelector(
        name="selector1",
        prompt="Select Path Points",
        quick_select=True,
        use_existing_selection=True,
        geometry_types=[hou.geometryType.Points],
        auto_start=False,
        allow_other_sops=False
    )

    return template