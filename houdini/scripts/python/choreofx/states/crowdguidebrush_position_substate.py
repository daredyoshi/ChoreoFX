"""
State:          crowdGuideBrush_state
Author:         stephenbester
"""

import hou
import viewerstate.utils as su
#import stateutils
from choreofx.states import node_parm_utils as pu
from choreofx.states import cursor_intersect as ci
from choreofx.states import sun_state_utils as ssu

reload(ci)
reload(pu)
reload(ssu)


class CrowdGuideBrush_Position(object):

    BRUSHTYPES = ("singlepoint", "circlebrush")

    BRUSHMODES = ("addremove", "xform", "reverse", "clone", "join")

    ADDREMOVEOPS = ("add", "insert", "remove")

    XFORMOPS = ("move", "rotate", "scale")


    def __init__(self, state_name, scene_viewer, parent):
        ### if you wanted autocompletion for the parent, need to import it
        #assert(isinstance(parent, CrowdGuideBrush))
        self._parent = parent
        #self._state_name = state_name
        self._scene_viewer = scene_viewer

        # HOUDINI REFERENCES

        self._node = None
        self._geometry = None
        self._geometryHandles = None

        # INTERNAL PARMS

        self._pressed = False
        self._isSelectionEvent = False
        self._currentPoint = 0

        self._lastMouseX = 0
        self._lastMouseY = 0

        self._currentXformOp = ''
        self._lastXformOp = 'move'
        self._stickyXformActive = False

        self._pathMode = 'position'
        self._currentAddRemoveOp = ''
        self._currentBrushMode = ''
        self._currentBrushType = ''
        self._sustainedAction = False

        self._currentPrimU = -1
        self._currentPrim = -1
        self._currentHandle = -1

        self._brushPosition = 0
        self._brushSize = 1

        self._rayOrigin = -1
        self._rayDir = -1

        self._stasherAllPoints = None
        self._textBrushMode = None

        self._guideCursorPoint = ssu.makeGeometryDrawableGroup(self._scene_viewer, "guideGroup_mousePoint")
        self._guideBrush = None


    def log(self, message):
        #print (message)
        self._parent.childLog("CGB_Pos", message)

    ############################### LIFE CYCLE EVENTS #######################################
    def onEnter(self, kwargs):
        """ Called on node bound states when it starts
        """

        self.log("onEnter")
        self._node = kwargs["node"]
        #state_parms = kwargs["state_parms"]

        self._stasherAllPoints = self._node.node("OUT_ALL_POINTS_EDITED")

        self._geometry = self._node.node("OUT_POSITION_HANDLE_PATHS").geometry()
        self._geometryHandles = self._node.node("OUT_POSITION_HANDLE_GEO").geometry()
        self._geometryAgentAnchors = self._node.node("OUT_AGENT_ANCHOR_GEO").geometry()

        geobrush = self._node.node("OUT_GUIDE_BRUSH").geometry()
        self._guideBrush = hou.SimpleDrawable(self._scene_viewer, geobrush, "my_guidebrush")
        self._guideBrush.setDisplayMode(hou.drawableDisplayMode.CurrentViewportMode)
        self._guideBrush.enable(True)
        self.setGuidesVisible(True)

        self._textBrushMode = hou.TextDrawable(self._scene_viewer, 'textBrushMode')
        self._textBrushMode.show(True)

        self.initFromNodeParms()
        self.setCursorInViewport(True)


        self.updatePromptMessage()


    def updatePromptMessage(self):

        if self._currentBrushMode == 'addremove':
            message = "LMB to Add / Insert / Move Handle.        CTRL+LMB to Remove Handle/s.      \n" \
                      "MMB on Empty to Start New Path.       MMB on Path to Extend from End.      " \
                      "MMB on First Point to Extend from Start.   \n" \
                      "S to make Houdini Point Selection."

        elif self._currentBrushMode == 'xform':
            message = "LMB on Path to Move Handle / Single Path.       LMB on Empty to Move selected Points.     \n" \
                      "SHIFT+LMB to Rotate Selected Points.       CTRL+LMB to Scale Selected Points.    \n" \
                      "S to make Houdini Point Selection."

        elif self._currentBrushMode == 'reverse':
            message = "LMB on path to Reverse Single Path.       LMB on empty to Reverse Selected Points.       " \

        elif self._currentBrushMode == 'clone':
            message = "LMB+Drag on path to Clone Single Path.       LMB+Drag on empty to Clone Selected Prims.       " \

        elif self._currentBrushMode == 'join':
            message = "LMB+Drag on Empty to Join Selected Prims.     *WIP*"
        else:
            message = ''


        self._scene_viewer.setPromptMessage(message)



    def initFromNodeParms(self):
        self._brushSize = pu.evalNodeParm(self._node, "brush_size")
        self._currentAddRemoveOp = self.ADDREMOVEOPS[pu.evalNodeParm(self._node, "addremove_op")]
        self._currentXformOp = self.XFORMOPS[pu.evalNodeParm(self._node, "xform_op")]
        self._currentBrushMode = self.BRUSHMODES[pu.evalNodeParm(self._node, "brush_mode")]
        self._currentBrushType = self.BRUSHTYPES[pu.evalNodeParm(self._node, "brush_type")]
        pass
        #self.setBrushMode(self.BRUSHMODES[pu.evalNodeParm(self._node, 'brush_mode')])

    def onExit(self, kwargs):
        """ Called when the state terminates
        """
        self.showGuides(False)
        pass
        #state_parms = kwargs["state_parms"]

    def onInterrupt(self, kwargs):
        """ Called when the state is interrupted e.g when the mouse moves outside the viewport
        """
        self.setCursorInViewport(False)
        self.showGuides(False)

    def onResume(self, kwargs):
        """ Called when an interrupted state resumes
        """
        self.showGuides(True)

        # Init the settings parms as they may have changed
        self.initFromNodeParms()
        self.setCursorInViewport(True)
        #self.log("Resume")

        self.updatePromptMessage()

    def onDraw(self, kwargs):
        """ This callback is used for rendering the drawables
        """
        handle = kwargs["draw_handle"]
        self._guideCursorPoint.draw(handle)

    def showGuides(self, visible):
        self._guideBrush.show(visible)

    def setGuidesVisible(self, visibility):
        """ Display or hide drawables.
        """
        self._guideCursorPoint.show(visibility)

    def updateGuideTransform(self, viewport):
        xform = self.getBrushSurfaceXform()
        self.setBrushXform(xform)
        self._scene_viewer.curViewport().draw()

    def setBrushXform(self, xform):
        self._guideBrush.setTransform(xform)

    def getBrushSurfaceXform(self):
        ### Builds an xform for the guidegeo using brush size and brush position
        xform = hou.hmath.buildTranslate(self._brushPosition)
        '''
        if self._currentBrushType == 'circlebrush':
            m = hou.hmath.buildScale(hou.Vector3(1, 1, 1) * self._brushSize)
            xform = m * xform
        '''
        return xform

    def highlightPosition(self, position):
        ### Display a pystate drawable at a point position
        new_geo = hou.Geometry()
        point = new_geo.createPoint()
        point.setPosition(position)

        # update the drawable
        self._guideCursorPoint.setGeometry(new_geo)
        self.setGuidesVisible(True)


    ###################################### SELECTION EVENTS ###########################################################
    def onStopSelection(self, kwargs):
        #selector_name = kwargs["name"]
        pass
        #self.log(selector_name + " has stopped")

    def onSelection(self, kwargs):
        """ Called when a selector has selected something
        """
        selection = kwargs["selection"]
        sel_name = kwargs["name"]
        #self.log(sel_name)

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

    def onStartSelection(self, kwargs):
        pass
        #selector_name = kwargs["name"]
        #self.log(selector_name + " has started")


    ################################## DEVICE EVENTS ##################################################################
    def onMouseEvent(self, kwargs):

        ui_event = kwargs["ui_event"]
        device = ui_event.device()
        vp = ui_event.curViewport()

        #self.log(ui_event.reason())

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
        #self.log("LEFT_BUTTON", LEFT_BUTTON)
        #self.log("MIDDLE_BUTTON", MIDDLE_BUTTON)

        MOUSEX = device.mouseX()
        MOUSEY = device.mouseY()

        BRUSHACTIVE = self._currentBrushMode == 'xform' and self._currentBrushType == 'circlebrush'

        (rayOrigin, rayDir) = ui_event.ray()
        self._rayOrigin = rayOrigin
        self._rayDir = rayDir
        self._brushPosition = ci.intersectOriginPlane(rayOrigin, rayDir)

        if RIGHT_BUTTON:
            return

        if not self._sustainedAction and SHIFT and BRUSHACTIVE:
            if LEFT_BUTTON:
                self.scaleBrushSize(MOUSEX)
            elif MIDDLE_BUTTON:
                self.incMouseBrushFalloff(MOUSEX)
            self._lastMouseX, self._lastMouseY = MOUSEX, MOUSEY
            return

        self._lastMouseX, self._lastMouseY = MOUSEX, MOUSEY

        if not self._sustainedAction:

            self.setBrushPosition(self._brushPosition)
            self.updateGuideTransform(vp)

            ### Don't do any snapping if we are in xform mode with circlebrush active
            isAgentAnchor = 0
            if BRUSHACTIVE:
                isPrimInterior, isHandle, prim_num, prim_u, snap_pos = False, False, -1, -1, (0,0,0)
            else:
                
                isAgentAnchor, isHandle, prim_num, prim_u, snap_pos = self.intersectExistingPrims(rayOrigin, rayDir)
                isPrimInterior = prim_num >= 0 and not isHandle

            ### Update NodeParm to drive sops
            self.setIsMouseDown((MOUSEDOWN or PICKED))
            pu.setNodeParm(self._node, "isShift", SHIFT, onlyifchanged=True)
            pu.setNodeParm(self._node, "isCtrl", CTRL, onlyifchanged=True)

            if isHandle or isAgentAnchor:
                self._brushPosition = snap_pos
                self.setBrushPosition(self._brushPosition)

            #if isHandle or isPrimInterior:
            self.setCurrentPrimParms(isHandle, prim_num, prim_u)

            self.setIsReadOnlyOp(False)


            if SINGLECLICK:
                if LEFT_BUTTON:
                    if self._currentBrushMode == 'addremove':

                        if CTRL:
                            if self._currentBrushMode == 'addremove':
                                if isHandle:
                                    self.opRemoveHandle()
                                else:
                                    self.opRemovePoints()
                        else:
                            if isPrimInterior:
                                self.opInsertPoint()
                            elif isHandle:
                                self.opMoveHandle()
                            else:
                                self.opAddPoint()

                    elif self._currentBrushMode == 'xform':

                        if self._currentXformOp == 'move':
                            if isHandle:
                                self.opMoveHandle()
                            else:
                                self.opMovePoints()

                        elif self._currentXformOp == 'rotate':
                            self.opRotatePoints()

                        elif self._currentXformOp == 'scale':
                            self.opScalePoints()

                    elif self._currentBrushMode == 'reverse':
                        self.opReversePrims()

                    elif self._currentBrushMode == 'clone':
                        self.opClonePrims()

                    elif self._currentBrushMode == 'join':
                        self.opJoinPrims()


                elif MIDDLE_BUTTON:
                    self.setIsReadOnlyOp(True)
                    if self._currentBrushMode == 'addremove':

                        if isHandle or isPrimInterior:
                            self.setActiveTipPoint(prim_num, isHandle, True)
                        else:
                            self.setActiveTipPoint(-1, False, False)


            ### Else not pressing, just holding keys
            else:
                if SHIFT:
                    pass

        if self._sustainedAction:
            self.updateSustainedAction()

            if MOUSEUP or PICKED:
                self.endSustainedAction()

        return False


    def onKeyTransitEvent(self, kwargs):
        """ Called for processing a transitory key event
        """
        ui_event = kwargs["ui_event"]
        SHIFT = ui_event.device().isShiftKey()
        CTRL = ui_event.device().isCtrlKey()
        KEYDOWN = ui_event.device().isKeyDown()
        KEYUP = ui_event.device().isKeyUp()

        if self._currentBrushMode == 'xform':
            if KEYDOWN:
                if SHIFT:
                    self.startXformStickyKey('rotate')
                elif CTRL:
                    self.startXformStickyKey('scale')
            elif KEYUP:
                self.endXformStickyKey()

        #self.log('key', ui_event.device().keyString())

        # return True to consume the key transition
        #if ui_event.device().isKeyDown():
        #    return True

        return False


    def onMouseWheelEvent(self, kwargs):
        """ Process a mouse wheel event
        """
        ui_event = kwargs["ui_event"]
        #self.log("reason:", ui_event.reason())

        device = kwargs["ui_event"].device()
        scroll = device.mouseWheel()

        SHIFT = device.isShiftKey()
        CTRL = device.isCtrlKey()

        return False

    ###################################### OTHER FUNCTIONS #################################################################


    def startSustainedAction(self, undoname):
        self.setBrushPosition(self._brushPosition)
        self.setCursorScreenPos(self._lastMouseX, self._lastMouseY)
        self._sustainedAction = True
        self.startPress(undoname)

    def updateSustainedAction(self):
        #self.setBrushPosition(self._brushPosition)
        #self.setCursorScreenPos(self._lastMouseX, self._lastMouseY)

        #isAgentAnchor, isHandle, prim_num, prim_u, snap_pos = self.intersectExistingPrims(self._rayOrigin, self._rayDir)
        prim_num, snap_pos = ci.getNearestHandleToCursor(self._geometryAgentAnchors, self._rayOrigin, self._rayDir)
        if prim_num >-1:
            pu.setNodeParm(self._node, "snapPoint", prim_num)
            self._brushPosition = snap_pos
        else:
            pu.setNodeParm(self._node, "snapPoint", -1)

        self.setBrushPositionEnd(self._brushPosition)
        self.setCursorScreenPosEnd(self._lastMouseX, self._lastMouseY)

    def endSustainedAction(self):
        self.log("SUS_STAMP")
        self.setIsMouseDown(True)
        self.stashEditedPoints()
        self.setIsMouseDown(False)
        if self._currentBrushMode == 'addremove':
            self.updateCurrentPrimParmsFromGeometry()
        self._sustainedAction = False
        self.finishPress()
        #self.setBrushOp('none')


    def stampBrushOp(self, undoname):
        self.log("STAMP")
        with hou.undos.group('brush: ' + undoname):
            self.setIsMouseDown(True)
            self.stashEditedPoints()
            self.setIsMouseDown(False)
            self.updateCurrentPrimParmsFromGeometry()


    def startXformStickyKey(self, xformop):
        if not self._stickyXformActive:
            self._lastXformOp = self._currentXformOp
            self.setXformOp(xformop)
            self._stickyXformActive = True

    def endXformStickyKey(self):
        self.setXformOp(self._lastXformOp)
        self._stickyXformActive = False

    def startPress(self, undoname):
        # Start Undo State
        if not self._pressed:
            self._scene_viewer.beginStateUndo("brush: " + undoname)
        self._pressed = True

    def finishPress(self):
        # End Undo State
        if self._pressed:
            self._scene_viewer.endStateUndo()
        self._pressed = False


    def readGeoDetailAttrib(self, geometry, attribname):
        return geometry.intAttribValue(attribname)

    def readGeoPrimAttrib(self, geometry, attribname, primnum):
        return geometry.prim(primnum).intAttribValue(attribname)


    def setCurrentPrimParms(self, isHandle, prim_num, prim_u):
        if isHandle:
            self._currentHandle = prim_num
            self._currentPrimU = -1
            #self.log(isHandle)
            #self.log(prim_num)
            self._currentPrim = -1
            point = self._geometry.point(prim_num)
            if point is not None:
                pointprim = point.prims()
                if len(pointprim) > 0:
                    self._currentPrim = pointprim[0].number()

        else:
            self._currentPrim = prim_num
            self._currentHandle = -1
            self._currentPrimU = prim_u

        pu.setNodeParm(self._node, "activePoint", self._currentHandle, onlyifchanged=True)
        pu.setNodeParm(self._node, "activePrim", self._currentPrim, onlyifchanged=True)
        pu.setNodeParm(self._node, "activePrimU", self._currentPrimU, onlyifchanged=True)


    def updateCurrentPrimParmsFromGeometry(self):
        activeTipPoint = self.readGeoDetailAttrib(self._geometry, "_lastActiveTipPoint")
        #if self._curre
        self.setActiveTipPoint(activeTipPoint, False, False)
        pu.setNodeParm(self._node, "activePoint", self._currentHandle)
        self.setCurrentPrimParms(False, -1, -1)

    def setActiveTipPoint(self, pointnum, ishandle, readfromprim):
        activeTip = pointnum

        if readfromprim:
            firstPoint = self.readGeoPrimAttrib(self._geometry, "_firstPoint", self._currentPrim)
            lastPoint = self.readGeoPrimAttrib(self._geometry, "_lastPoint", self._currentPrim)

            if ishandle and pointnum == firstPoint:
                activeTip = firstPoint
            else:
                activeTip = lastPoint

        pu.setNodeParm(self._node, "activeTipPoint", activeTip, True, "brush: Set Tip Point")


    def intersectExistingPrims(self, rayOrigin, rayDir):
        # snap_pos = hou.Vector3(0,0,0)
        prim_u = -1
        isHandle = True
        isAgentAnchor = True

        ### First try get a nearby handle point.
        prim_num, snap_pos = ci.getNearestHandleToCursor(self._geometryHandles, rayOrigin, rayDir)
        if prim_num < 0:
            isHandle = False
            ### Else try get an agent anchor point.
            prim_num, snap_pos = ci.getNearestHandleToCursor(self._geometryAgentAnchors, rayOrigin, rayDir)
        else:
            isAgentAnchor = False

        ### If still no point, try get a point on the paths geometry
        if prim_num < 0:
            isAgentAnchor = False
            prim_num, snap_pos, normal, prim_u = ci.intersectCurves(self._geometry, rayOrigin, rayDir, 0.5)

        if prim_num >= 0:
            self.highlightPosition(snap_pos)
        else:
            self.setGuidesVisible(False)

        if isAgentAnchor:
            prim_num = -1

        return isAgentAnchor, isHandle, prim_num, prim_u, snap_pos


    ###################################### OPERATIONS #################################################################


    def opAddPoint(self):
        self.setBrushMode('addremove')
        self.setAddRemoveOp('add')
        #self.setBrushOp('add')
        self.startSustainedAction('add')

    def opInsertPoint(self):
        #self.setBrushOp('insert')
        self.setBrushMode('addremove')
        self.setAddRemoveOp('insert')
        self.startSustainedAction('insert')

    def opMovePoints(self):
        #self.setBrushOp('move')
        self.setXformOp('move')
        self.startSustainedAction('move')

    def opMoveHandle(self):
        #self.setBrushOp('move')
        self.setXformOp('move')
        self.startSustainedAction('move')
        #self.setIsSelectionEvent(True)
        #pu.setNodeParm(self._node, 'selectedPointsGroup', str(self._currentHandle))

    def opRotatePoints(self):
        self.setXformOp('rotate')
        #self.setBrushOp("rotate")
        self.startSustainedAction('rotate')

    def opScalePoints(self):
        self.setXformOp('scale')
        #self.setBrushOp("scale")
        self.startSustainedAction('scale')

    def opReversePrims(self):
        self.setBrushMode('reverse')
        #self.setBrushOp('reverse')
        self.stampBrushOp('reverse')

    def opRemovePoints(self):
        #self.setBrushOp('remove')
        self.setBrushMode('addremove')
        self.setAddRemoveOp('remove')
        self.stampBrushOp('remove')

    def opRemoveHandle(self):
        #self.setBrushOp('remove')
        self.setBrushMode('addremove')
        self.setAddRemoveOp('remove')
        self.setIsSelectionEvent(True)
        pu.setNodeParm(self._node, 'selectedPointsGroup', str(self._currentHandle))
        self.stampBrushOp('remove')

    def opClonePrims(self):
        self.setBrushMode('clone')
        #self.setBrushOp("clone")
        self.startSustainedAction('clone')

    def opJoinPrims(self):
        self.setBrushMode('join')
        #self.setBrushOp("clone")
        self.startSustainedAction('join')

    def opLockPoints(self):
        pu.setNodeParm(self._node, "isLockMode", True)
        pu.setNodeParm(self._node, "lock_op", 0)
        self.stampBrushOp('lock')
        pu.setNodeParm(self._node, "isLockMode", False)

    def opUnlockPoints(self):
        pu.setNodeParm(self._node, "isLockMode", True)
        pu.setNodeParm(self._node, "lock_op", 1)
        self.stampBrushOp('unlock')
        self.log('unlock')
        pu.setNodeParm(self._node, "isLockMode", False)

    ###################################### BRUSH #################################################################

    def stashEditedPoints(self):

        if pu.evalNodeParm(self._node, 'autoslideDist') == True:
            self._parent.timingStashEditedPoints()

        stashPoints = self._stasherAllPoints.geometry().freeze(True, True)
        pu.setNodeParm(self._node, 'stash_all_points', stashPoints, True)
        #self.log(self._currentBrushOp)

        if self._isSelectionEvent:
            self.setIsSelectionEvent(False)
            pu.setNodeParm(self._node, 'selectedPointsGroup', "")

    def clearStash(self):
        pu.resetNodeParm(self._node, 'stash_all_points')

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

    def setCursorInViewport(self, state):
        pu.setNodeParm(self._node, 'isCursorInViewport', state)

    def setAddRemoveOp(self, opname):
        value = self.ADDREMOVEOPS.index(opname)
        self._currentAddRemoveOp = opname
        pu.setNodeParm(self._node, 'addremove_op', value)

    def setXformOp(self, opname):
        #self.log(opname)
        value = self.XFORMOPS.index(opname)
        self._currentXformOp = opname
        pu.setNodeParm(self._node, 'xform_op', value)


    def setBrushMode(self, modename):
        #self.log(modename)
        old = self._currentBrushMode
        self._currentBrushMode = modename
        pu.setNodeParm(self._node, 'brush_mode', self._currentBrushMode)
        self.updatePromptMessage()

    def setBrushType(self, typename):
        #self.log(typename)
        value = self.BRUSHTYPES.index(typename)
        self._currentBrushType = typename
        pu.setNodeParm(self._node, 'brush_type', value)
        self.updateGuideTransform(self._scene_viewer)


    ###################################### MOUSE AND OTHER #################################################################

    def getMouseDeltaX(self, mouseX):
        delta = mouseX - self._lastMouseX
        self._lastMouseX = mouseX
        return delta

    def getMouseDeltaY(self, mouseY):
        delta = mouseY - self._lastMouseY
        self._lastMouseY = mouseY
        return delta

    def setCursorScreenPos(self, mouseX, mouseY):
        pu.setNodeParmTuple(self._node, "cursorScreenPos", (mouseX, mouseY))

    def setCursorScreenPosEnd(self, mouseX, mouseY):
        pu.setNodeParmTuple(self._node, "cursorScreenPosEnd", (mouseX, mouseY))

    def setIsMouseDown(self, state):
        pu.setNodeParm(self._node, 'isMouseDown', state, onlyifchanged=True)

    def setIsReadOnlyOp(self, state):
        pu.setNodeParm(self._node, 'isReadOnlyOp', state)

    def setIsSelectionEvent(self, state):
        self._isSelectionEvent = state
        pu.setNodeParm(self._node, 'isSelectionEvent', state)

    ###################################### STATE MENU ACTIONS #################################################################

    def onMenuPreOpen(self, kwargs):

        ### Set all the values of the menu items from node parms or internal vars.
        menu_id = kwargs['menu']
        node = kwargs['node']
        menu_states = kwargs['menu_states']
        menu_item_states = kwargs['menu_item_states']

        ### Radio menus come through as their own menu id. Set to string values
        if menu_id == 'radio_brushMode':
            menu_states['value'] = self._currentBrushMode

        elif menu_id == 'radio_xformOp':
            menu_states['value'] = self._currentXformOp

        elif menu_id == 'radio_brushType':
            menu_states['value'] = self._currentBrushType

        ### other items on the base level have the base menu name id
        elif menu_id == 'crowdGuideBrush_menu':
            menu_item_states['toggle_selectAllPrimPoints']['value'] = pu.evalNodeParm(self._node, 'selectAllPrimPoints')
            menu_item_states['toggle_affectAhead']['value'] = pu.evalNodeParm(self._node, 'affectAhead')
            menu_item_states['toggle_affectBehind']['value'] = pu.evalNodeParm(self._node, 'affectBehind')

        return kwargs


    def onMenuAction(self, kwargs):
        ### Define what to do when an item in the menu is pressed.
        menu_item = kwargs['menu_item']
        node = kwargs['node']

        ### Getting the dict entry of a radiogroup returns its string value
        #self.log(kwargs['radio_xformOp'])
        self.log(menu_item)
        if kwargs["menu_item"] == "radio_brushMode":
            self.setBrushMode(kwargs['radio_brushMode'])
        elif kwargs["menu_item"] == "radio_xformOp":
            self.setXformOp(kwargs['radio_xformOp'])
            self.setBrushMode('xform')

        elif kwargs["menu_item"] == "radio_brushType":
            self.setBrushType(kwargs['radio_brushType'])

        elif kwargs["menu_item"] == "action_lockPoints":
            self.opLockPoints()
        elif kwargs["menu_item"] == "action_unlockPoints":
            self.opUnlockPoints()

        elif kwargs["menu_item"] == "toggle_selectAllPrimPoints":
            pu.setNodeParm(self._node, 'selectAllPrimPoints', kwargs['toggle_selectAllPrimPoints'], True, 'Invert Selection Mask')
        elif kwargs["menu_item"] == "toggle_affectAhead":
            pu.setNodeParm(self._node, 'affectAhead', kwargs['toggle_affectAhead'], True,'Toggle Affect Ahead')
        elif kwargs["menu_item"] == "toggle_affectBehind":
            pu.setNodeParm(self._node, 'affectBehind', kwargs['toggle_affectBehind'], True,'Toggle Affect Behind')


