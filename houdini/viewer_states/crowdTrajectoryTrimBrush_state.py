import hou
import viewerstate.utils as su
from choreofx.states import node_parm_utils as pu
from choreofx.states import cursor_intersect as ci
from choreofx.states import sun_state_utils as ssu

reload(ci)
reload(pu)
reload(ssu)

class crowdTrajectoryTrimBrush(object):

    BRUSHOPS = ("slideframe", "resetframe", "startframe", "endframe", "offsetframe", "resetoffsetframe")

    MSG = "LMB+Drag to Change Frame Time.       CTRL+LMB to Reset to Start/End.       SHIFT+LMB on Path to Set End.       SHIFT+MMB on Path to Set Start.       " \
          "CTRL+MMB+Drag to Change Prim Timing Offset.       CTRL+SHIFT+LMB to Reset Prim Timing Offset.       S to make Houdini Point Selection.     Press on Empty Space to Affect Selection"

    def __init__(self, state_name, scene_viewer, parent=None):
        self._parent = parent
        self._node = None
        self._scene_viewer = scene_viewer
        self._geometryTrajHandles = None
        self._geometryTrajPaths = None
        self._stasherTrajPoints = None
        self._sustainedAction = False
        self._pressed = False
        self._isSelectionEvent = False

        self._brushPosition = 0
        self._lastMouseX = 0
        self._lastMouseY = 0
        self._isShift = False

        self._currentPrimU = -1
        self._currentPrim = -1
        self._currentHandle = -1
        self._currentPrimDist = -1
        self._currentPoint = -1

        self._highlighterKnob = ssu.HighlighterKnob(self._scene_viewer)
        self._drawTextGlobalFrame = ssu.TextOnPoints(self._scene_viewer, "globalframe_")
        self._guideBrush = None
        self._guideHda = None


    def log2(self, message):
        #print (message)
        if self._parent != None:
            self._parent.childLog("CGB_Time", message)

    ############################### LIFE CYCLE EVENTS #######################################

    def onEnter(self, kwargs):
        self.log("onEnter")
        self._node = kwargs["node"]

        self._stasherTrajPoints = self._node.node("OUT_STASH_TRAJ_POINTS")
        self._geometryTrajHandles = self._node.node("OUT_HANDLE_PRIMS").geometry()
        self._geometryTrajPaths = self._node.node("IN_Trajectories").geometry()
        self._drawTextGlobalFrame.updateTextPoints(self._geometryTrajHandles, "global_frame")
        self._drawTextGlobalFrame.show(True)

        geobrush = self._node.node("OUT_GUIDE_BRUSH").geometry()
        self._guideBrush = hou.SimpleDrawable(self._scene_viewer, geobrush, "my_guidebrush_TrimBrush")
        self._guideBrush.setDisplayMode(hou.drawableDisplayMode.CurrentViewportMode)
        self._guideBrush.enable(True)

        geoHdaGuides = self._node.node("OUT_GUIDES").geometry()
        if pu.evalNodeParm(self._node, "guideDisplay") == 1:
            self._guideHda = hou.SimpleDrawable(self._scene_viewer, geoHdaGuides, "guidehda_TrimBrush")
            self._guideHda.setDisplayMode(hou.drawableDisplayMode.CurrentViewportMode)
            self._guideHda.enable(True)
            self._guideHda.show(True)

        self.showGuides(True)
        self._scene_viewer.setPromptMessage(self.MSG)

    def onExit(self, kwargs):
        self.showGuides(False)

        if self._guideHda is not None:
            self._guideHda.show(False)
        pass

    def onResume(self, kwargs):
        self.showGuides(True)
        self._scene_viewer.setPromptMessage(self.MSG)
        self._drawTextGlobalFrame.updateTextPoints(self._geometryTrajHandles, "global_frame")
        self._drawTextGlobalFrame.show(True)
        #self.setCursorInViewport(True)

    def onInterrupt(self, kwargs):
        self.showGuides(False)
        #self.setCursorInViewport(False)

    def onDraw(self, kwargs):
        """ This callback is used for rendering the drawables
        """
        handle = kwargs["draw_handle"]
        self._highlighterKnob.draw (handle)
        #self._drawTextGlobalFrame.draw(handle)

    def updateGuideTransform(self, guide):
        xform = hou.hmath.buildTranslate(self._brushPosition)
        self._guideBrush.setTransform(xform)
        #sself._scene_viewer.curViewport().draw()

    def showGuides(self, visible):
        self._guideBrush.show(visible)
        pass

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
        SINGLECLICK = MOUSEDOWN or PICKED
        SHIFT = device.isShiftKey()
        CTRL = device.isCtrlKey()
        LEFT_BUTTON = device.isLeftButton()
        MIDDLE_BUTTON = device.isMiddleButton()
        RIGHT_BUTTON = device.isRightButton()
        MOUSEX = device.mouseX()
        MOUSEY = device.mouseY()

        self._isShift = SHIFT

        if RIGHT_BUTTON:
            return

        (rayOrigin, rayDir) = ui_event.ray()
        self._brushPosition = ci.intersectOriginPlane(rayOrigin, rayDir)

        self._lastMouseX, self._lastMouseY = MOUSEX, MOUSEY


        if not self._sustainedAction:

            self.setBrushPosition(self._brushPosition)
            self.updateGuideTransform(vp)

            isHandle, prim_num, prim_u, snap_pos, pt_num = self.intersectExistingPrims(rayOrigin, rayDir)


            ### Update NodeParm to drive sops
            self.setIsMouseDown((MOUSEDOWN or PICKED))
            pu.setNodeParm(self._node, "isShift", SHIFT)
            pu.setNodeParm(self._node, "isCtrl", CTRL)

            self.setCurrentPrimParms(isHandle, prim_num, pt_num)

            if SINGLECLICK:
                if LEFT_BUTTON:

                    if CTRL and SHIFT:
                        self.opResetOffsetFrame()
                    elif CTRL:
                        self.opResetFrame()
                    elif SHIFT and not isHandle:
                        self.opEndFrame()
                    else:
                        self.opSlideFrame()

                elif MIDDLE_BUTTON:
                    if SHIFT and not isHandle:
                        self.opStartFrame()
                    elif CTRL:
                        self.opOffsetFrame()

        ### If active action update position offsets or end action on mouseup
        if self._sustainedAction:
            self.updateSustainedAction()
            self._drawTextGlobalFrame.updateTextPoints(self._geometryTrajHandles, "global_frame")
            self._drawTextGlobalFrame.show(True)

            if MOUSEUP or PICKED:
                self.endSustainedAction()

        return False


    def startSustainedAction(self, undoname):
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
        #self.setIsMouseUp(True)
        self._sustainedAction = False
        self.finishPress()

    def stampBrushOp(self, undoname):
        self.log("STAMP")
        with hou.undos.group('timing: ' + undoname):
            self.setIsMouseDown(True)
            self.stashEditedPoints()
            self.setIsMouseDown(False)

    def startPress(self, undoname):
        if not self._pressed:
            self._scene_viewer.beginStateUndo("trajtrim: " + undoname)
        self._pressed = True

    def finishPress(self):
        if self._pressed:
            self._scene_viewer.endStateUndo()
        self._pressed = False

    def setCurrentPrimParms(self, isHandle, prim_num, pt_num):
        currentGlobalFrame = -1
        if isHandle:
            self._currentHandle = prim_num
            self._currentPrim = -1
            point = self._geometryTrajHandles.point(prim_num)
            if point is not None:
                if self._geometryTrajHandles.findPointAttrib('primid') is not None:
                    self._currentPrim = point.attribValue("primid")

        else:
            self._currentPrim = prim_num
            self._currentHandle = pt_num

        pu.setNodeParm(self._node, "activePoint", self._currentHandle)
        pu.setNodeParm(self._node, "activePrim", self._currentPrim)
        #pu.setNodeParm(self._node, "currentGlobalFrame", currentGlobalFrame)



    ###################################### OPERATIONS #################################################################


    def opResetFrame(self):
        self.setBrushOp('resetframe')
        self.stampBrushOp('resetframe')

    def opSlideFrame(self):
        self.setBrushOp('slideframe')
        self.startSustainedAction('slideframe')

    def opStartFrame(self):
        self.setBrushOp('startframe')
        self.startSustainedAction('startframe')

    def opEndFrame(self):
        self.setBrushOp('endframe')
        self.startSustainedAction('endframe')

    def opOffsetFrame(self):
        self.setBrushOp('offsetframe')
        self.startSustainedAction('offsetframe')

    def opResetOffsetFrame(self):
        self.setBrushOp('resetoffsetframe')
        self.stampBrushOp('resetoffsetframe')


    ###################################### BRUSH #################################################################

    def stashEditedPoints(self):
        stashPoints = self._stasherTrajPoints.geometry().freeze(True, True)
        pu.setNodeParm(self._node, 'stash_traj_points', stashPoints, True)
        #self.log(self._currentBrushOp)

        #if self._isSelectionEvent:
        #    self.setIsSeluectionEvent(False)
        #    pu.setNodeParm(self._node, 'selectedPointsGroup', "")

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

    def setIsMouseUp(self, state):
        pu.setNodeParm(self._node, 'isMouseUp', state, onlyifchanged=True)

    def setBrushOp(self, opname):
        value = self.BRUSHOPS.index(opname)
        pu.setNodeParm(self._node, 'brush_op', value)

    def setIsSelectionEvent(self, state):
        self._isSelectionEvent = state
        pu.setNodeParm(self._node, 'isSelectionEvent', state)


    def intersectExistingPrims(self, rayOrigin, rayDir):
        # snap_pos = hou.Vector3(0,0,0)
        prim_u = -1
        isHandle = True
        pt_num = -1

        ### First by getting a nearby handle point. If that fails, try get a point on the paths geometry
        prim_num, snap_pos = ci.getNearestHandleToCursor(self._geometryTrajHandles, rayOrigin, rayDir)

        if prim_num < 0 and self._isShift:
            isHandle = False
            prim_num, pt_num, prim_u, snap_pos = ci.getNearestPointToCursor(self._geometryTrajPaths, rayOrigin, rayDir, 0.5)

        if prim_num >= 0:
            self._highlighterKnob.setKnobPosition(snap_pos)
            self._highlighterKnob.show(True)
        else:
            self._highlighterKnob.show(False)
            isHandle = False

        return isHandle, prim_num, prim_u, snap_pos, pt_num

    def onMenuPreOpen(self, kwargs):
        return kwargs

    def onMenuAction(self, kwargs):
        pass

def createViewerStateTemplate():
    """ Mandatory entry point to create and return the viewer state
        template to register. """

    # state_typename = kwargs["type"].definition().sections()["DefaultState"].contents()
    state_typename = "crowdTrajectoryTrimBrush_state"
    state_label = "Crowd Trajectory Trim Brush"
    state_cat = hou.sopNodeTypeCategory()

    template = hou.ViewerStateTemplate(state_typename, state_label, state_cat)
    template.bindFactory(crowdTrajectoryTrimBrush)
    return template