import hou
import viewerstate.utils as su
from choreofx.states import node_parm_utils as pu
from choreofx.states import cursor_intersect as ci
from choreofx.states import sun_state_utils as ssu

class CrowdGuideBrush_Timing(object):

    TIMEOPS = ("add", "remove", "slidedist", "slideframe")

    MSG = "LMB to Insert Handle.      LMB+Drag to change frame time.       LMB+SHIFT+Drag to slide along path.      CTRL+LMB to Remove Handle.       \n" \
          "S to make Houdini Point Selection.     Press on Empty Space to Affect Selection"

    def __init__(self, state_name, scene_viewer, parent):
        self._parent = parent
        self._node = None
        self._scene_viewer = scene_viewer
        self._geometryPosPaths = None
        self._geometryTimeHandles = None
        self._stasherTimingPoints = None
        self._sustainedAction = False
        self._pressed = False
        self._isSelectionEvent = False

        self._brushPosition = 0
        self._lastMouseX = 0
        self._lastMouseY = 0

        self._currentPrimU = -1
        self._currentPrim = -1
        self._currentHandle = -1
        self._currentPrimDist = -1
        self._currentPoint = -1

        self._highlighterKnob = ssu.HighlighterKnob(self._scene_viewer)
        self._guideBrush = None
        self._guideAgents = None


    def log(self, message):
        #print (message)
        self._parent.childLog("CGB_Time", message)

    ############################### LIFE CYCLE EVENTS #######################################

    def onEnter(self, kwargs):
        self.log("onEnter")
        self._node = kwargs["node"]

        self._stasherTimingPoints = self._node.node("OUT_TIMING_POINT_EDITED")
        self._geometryPosPaths = self._node.node("OUT_SMOOTH_POSITION_PATHS").geometry()
        self._geometryTimeHandles = self._node.node("OUT_TIMING_HANDLE_GEO").geometry()

        geobrush = self._node.node("OUT_GUIDE_BRUSH").geometry()
        self._guideBrush = hou.SimpleDrawable(self._scene_viewer, geobrush, "my_guidebrush2")
        self._guideBrush.setDisplayMode(hou.drawableDisplayMode.CurrentViewportMode)
        self._guideBrush.enable(True)


        geoGuideAgents = self._node.node("OUT_GUIDE_AGENTS").geometry()
        if pu.evalNodeParm(self._node, "guideDisplay") == 1:
            self._guideAgents = hou.SimpleDrawable(self._scene_viewer, geoGuideAgents, "guideAgents_GuideBrush")
            self._guideAgents.enable(True)
            self._guideAgents.show(True)

        self.showGuides(True)
        self._scene_viewer.setPromptMessage(self.MSG)


    def onExit(self, kwargs):
        self.showGuides(False)
        if self._guideAgents is not None:
            self._guideAgents.enable(False)
            self._guideAgents.show(False)

    def onResume(self, kwargs):
        self.showGuides(True)
        self._scene_viewer.setPromptMessage(self.MSG)
        self.updateVarsFromNodeParms()
        #self.setCursorInViewport(True)

    def onInterrupt(self, kwargs):
        self.showGuides(False)
        #self.setCursorInViewport(False)

    def onDraw(self, kwargs):
        """ This callback is used for rendering the drawables
        """
        handle = kwargs["draw_handle"]
        self._highlighterKnob.draw(handle)

    def updateGuideTransform(self, guide):
        xform = hou.hmath.buildTranslate(self._brushPosition)
        self._guideBrush.setTransform(xform)
        #sself._scene_viewer.curViewport().draw()

    def showGuides(self, visible):
        self._guideBrush.show(visible)

    def showAgentGuides(self, visible):
        self._guideAgents.show(visible)


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
            self.updateGuideTransform(vp)

            isHandle, prim_num, prim_u, snap_pos = self.intersectExistingPrims(rayOrigin, rayDir)
            isPrimInterior = prim_num >= 0 and not isHandle

            ### Update NodeParm to drive sops
            self.setIsMouseDown((MOUSEDOWN or PICKED))
            pu.setNodeParm(self._node, "isShift", SHIFT)
            pu.setNodeParm(self._node, "isCtrl", CTRL)

            self.setCurrentPrimParms(isHandle, prim_num, prim_u)


            if SINGLECLICK:
                if LEFT_BUTTON:
                    if CTRL:
                        self.opRemovePoints()
                    elif SHIFT:
                        self.opSlideDist()
                    else:
                        if prim_num > -1 and not isHandle:
                            self.opAddPoint()
                        else:
                            self.opSlideFrame()

                elif MIDDLE_BUTTON:
                    self.opSlideDist()
                    '''if isHandle:
                        self.opSlideDist()
                    else:
                        self.setIsReadOnlyOp(True)'''



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
        #self.setBrushPosition(self._brushPosition)
        #self.setCursorScreenPos(self._lastMouseX, self._lastMouseY)
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
        with hou.undos.group('timing: ' + undoname):
            self.setIsMouseDown(True)
            self.stashEditedPoints()
            self.setIsMouseDown(False)

    def startPress(self, undoname):
        if not self._pressed:
            self._scene_viewer.beginStateUndo("timing: " + undoname)
        self._pressed = True

    def finishPress(self):
        if self._pressed:
            self._scene_viewer.endStateUndo()
        self._pressed = False

    def readPointPrimDistAttrib(self, geometry, pointnum):
        dist = -1
        if pointnum > -1:
            dist = geometry.point(pointnum).attribValue("primdist")
        return dist

    def setIsReadOnlyOp(self, state):
        pu.setNodeParm(self._node, 'isReadOnlyOp', state)

    def readGlobalFrameAttribAtInsertPoint(self):
        return self._geometryTimeHandles.intAttribValue("current_global_frame")

    def setCurrentPrimParms(self, isHandle, prim_num, prim_u):
        currentGlobalFrame = -1
        if isHandle:
            self._currentHandle = prim_num
            self._currentPrimU = -1
            self._currentPrim = -1
            point = self._geometryTimeHandles.point(prim_num)
            if point is not None:
                if self._geometryTimeHandles.findPointAttrib('primid') is not None:
                    self._currentPrim = point.attribValue("primid")

        else:
            self._currentPrim = prim_num
            self._currentHandle = -1
            self._currentPrimU = prim_u

            if prim_num > -1:
                self._currentPrimDist = self.readPointPrimDistAttrib(self._geometryPosPaths, self._currentPoint)
                currentGlobalFrame = self.readGlobalFrameAttribAtInsertPoint()

        pu.setNodeParm(self._node, "activePoint", self._currentHandle)
        pu.setNodeParm(self._node, "activePrim", self._currentPrim)
        pu.setNodeParm(self._node, "activePrimU", self._currentPrimU)
        pu.setNodeParm(self._node, "currentPrimDist", self._currentPrimDist)
        pu.setNodeParm(self._node, "currentGlobalFrame", currentGlobalFrame)



    ###################################### OPERATIONS #################################################################

    def opAddPoint(self):
        self.setTimeOp('add')
        self.startSustainedAction('add')

    def opRemovePoints(self):
        self.setTimeOp('remove')
        self.startSustainedAction('remove')

    def opSlideDist(self):
        self.setTimeOp('slidedist')
        self.startSustainedAction('slidedist')

    def opSlideFrame(self):
        self.setTimeOp('slideframe')
        self.startSustainedAction('slideframe')


    ###################################### BRUSH #################################################################

    def stashEditedPoints(self):
        stashPoints = self._stasherTimingPoints.geometry().freeze(True, True)
        pu.setNodeParm(self._node, 'stash_timing_points', stashPoints, True)
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

    def setTimeOp(self, opname):
        value = self.TIMEOPS.index(opname)
        pu.setNodeParm(self._node, 'time_op', value)

    def setIsSelectionEvent(self, state):
        self._isSelectionEvent = state
        pu.setNodeParm(self._node, 'isSelectionEvent', state)



    def intersectExistingPrims(self, rayOrigin, rayDir):
        # snap_pos = hou.Vector3(0,0,0)
        prim_u = -1
        isHandle = True
        pt_num = -1

        ### First by getting a nearby handle point. If that fails, try get a point on the paths geometry
        prim_num, snap_pos = ci.getNearestHandleToCursor(self._geometryTimeHandles, rayOrigin, rayDir)

        if prim_num < 0:
            isHandle = False
            prim_num, pt_num, prim_u, snap_pos = ci.getNearestPointToCursor(self._geometryPosPaths, rayOrigin, rayDir, 0.5)
        if prim_num >= 0:
            if pt_num > -1:
                self._currentPoint = pt_num
            #self.log(prim_num)
            #self.log(snap_pos)
            self._highlighterKnob.setKnobPosition(snap_pos)
            self._highlighterKnob.show(True)
        else:
            self._highlighterKnob.show(False)

        return isHandle, prim_num, prim_u, snap_pos

    def onMenuPreOpen(self, kwargs):
        return kwargs

    def onMenuAction(self, kwargs):
        pass