########## END OF STATE CLASS ###########

def screenDistToWorld(scene_viewer, world_pos, pixels):
    gv = scene_viewer.curViewport()
    screen_pos = gv.mapToScreen(world_pos)

    d, o = gv.mapToWorld(screen_pos[0] + float(pixels), screen_pos[1])
    ref_pos = hou.hmath.intersectPlane(world_pos, d, o, d)

    return (world_pos - ref_pos).length()

###################################### CREATE STATE #################################################################

def create_menu(state_typename):
    menu = hou.ViewerStateMenu('crowdGuideBrush_menu', 'Crowd Guide Brush')

    radioGroupName = 'radio_brushMode'
    menu.addRadioStrip(radioGroupName, 'Brush Mode', 'addremove')

    hk = su.hotkey(state_typename, 'hk_addremove', '1', 'Add Remove', 'Enable Add Remove Mode')
    menu.addRadioStripItem(radioGroupName, 'addremove', 'Add Remove', hotkey=hk)

    hk = su.hotkey(state_typename, 'hk_xform', '2', 'Xform', 'Enable Xform Mode')
    menu.addRadioStripItem(radioGroupName, 'xform', 'Xform', hotkey=hk)

    hk = su.hotkey(state_typename, 'hk_reverse', '3', 'Reverse', 'Enable Reverse Mode')
    menu.addRadioStripItem(radioGroupName, 'reverse', 'Reverse', hotkey=hk)

    hk = su.hotkey(state_typename, 'hk_clone', '4', 'Clone', 'Enable Clone Mode')
    menu.addRadioStripItem(radioGroupName, 'clone', 'Clone', hotkey=hk)

    hk = su.hotkey(state_typename, 'hk_join', '5', 'Join', 'Enable Join Mode')
    menu.addRadioStripItem(radioGroupName, 'join', 'Join', hotkey=hk)


    radioGroupName = 'radio_xformOp'
    menu.addRadioStrip(radioGroupName, 'Xform Op', 'move')

    hk = su.hotkey(state_typename, 'hk_move', 't', 'Move', 'Enable Move')
    menu.addRadioStripItem(radioGroupName, 'move', 'Move', hotkey=hk)

    hk = su.hotkey(state_typename, 'hk_rotate', 'r', 'Rotate', 'Enable Rotate')
    menu.addRadioStripItem(radioGroupName, 'rotate', 'Rotate', hotkey=hk)

    hk = su.hotkey(state_typename, 'hk_scale', 'e', 'Scale', 'Enable Scale')
    menu.addRadioStripItem(radioGroupName, 'scale', 'Scale', hotkey=hk)


    radioGroupName = 'radio_brushType'
    menu.addRadioStrip(radioGroupName, 'Brush Type', 'singlepoint')

    hk = su.hotkey(state_typename, 'hk_singlepoint', 'n', 'Single Point', 'Enable Single Point')
    menu.addRadioStripItem(radioGroupName, 'singlepoint', 'Single Point', hotkey=hk)

    hk = su.hotkey(state_typename, 'hk_circlebrush', 'b', 'Circle Brush', 'Enable Circle Brush')
    menu.addRadioStripItem(radioGroupName, 'circlebrush', 'Circle Brush', hotkey=hk)


    menu.addSeparator()
    hk = su.hotkey(state_typename, 'hk_toggle_selectAllPrimPoints', 'v', 'Toggle Select All Prim Points')
    menu.addToggleItem('toggle_selectAllPrimPoints', 'Select All Prim Points', False, hotkey=hk)
    menu.addToggleItem('toggle_affectAhead', 'Affect Ahead', False)
    menu.addToggleItem('toggle_affectBehind', 'Affect Behind', False)

    menu.addActionItem('action_lockPoints', 'Lock Selected Points')
    menu.addActionItem('action_unlockPoints', 'Unlock All Points')

    return menu
'''
def createViewerStateTemplate():
    """ Mandatory entry point to create and return the viewer state
        template to register. """


    #state_typename = kwargs["type"].definition().sections()["DefaultState"].contents()
    state_typename = "crowdGuideBrush_state"
    state_label = "Crowd Guide Brush"
    state_cat = hou.sopNodeTypeCategory()

    template = hou.ViewerStateTemplate(state_typename, state_label, state_cat)
    template.bindFactory(CrowdGuideBrush_Position)
    #template.bindIcon(kwargs["type"].icon())

    template.bindMenu(create_menu(state_typename))

    return template
'''




