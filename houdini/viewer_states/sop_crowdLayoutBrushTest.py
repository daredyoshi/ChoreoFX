import hou
import viewerstate.utils as su
from choreofx.states import node_parm_utils as pu
from choreofx.states import cursor_intersect as ci
from choreofx.states import sun_state_utils as ssu

class CrowdLayoutBrushTest(object):

    LAYOUTMODES = ("add", "modify")

    MSG = "LMB to Insert Agent"

    def __init__(self, state_name, scene_viewer, parent=None):
        self._parent = parent
        self._node = None
        self._scene_viewer = scene_viewer
        self._stasherLayoutPoints = None
        self._sustainedAction = False
        self._pressed = False
        self._isSelectionEvent = False

        self._brushPosition = hou.Vector3(0, 0, 0)
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
        xform = hou.hmath.buildTranslate(self._brushPosition)
        self._guideBrush.setTransform(xform)
        self._scene_viewer.curViewport().draw()
        #sself._scene_viewer.curViewport().draw()

    def showGuides(self, visible):
        #self._guideBrush.enable(visible)
        self._guideBrush.show(visible)
        self.updateGuideTransform()

    def updateVarsFromNodeParms(self):
        ### Update the internal variables from the node parameters
        pass
        #self.handlePosMethod = self.node.parm("posMethod").evalAsInt()

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

        self._lastMouseX, self._lastMouseY = MOUSEX, MOUSEY


        if not self._sustainedAction:

            self.setBrushPosition(self._brushPosition)
            self.updateGuideTransform()


            ### Update NodeParm to drive sops
            self.setIsMouseDown((MOUSEDOWN or PICKED))
            pu.setNodeParm(self._node, "isShift", SHIFT)
            pu.setNodeParm(self._node, "isCtrl", CTRL)


            if SINGLECLICK:
                if LEFT_BUTTON:
                    self.opAddPoints()


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
        self.finishPress()

    def stampBrushOp(self, undoname):
        self.log("STAMP")
        with hou.undos.group('layout: ' + undoname):
            self.setIsMouseDown(True)
            self.stashEditedPoints()
            self.setIsMouseDown(False)

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


    ###################################### OPERATIONS #################################################################

    def opAddPoints(self):
        self.setLayoutMode('add')
        self.startSustainedAction('add')

    ###################################### BRUSH #################################################################

    def stashEditedPoints(self):
        stashPoints = self._stasherLayoutPoints.geometry().freeze(True, True)
        pu.setNodeParm(self._node, 'stash_layout_points', stashPoints, True)
        #self.log(self._currentBrushOp)

        if self._isSelectionEvent:
            self.setIsSelectionEvent(False)
            pu.setNodeParm(self._node, 'selectedPointsGroup', "")

    def setBrushPosition(self, position):
        pu.setNodeParmTuple(self._node, 'brush_position', position)

    def setBrushPositionEnd(self, position):
        pu.setNodeParmTuple(self._node, 'brush_positionEnd', position)


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
        pu.setNodeParm(self._node, 'layout_mode', value)

    def setIsSelectionEvent(self, state):
        self._isSelectionEvent = state
        pu.setNodeParm(self._node, 'isSelectionEvent', state)


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