"""
State:          crowdGuidePlacementHandles_state
Author:         stephen
"""

import hou
import viewerstate.utils as su
from choreofx.states import cursor_intersect as ci
reload(ci)

def setNodeParm(node, parmname, value, undo=False, undoname=''):
    if undo:
        if undoname != '':
            with hou.undos.group(undoname):
                node.parm(parmname).set(value)
        else:
            node.parm(parmname).set(value)
    else:
        with hou.undos.disabler():
            node.parm(parmname).set(value)




class State(object):
    MSG = "LMB to Insert or Place Handle.    LMB+Drag to Move handle.    CTRL+LMB to Remove Handle.\n     MMB to End Drawing.    SHIFT+LMB to Start New Prim.    SHIFT+LMB on Tips to Extend Existing"

    def __init__(self, state_name, scene_viewer):
        self.state_name = state_name
        self.scene_viewer = scene_viewer
        self.poly_id = -1
        self.cursor_text = "Text"
        self.geometry = None
        self.geometryHandles = None
        self.mouse_screen = hou.Vector2()
        self.cursorPos = hou.Vector3()
        self.cursorStartPos = hou.Vector3()
        self.handleStartPos = hou.Vector3()
        self.currentPoint = -1
        self.currentHandleIdx = -1
        self.currentPrimid = -1
        self.currentPrimVtxCount = -1
        self.currentPointIndex = -1
        #self.currentPrimu = -1
        self.dragAction = False
        self.isHandle = False
        #self.autoSlide = False
        self.drawActive = False
        self.drawFromStart = False

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

    def showGuides(self, visible):
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

        self.geometry = node.geometry()
        self.geometryHandles = node.node("OUT_HANDLE_POINTS").geometry()

        self.showGuides(True)
        self.scene_viewer.setPromptMessage(State.MSG)

        if self.multiparm.evalAsInt() == 0:
            self.setDrawActive(True)
            self.currentPrimid = 0


    def onExit(self, kwargs):
        """ Called when the state terminates
        """
        self.setDrawActive(False)


    def onResume(self, kwargs):
        self.showGuides(True)
        self.scene_viewer.setPromptMessage(State.MSG)


    def onInterrupt(self, kwargs):
        self.showGuides(False)


    def updateCursorPosition(self, position):
        with hou.undos.disabler():
            self.node.parmTuple("cursorPos").set(position)


    def updateNodeCurrentAttribs(self):
        with hou.undos.disabler():
            self.node.parm("currentPrim").set(self.currentPrimid)
            self.node.parm("currentPointIndex").set(self.currentPointIndex)


    def insertHandle(self, primid, pointindex, position):
        ### Add a new entry into the Handles list
        with hou.undos.group("insertHandle"):
            count = self.multiparm.evalAsInt()
            self.multiparm.set(count + 1)
            #self.log("count ", count)
            #self.log("posOffset_%s" % (count + 1))
            #self.log("pos_offset ", pos_offset)
            self.node.parmTuple("position_%s" % (count + 1)).set(position)
            self.node.parm("primid_%s" % (count + 1)).set(primid)
            self.node.parm("pointindex_%s" % (count+1)).set(pointindex)

        return count + 1


    def removeHandleAtPoint(self, point_id):
        ### Remove an entry from the Handles list
        parmindex = self.findHandleIndexAtHandlePoint(point_id)
        self.log("parmindex", parmindex)

        if parmindex > -1:
            with hou.undos.group("Remove Handle Index"):
                #self.log("removing handle: ", index)
                pointIndex = self.node.parm("pointindex_%s" % parmindex).eval()
                self.multiparm.removeMultiParmInstance(parmindex - 1)
                self.offsetExistingHandlesPointIndex(self.currentPrimid, pointIndex, -1)


    def setCurrentPrimAndIndexToPoint(self, point_id):
        ### Set current vars to the primid, pointindex, and vtxcount of the specified point and update node parms
        self.currentPrimid = self.geometryHandles.point(point_id).attribValue("primid")
        self.currentPointIndex = self.geometryHandles.point(point_id).attribValue("pointindex")
        self.currentPrimVtxCount = self.geometryHandles.point(point_id).attribValue("vtxcount")
        self.updateNodeCurrentAttribs()

        ### If the selected point is the end of a primitive, activate Drawing
        if self.currentPointIndex == 0:
            self.setDrawActive(True)
            self.drawFromStart = True
        elif self.currentPointIndex == self.currentPrimVtxCount-1:
            self.setDrawActive(True)
            self.drawFromStart = False


    def setHandlePosition(self, index, position):
        ### Set the Position Offset parm for a Handle entry
        #self.log("setHandlePosition: %d p: %s" % (index, position))
        with hou.undos.group("setHandlePos"):
            self.node.parmTuple("position_%s" % (index)).set(position)


    def findHandleIndexAtHandlePoint(self, point_id):
        ### Loop through the handle list to find an entry with the primid and pointindex of the specified Point

        if point_id < 0:
            return -1

        handleIdx = -1

        ### Lookup the primid and pointindex from the current handle point to compare against.
        handlePrim = self.geometryHandles.point(point_id).attribValue("primid")
        handleIndex = self.geometryHandles.point(point_id).attribValue("pointindex")
        #self.log("handlePrim", handlePrim)

        count = self.multiparm.evalAsInt()
        for i in range(count):
            parmPrimid = self.node.parm("primid_%s" % (i + 1)).evalAsInt()
            if parmPrimid == handlePrim:
                parmPointIndex = self.node.parm("pointindex_%s" % (i + 1)).evalAsInt()
                if abs(parmPointIndex - handleIndex) < 0.0001:
                    handleIdx = i + 1
                    break

        return handleIdx


    def getHandlePosition(self, index):
        ### Return the Position Offset vector at an index in the Handles List
        currentPos = hou.Vector3()
        if index > 0:
            currentPos = hou.Vector3(self.node.parmTuple("position_%s" % (index)).eval())
        return currentPos


    def offsetExistingHandlesPointIndex(self, primid, startIndex, offset):
        count = self.multiparm.evalAsInt()
        for i in range(count):
            parmPrimid = self.node.parm("primid_%s" % (i + 1)).evalAsInt()
            if parmPrimid == primid:
                parmPointIndex = self.node.parm("pointindex_%s" % (i + 1)).evalAsInt()
                self.log("offset", parmPointIndex, parmPointIndex > startIndex)
                if parmPointIndex > startIndex:
                    self.node.parm("pointindex_%s" % (i + 1)).set(parmPointIndex + offset)


    def highlightPoint(self, point_num, position):
        ### Display a pystate drawable at a points position

        if point_num != -1:
            if point_num != self.currentPoint:
                ### We're only updating currentPoint when it is different to minimize update calls to Drawables.
                self.currentPoint = point_num
                #u = self.geometry.prim(self.currentPrimid).attribValueAtInterior("u", self.currentPrimu, 0, 0)
                #u = self.geometry.point(self.currentPoint).attribValue("u")
                #self.cursor_text = "<font size=4,>%f</font>" % (u)

                new_geo = hou.Geometry()
                point = new_geo.createPoint()
                point.setPosition(position)

                # update the drawable
                self.poly_guide.setGeometry(new_geo)
                self.showGuides(True)

        else:
            self.currentPoint = -1
            self.poly_geo = None
            self.showGuides(False)

    def setDrawActive(self, state):
        self.drawActive = state
        setNodeParm(self.node, "drawActive", state)


    def onMouseEvent(self, kwargs):
        """ Computes the cursor text position and drawable geometry
        """
        ui_event = kwargs["ui_event"]
        reason = ui_event.reason()
        #self.log(reason)

        #MOUSEX = ui_event.device().mouseX()
        #MOUSEY = ui_event.device().mouseY()

        LEFTBUTTON = ui_event.device().isLeftButton()
        MIDDLEBUTTON = ui_event.device().isMiddleButton()
        RIGHTBUTTON = ui_event.device().isRightButton()

        MOUSEDOWN = reason == hou.uiEventReason.Start or reason == hou.uiEventReason.Picked
        MOUSEUP = reason == hou.uiEventReason.Changed
        MOUSEDRAG = reason == hou.uiEventReason.Active

        CTRL = ui_event.device().isCtrlKey()
        SHIFT = ui_event.device().isShiftKey()

        #self.log("MOUSEUP ", MOUSEUP)
        #self.log("LEFTBUTTON ", LEFTBUTTON)

        ### Get mouse screen position
        (origin, dir) = ui_event.ray()
        self.mouse_screen = self.scene_viewer.curViewport().mapToScreen(origin)
        # self.cursor_text = "<font size=4,>%.2f, %.2f</font>" % ( self.mouse_screen[0], self.mouse_screen[1] )


        ### If we are not currently pulling a handle then try get the nearest point to the mouse
        if self.drawActive is True:
            if self.drawActive is True:
                self.cursorPos = ci.intersectOriginPlane(origin, dir)
                self.updateCursorPosition(self.cursorPos)

        elif not self.dragAction:
            #snap_pos = hou.Vector3(0,0,0)
            primnum = -1
            pt_u = -1
            #pt_num = -1

            ### First by getting a nearby handle point. If that fails, try get a point on the paths geometry
            pt_num, snap_pos = ci.getNearestHandleToCursor(self.geometryHandles, origin, dir)
            if pt_num < 0:
                self.isHandle = False
                primnum, pt_num, pt_u, snap_pos = ci.getNearestPointToCursor(self.geometry, origin, dir)

                self.currentPrimid = primnum
                self.currentPrimu = pt_u
                #self.log("pt_num: ", pt_num)

            else:
                self.currentPrimid = self.geometryHandles.point(pt_num).attribValue("primid")
                self.isHandle = True

            self.highlightPoint(pt_num, snap_pos)
        #self.log("Primid:", self.currentPrimid)


        if MIDDLEBUTTON:
            ### If we pressed with MMB, end drawing mode
            self.setDrawActive(False)
            pass
            #self.removeHandleAtPoint(pt_num)

        if LEFTBUTTON:
            if MOUSEDOWN:
                ### If not pressing an existing point and drawing mode is active then make a new handle at cursor
                if self.currentPoint < 0:
                    if self.drawActive is True:

                        self.scene_viewer.beginStateUndo("Create Handle and Move")
                        if self.drawFromStart:
                            self.currentPointIndex = 0
                            self.offsetExistingHandlesPointIndex(self.currentPrimid, self.currentPointIndex-1, 1)
                        else:
                            self.currentPointIndex += 1

                        self.currentHandleIdx = self.insertHandle(self.currentPrimid, self.currentPointIndex, self.cursorPos)
                        self.handleStartPos = hou.Vector3()
                        self.cursorStartPos = hou.Vector3()
                        self.dragAction = True

                        self.updateNodeCurrentAttribs()


                else:
                    ### self.currentPoint is the nearest point to the mouse position (last set by highlightPoint)
                    #self.log("click:", self.currentPoint)
                    self.log("Primid:", self.currentPrimid)
                    #self.log("Primu:", self.currentPrimu)

                    if self.isHandle is True:
                        ### If we are on an existing Handle entry at current Point then just update it
                        existingHandleIdx = self.findHandleIndexAtHandlePoint(self.currentPoint)

                        # self.log("existingHandleIdx", existingHandleIdx)
                        if CTRL:
                            ### Reset existing handle position offset
                            self.removeHandleAtPoint(self.currentPoint)
                            #with hou.undos.group("Reset Handle"):
                            #    self.setHandlePosition(existingHandleIdx, hou.Vector3(0, 0, 0))
                        elif SHIFT:
                            self.setCurrentPrimAndIndexToPoint(self.currentPoint)
                            ### Reset existing handle position offset
                        else:

                            self.scene_viewer.beginStateUndo("Move Handle")
                            self.handleStartPos = self.getHandlePosition(existingHandleIdx)
                            self.currentHandleIdx = existingHandleIdx
                            self.dragAction = True
                    else:
                        ### If there is no existing Handle entry, create a new one and set it's values
                        self.scene_viewer.beginStateUndo("Insert Handle and Move")
                        position = self.geometry.point(self.currentPoint).position()

                        ### u is the real u of the primitive curve. primu is the adjusted u after length constraint
                        #primu = self.geometry.prim(self.currentPrimid).attribValueAtInterior("primu", self.currentPrimu, 0, 0)
                        #self.currentHandleIdx = self.insertHandle(self.currentPrimid, primu, pos_offset)
                        self.offsetExistingHandlesPointIndex(self.currentPrimid, self.currentPointIndex, 1)
                        self.currentHandleIdx = self.insertHandle(self.currentPrimid, self.currentPointIndex+1, position)
                        self.handleStartPos = hou.Vector3(position)
                        self.dragAction = True

                    ### Start the Drag state and set the start position for calculating offset
                    if self.dragAction:
                        self.cursorStartPos = ci.intersectOriginPlane(origin, dir)
                    #self.dragAction = True

                ### Picked is a fast mouse press. It skips the mouse up event, so we need to treat is as a mouse up.
                if reason == hou.uiEventReason.Picked:
                    self.dragAction = False
                    self.scene_viewer.endStateUndo()

            ### If we are dragging with an active dragAction then update the Handle's position offset
            elif MOUSEDRAG and self.dragAction:
                planePos = ci.intersectOriginPlane(origin, dir)
                deltaCursor = planePos - self.cursorStartPos
                self.setHandlePosition(self.currentHandleIdx, self.handleStartPos + deltaCursor)

        ### On Mouse Up we end the dragging state and the undo entry
        elif MOUSEUP and self.dragAction:
            #self.log("MOUSEUP")
            self.dragAction = False
            self.currentHandleIdx = -1
            self.currentPoint = -1
            #if self.autoSlide:
            #    self.bakeAutoSlideToParms()
            self.scene_viewer.endStateUndo()

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
    state_typename = "crowdGuidePlacementHandles_state"
    state_label = "Crowd Guide Placement Handles"
    state_cat = hou.sopNodeTypeCategory()

    template = hou.ViewerStateTemplate(state_typename, state_label, state_cat)
    template.bindFactory(State)
    #template.bindIcon(kwargs["type"].icon())

    return template
