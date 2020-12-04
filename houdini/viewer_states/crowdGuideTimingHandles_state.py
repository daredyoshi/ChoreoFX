"""
State:          crowdGuideTimingHandles_state
Author:         stephen
"""

import hou
#import viewerstate.utils as su
from choreofx.states import cursor_intersect as ci

class State(object):
    MSG = "LMB to Insert Handle.    LMB+Drag to slide along path.    CTRL+LMB+Drag to change frame time.     MMB to Remove Handle."

    POSATTRIBS = ('u', 'primdist')

    def __init__(self, state_name, scene_viewer):
        self.state_name = state_name
        self.scene_viewer = scene_viewer
        self.poly_id = -1
        self.cursor_text = "Text"
        self.geometry = None
        self.geometryHandles = None
        self.mouseStart = hou.Vector2()
        self.mouseXLast = -1
        self.mouse_screen = hou.Vector2()
        self.cursorStartPos = hou.Vector3()
        self.dragStartValue = 0
        self.handleStartPos = hou.Vector3()
        self.currentPoint = -1
        self.currentHandleIdx = -1
        self.currentPrimid = -1
        self.currentPrimu = -1
        self.currentPrimDist = -1
        self.dragAction = False
        self.isHandle = False
        self.autoSlide = False
        self.slideHandlesAhead = False
        self.slideHandlesBehind = False
        self.handlePosMethod = 0

        self.text = hou.TextDrawable(self.scene_viewer, "text")

        # Construct a geometry drawable group
        line = hou.GeometryDrawable(self.scene_viewer, hou.drawableGeometryType.Line, "line",
                                    params={
                                        "color1": (0.0, 0.0, 1.0, 1.0),
                                        "style": hou.drawableGeometryLineStyle.Plain,
                                        "line_width": 3}
                                    )

        face = hou.GeometryDrawable(self.scene_viewer, hou.drawableGeometryType.Face, "face",
                                    params={
                                        "style": hou.drawableGeometryFaceStyle.Plain,
                                        "color1": (0.0, 1.0, 0.0, 1.0)}
                                    )

        point = hou.GeometryDrawable(self.scene_viewer, hou.drawableGeometryType.Point, "point",
                                     params={
                                         "num_rings": 2,
                                         "radius": 8,
                                         "color1": (1.0, 0.0, 0.0, 1.0),
                                         "style": hou.drawableGeometryPointStyle.LinearCircle}
                                     )

        self.poly_guide = hou.GeometryDrawableGroup("poly_guide")

        self.poly_guide.addDrawable(face)
        self.poly_guide.addDrawable(line)
        self.poly_guide.addDrawable(point)

    def show(self, visible):
        """ Display or hide drawables.
        """
        self.text.show(visible)
        self.poly_guide.show(visible)

    def onEnter(self, kwargs):
        """ Assign the geometry to drawabled
        """
        node = kwargs["node"]
        self.node = node
        self.multiparm = node.parm("Handles")
        self.geometry = node.node("OUT_POSITION_PATHS").geometry()
        #self.geometry = node.geometry()
        self.geometryHandles = node.node("OUT_HANDLE_PRIMS").geometry()
        self.updateVarsFromParms()
        self.show(True)
        self.scene_viewer.setPromptMessage(State.MSG)

    def onResume(self, kwargs):
        self.show(True)
        self.scene_viewer.setPromptMessage(State.MSG)
        self.updateVarsFromParms()

    def onInterrupt(self, kwargs):
        self.show(False)

    def setNodeParm(self, parmname, value, undo=False, undoname=''):
        if undo:
            if undoname != '':
                with hou.undos.group(undoname):
                    self.node.parm(parmname).set(value)
            else:
                self.node.parm(parmname).set(value)
        else:
            with hou.undos.disabler():
                self.node.parm(parmname).set(value)

    def updateNodeCurrentParms(self):
        self.setNodeParm("currentPrim", self.currentPrimid)

        if self.handlePosMethod == 1:
            self.setNodeParm("currentPosValue", self.currentPrimDist)
        else:
            self.setNodeParm("currentPosValue", self.currentPrimu)

    def updateVarsFromParms(self):
        ### Update the internal variables from the node parameters
        self.handlePosMethod = self.node.parm("posMethod").evalAsInt()
        self.slideHandlesAhead = self.node.parm("adjustAhead").evalAsInt()
        self.slideHandlesBehind = self.node.parm("adjustBehind").evalAsInt()
        #self.log("handlePosMethod ", self.handlePosMethod )
        #self.log("POSATTRIB ", self.POSATTRIBS[self.handlePosMethod])
        #self.autoSlide = (self.node.parm("autoSlideExisting").eval() == 1) and (self.node.parm("autoBake").eval() == 1)

    def insertHandle(self, primid, primu, pos_offset):
        ### Add a new entry into the Handles list
        with hou.undos.group("insertHandle"):
            count = self.multiparm.evalAsInt()
            self.multiparm.set(count + 1)
            #self.log("count ", count)
            #self.log("posOffset_%s" % (count + 1))
            #self.log("pos_offset ", pos_offset)
            #self.node.parmTuple("posOffset_%s" % (count + 1)).set(pos_offset)
            self.node.parm("primid_%s" % (count + 1)).set(primid)
            self.node.parm("primu_%s" % (count + 1)).set(primu)

        return count + 1

    def insertHandleWithValue(self, primid, posParmName, posValue):
        ### Add a new entry into the Handles list at Distance Along Curve
        with hou.undos.group("insertHandle"):
            count = self.multiparm.evalAsInt()
            self.multiparm.set(count + 1)
            self.node.parm("primid_%s" % (count + 1)).set(primid)
            self.node.parm("%s_%s" % (posParmName, count + 1)).set(posValue)
        return count + 1

    def removeHandleAtPoint(self, point_id):
        ### Remove an entry from the Handles list

        index = self.findHandleIndexAtHandlePoint(point_id, self.POSATTRIBS[self.handlePosMethod])
        if index > -1:
            with hou.undos.group("Remove Handle Index"):
                #self.log("removing handle: ", index)
                self.multiparm.removeMultiParmInstance(index - 1)


    def setHandlePosition(self, index, position):
        ### Set the Position Offset parm for a Handle entry
        #self.log("setHandlePosition: %d p: %s" % (index, position))
        with hou.undos.group("setHandlePos"):
            pass
            #self.node.parmTuple("posOffset_%s" % (index)).set(position)

    def setHandleParm(self, parmname, index, value):
        ### Set value of the parameter with parmname at index
        #self.log("set " + parmname + ": %d p: %s" % (index, position))
        with hou.undos.group("set "+ parmname):
            self.node.parm(parmname + "%s" % (index)).set(value)

    def evalHandleParm(self, parmname, index):
        self.log("%s%s" % (parmname, index))
        ### Get value of the parameter with parmname at index
        currentValue = 0
        if index > 0:
            currentValue = self.node.parm("%s%s" % (parmname, index)).eval()

        return currentValue

    def getGlobalFrameAtInsertPoint(self):
        self.updateNodeCurrentParms()
        return self.geometryHandles.intAttribValue("current_global_frame")

    def findHandleIndexAtPoint(self, point_id):
        ### Loop through the handle list to find an entry with the specified point_id

        handleIdx = -1
        count = self.multiparm.evalAsInt()
        for i in range(count):
            parmPoint = self.node.parm("pointid_%s" % (i + 1)).evalAsInt()
            if parmPoint == point_id:
                handleIdx = i + 1

        return handleIdx

    def  findHandleIndexAtHandlePoint(self, point_id, matchAttrib):
        ### Loop through the handle list to find an entry with the specified point_id

        if point_id < 0:
            return -1

        handleIdx = -1

        ### Lookup the primid and primu from the current handle point to compare against.
        handlePrim = self.geometryHandles.point(point_id).attribValue("primid")

        if matchAttrib == "u":
            handleValue = self.geometryHandles.point(point_id).attribValue("u")
        elif matchAttrib == "primdist":
            handleValue = self.geometryHandles.point(point_id).attribValue("primdist")

        #self.log("handlePrim", handlePrim)
        #self.log("handlePrimU", handlePrimU)

        ### Loop through the multiparm to find an entry with a matching primid and primu
        count = self.multiparm.evalAsInt()
        for i in range(count):
            parmPrimid = self.node.parm("primid_%s" % (i + 1)).evalAsInt()
            if parmPrimid == handlePrim:
                if matchAttrib == "primu":
                    parmValue = self.node.parm("primu_%s" % (i + 1)).evalAsFloat()
                elif matchAttrib == "primdist":
                    parmValue = self.node.parm("primdist_%s" % (i + 1)).evalAsFloat()

                if abs(parmValue - handleValue) < 0.0001:
                    handleIdx = i + 1
                    break

        return handleIdx

    def getHandlePosition(self, index):
        ### Return the Position Offset vector at an index in the Handles List

        currentPos = hou.Vector3()
        if index > 0:
            currentPos = hou.Vector3(self.node.parmTuple("posOffset_%s" % (index)).eval())
        return currentPos


    def slideHandleParms(self, parmname, index, value):
        indexprimid = self.node.parm("%s%s" % ("primid_", index)).eval()

        parmValue = self.node.parm("%s%s" % (parmname, index)).eval()
        anchorValue = parmValue
        self.setHandleParm(parmname, index, parmValue + value)

        if self.slideHandlesAhead or self.slideHandlesBehind:
            count = self.multiparm.evalAsInt()

            for i in range(1, count+1, 1):
                primid = self.node.parm("%s%s" % ("primid_", i)).eval()
                if i == index or primid != indexprimid:
                    continue

                parmValue = self.node.parm("%s%s" % (parmname, i)).eval()
                if self.slideHandlesBehind and parmValue < anchorValue:
                    self.setHandleParm(parmname, i, parmValue + value)
                elif self.slideHandlesAhead and parmValue > anchorValue:
                    self.setHandleParm(parmname, i, parmValue + value)




    def highlightPoint(self, point_num, position):
        ### Display a pystate drawable at a points position

        if point_num != -1:
            if point_num != self.currentPoint:
                ### We're only updating currentPoint when it is different to minimize update calls to Drawables.
                self.currentPoint = point_num

                ### Text Visualizer at cursor
                #u = self.geometry.prim(self.currentPrimid).attribValueAtInterior("u", self.currentPrimu, 0, 0)
                u = self.geometry.point(self.currentPoint).attribValue("primdist")
                self.cursor_text = "<font size=4,>%f</font>" % (u)

                new_geo = hou.Geometry()
                point = new_geo.createPoint()
                point.setPosition(position)

                # update the drawable
                self.poly_guide.setGeometry(new_geo)
                self.show(True)

        else:
            self.currentPoint = -1
            self.poly_geo = None
            self.show(False)


    def onMouseEvent(self, kwargs):
        """ Computes the cursor text position and drawable geometry
        """
        ui_event = kwargs["ui_event"]
        reason = ui_event.reason()
        #self.log(reason)

        MOUSEX = ui_event.device().mouseX()
        #MOUSEY = ui_event.device().mouseY()

        LEFTBUTTON = ui_event.device().isLeftButton()
        MIDDLEBUTTON = ui_event.device().isMiddleButton()
        RIGHTBUTTON = ui_event.device().isRightButton()

        MOUSEDOWN = reason == hou.uiEventReason.Start or reason == hou.uiEventReason.Picked
        MOUSEUP = reason == hou.uiEventReason.Changed
        MOUSEDRAG = reason == hou.uiEventReason.Active

        CTRL = ui_event.device().isCtrlKey()

        #self.log("MOUSEUP ", MOUSEUP)
        #self.log("LEFTBUTTON ", LEFTBUTTON)

        ### Get mouse screen position
        (origin, dir) = ui_event.ray()
        self.mouse_screen = self.scene_viewer.curViewport().mapToScreen(origin)
        # self.cursor_text = "<font size=4,>%.2f, %.2f</font>" % ( self.mouse_screen[0], self.mouse_screen[1] )


        ### If we are not currently pulling a handle then try get the nearest point to the mouse
        if not self.dragAction:
            #snap_pos = hou.Vector3(0,0,0)
            primnum = -1
            pt_u = -1
            #pt_num = -1

            ### First by getting a nearby handle point. If that fails, try get a point on the paths geometry
            pt_num, snap_pos = ci.getNearestHandleToCursor(self.geometryHandles, origin, dir)
            if (pt_num < 0):
                self.isHandle = False
                primnum, pt_num, pt_u, snap_pos = ci.getNearestPointToCursor(self.geometry, origin, dir)

                ### TODO: get the agent_id on the prim rather than the primnum. More stable when removing agents
                self.currentPrimid = primnum
                self.currentPrimu = pt_u
                #self.currentPrimDist =
                #self.log("pt_num: ", pt_num)
            else:
                self.isHandle = True

            self.highlightPoint(pt_num, snap_pos)

        #self.log("Primid:", self.currentPrimid)
        #self.log("pt_num:", pt_num)

        if MIDDLEBUTTON and self.isHandle is True:
            ### If we pressed with MMB on a handle, start a frame time drag action
            if MOUSEDOWN:
                existingHandleIdx = self.findHandleIndexAtHandlePoint(self.currentPoint,  self.POSATTRIBS[self.handlePosMethod])

                self.scene_viewer.beginStateUndo("Slide Handle Frame")
                # self.handleStartPos = self.getHandlePosition(existingHandleIdx)
                self.currentHandleIdx = existingHandleIdx
                self.dragAction = True
                self.mouseStart = MOUSEX

                self.dragStartValue = self.evalHandleParm("globalFrame_", self.currentHandleIdx)
                #self.removeHandleAtPoint(pt_num)
            elif MOUSEDRAG and self.dragAction:
                planePos = ci.intersectOriginPlane(origin, dir)
                #deltaCursor = planePos - self.cursorStartPos
                #deltaX = self.mouseStart - MOUSEX
                deltaX = MOUSEX - self.mouseXLast

                #self.setHandleParm("globalFrame_", self.currentHandleIdx, self.dragStartValue - int(deltaX * 0.5))
                self.slideHandleParms("globalFrame_", self.currentHandleIdx, int(deltaX * 0.5))


        if LEFTBUTTON and not self.currentPoint < 0:
            if MOUSEDOWN:

                ### self.currentPoint is the nearest point to the mouse position (last set by highlightPoint)
                #self.log("click:", self.currentPoint)
                self.log("Primid:", self.currentPrimid)
                self.log("Primu:", self.currentPrimu)
                self.log("PrimDist:", self.currentPrimDist)


                if self.isHandle is True:


                    ### If we are on an existing Handle entry at current Point then just update it
                    existingHandleIdx = self.findHandleIndexAtHandlePoint( self.currentPoint,  self.POSATTRIBS[self.handlePosMethod])

                    # self.log("existingHandleIdx", existingHandleIdx)
                    if CTRL:
                        ### If we CTRL+LMB, then try remove the handle at that point
                        self.removeHandleAtPoint(pt_num)
                        ### Reset existing handle position offset
                        #with hou.undos.group("Reset Handle"):
                        #    self.setHandlePosition(existingHandleIdx, hou.Vector3(0, 0, 0))
                    else:

                        self.scene_viewer.beginStateUndo("Slide Handle PrimU")
                        #self.handleStartPos = self.getHandlePosition(existingHandleIdx)
                        self.currentHandleIdx = existingHandleIdx
                        self.currentPrimDist = self.evalHandleParm("primdist_", self.currentHandleIdx)
                        self.dragAction = True
                else:
                    if not CTRL:
                        if self.handlePosMethod == 1:
                            self.currentPrimDist = self.geometry.point(self.currentPoint).attribValue("primdist")

                        self.log("PrimDist:", self.currentPrimDist)

                        ### If there is no existing Handle entry, create a new one and set it's values
                        self.scene_viewer.beginStateUndo("Add Handle and Slide PrimU")
                        pos_offset = self.geometry.point(self.currentPoint).position()
                        #self.dragStartValue = self.evalHandleParm("globalFrame_", self.currentHandleIdx)

                        ### u is the real u of the primitive curve. primu is the adjusted u after length constraint
                        #primu = self.geometry.prim(self.currentPrimid).attribValueAtInterior("primu", self.currentPrimu, 0, 0)
                        #self.currentHandleIdx = self.insertHandle(self.currentPrimid, primu, pos_offset)

                        ### Get the interpolated global frame between existing handles at the cursor point
                        newHandleGlobalFrame = self.getGlobalFrameAtInsertPoint()

                        if self.handlePosMethod == 1:
                            self.currentHandleIdx = self.insertHandleWithValue(self.currentPrimid, "primdist", self.currentPrimDist)
                        else:
                            self.currentHandleIdx = self.insertHandle(self.currentPrimid, self.currentPrimu, pos_offset)

                        self.setHandleParm("globalFrame_", self.currentHandleIdx, newHandleGlobalFrame)
                        self.dragStartValue = self.currentPrimDist
                        self.isHandle = True
                        self.handleStartPos = hou.Vector3(pos_offset)
                        #self.setHandleParm("globalFrame_", self.currentHandleIdx, 0)
                        self.dragAction = True

                ### Start the Drag state and set the start position for calculating offset
                if self.dragAction:
                    self.mouseStart = MOUSEX
                    self.cursorStartPos = ci.intersectOriginPlane(origin, dir)

                    if self.handlePosMethod == 1:
                        self.dragStartValue = self.currentPrimDist
                    else:
                        self.dragStartValue = self.currentPrimu
                    #self.dragStartValue = 0
                    #if self.isHandle is True:
                        #self.dragStartValue = self.geometryHandles.point(self.currentPoint).attribValue("global_frame")
                        #self.dragStartValue = self.evalHandleParm("globalFrame_", self.currentHandleIdx)
                        #self.dragStartValue = self.evalHandleParm("globalFrame_", self.currentHandleIdx)
                    self.log("dragStartValue:", self.dragStartValue)
                #self.dragAction = True

                ### Picked is a fast mouse press. It skips the mouse up event, so we need to treat is as a mouse up.
                if reason == hou.uiEventReason.Picked:
                    self.dragAction = False
                    self.scene_viewer.endStateUndo()

            ### If we are dragging with an active dragAction then update the Handle's position offset
            elif MOUSEDRAG and self.dragAction:
                planePos = ci.intersectOriginPlane(origin, dir)
                #deltaCursor = planePos - self.cursorStartPos
                #deltaX = self.mouseStart - MOUSEX
                deltaX = MOUSEX - self.mouseXLast

                #self.setHandleParm("globalFrame_", self.currentHandleIdx, self.dragStartValue - int(deltaX * 0.5))
                if self.handlePosMethod == 1:
                    #self.setHandleParm("primdist_", self.currentHandleIdx, self.dragStartValue - (deltaX * 0.1))
                    self.slideHandleParms("primdist_", self.currentHandleIdx, (deltaX * 0.1))
                else:
                    self.setHandleParm("primu_", self.currentHandleIdx, self.dragStartValue - (deltaX * 0.001))

        ### On Mouse Up we end the dragging state and the undo entry
        elif MOUSEUP and self.dragAction:
            #self.log("MOUSEUP")
            self.dragAction = False
            self.currentHandleIdx = -1
            self.currentPoint = -1
            #if self.autoSlide:
            #    self.bakeAutoSlideToParms()
            self.scene_viewer.endStateUndo()

        self.mouseXLast = MOUSEX

    def onDraw(self, kwargs):
        """ This callback is used for rendering the drawables
        """
        handle = kwargs["draw_handle"]

        self.poly_guide.draw(handle)

        # cursor text
        params = {
            "text": self.cursor_text,
            "multi_line": True,
            "translate": (self.mouse_screen[0], self.mouse_screen[1], 0.0),
            "highlight_mode": hou.drawableHighlightMode.MatteOverGlow,
            "glow_width": 1,
            "color1": hou.Color(1.0, 1.0, 1.0),
            "color2": (0.0, 0.0, 0.0, 1.0)}
        self.text.draw(handle, params)


def createViewerStateTemplate():
    """ Mandatory entry point to create and return the viewer state
        template to register. """

    #state_typename = kwargs["type"].definition().sections()["DefaultState"].contents()
    state_typename = "crowdGuideTimingHandles_state"
    state_label = "Crowd Guide Timing Handles"
    state_cat = hou.sopNodeTypeCategory()

    template = hou.ViewerStateTemplate(state_typename, state_label, state_cat)
    template.bindFactory(State)
    #template.bindIcon(kwargs["type"].icon())

    return template
