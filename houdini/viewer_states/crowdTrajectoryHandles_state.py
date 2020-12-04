"""
State:          Drawabletest
State type:     drawabletest
Description:    Drawabletest
Author:         stephen
Date Created:   August 17, 2020 - 16:51:22
"""

# Usage: This sample uses a geometry drawable group to draw highlights
# when hovering over geometry polygons. Make sure to add an input on the
# node, connect a polygon mesh geometry and hit enter in the viewer.

import hou
import viewerstate.utils as su


class State(object):
    MSG = "LMB to Insert Handle.    LMB+Drag to Move handle on xz plane.    CTRL+LMB to Reset Handle.     MMB to Remove Handle."

    def __init__(self, state_name, scene_viewer):
        self.state_name = state_name
        self.scene_viewer = scene_viewer
        self.poly_id = -1
        self.cursor_text = "Text"
        self.geometry = None
        self.geometryHandles = None
        self.mouse_screen = hou.Vector2()
        self.cursorStartPos = hou.Vector3()
        self.handleStartPos = hou.Vector3()
        self.currentPoint = -1
        self.currentHandleIdx = -1
        self.currentPrimid = -1
        self.currentPrimu = -1
        self.dragAction = False
        self.isHandle = False
        self.autoSlide = False

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

        self.geometry = node.geometry()
        self.geometryHandles = node.node("OUT_HANDLE_POINTS").geometry()
        self.updateAutoSlide()
        #self.log(self.geometryHandles)
        self.show(True)

        self.scene_viewer.setPromptMessage(State.MSG)

    def onResume(self, kwargs):
        self.show(True)
        self.scene_viewer.setPromptMessage(State.MSG)


        self.updateAutoSlide()

    def onInterrupt(self, kwargs):
        self.show(False)

    def updateAutoSlide(self):
        ### Update the autoslide option from the node parameter
        self.autoSlide = (self.node.parm("autoSlideExisting").eval() == 1) and (self.node.parm("autoBake").eval() == 1)

    def insertHandle(self, primid, primu, pos_offset):
        ### Add a new entry into the Handles list
        with hou.undos.group("insertHandle"):
            count = self.multiparm.evalAsInt()
            self.multiparm.set(count + 1)
            #self.log("count ", count)
            #self.log("posOffset_%s" % (count + 1))
            #self.log("pos_offset ", pos_offset)
            self.node.parmTuple("posOffset_%s" % (count + 1)).set(pos_offset)
            self.node.parm("primid_%s" % (count + 1)).set(primid)
            self.node.parm("primu_%s" % (count + 1)).set(primu)

        return count + 1

    def removeHandleAtPoint(self, point_id):
        ### Remove an entry from the Handles list

        index = self.findHandleIndexAtHandlePoint(point_id)
        if index > -1:
            with hou.undos.group("Remove Handle Index"):
                #self.log("removing handle: ", index)
                self.multiparm.removeMultiParmInstance(index - 1)


    def setHandlePosition(self, index, position):
        ### Set the Position Offset parm for a Handle entry
        #self.log("setHandlePosition: %d p: %s" % (index, position))
        with hou.undos.group("setHandlePos"):
            self.node.parmTuple("posOffset_%s" % (index)).set(position)

    def findHandleIndexAtPoint(self, point_id):
        ### Loop through the handle list to find an entry with the specified point_id

        handleIdx = -1
        count = self.multiparm.evalAsInt()
        for i in range(count):
            parmPoint = self.node.parm("pointid_%s" % (i + 1)).evalAsInt()
            if parmPoint == point_id:
                handleIdx = i + 1

        return handleIdx

    def findHandleIndexAtHandlePoint(self, point_id):
        ### Loop through the handle list to find an entry with the specified point_id

        if point_id < 0:
            return -1

        handleIdx = -1

        ### Lookup the primid and primu from the current handle point to compare against.
        handlePrim = self.geometryHandles.point(point_id).attribValue("primid")
        handlePrimU = self.geometryHandles.point(point_id).attribValue("u")

        #self.log("handlePrim", handlePrim)
        #self.log("handlePrimU", handlePrimU)

        ### Loop through the multiparm to find an entry with a matching primid and primu
        count = self.multiparm.evalAsInt()
        for i in range(count):
            parmPrimid = self.node.parm("primid_%s" % (i + 1)).evalAsInt()
            if parmPrimid == handlePrim:
                parmPrimu = self.node.parm("primu_%s" % (i + 1)).evalAsFloat()
                if abs(parmPrimu - handlePrimU) < 0.0001:
                    handleIdx = i + 1
                    break

        return handleIdx

    def getHandlePosition(self, index):
        ### Return the Position Offset vector at an index in the Handles List

        currentPos = hou.Vector3()
        if index > 0:
            currentPos = hou.Vector3(self.node.parmTuple("posOffset_%s" % (index)).eval())
        return currentPos

    def bakeAutoSlideToParms(self):
        ### Read updated attibs after sliding compensation and bake it back to the original parameter values
        #self.log('Baking values to parms!')
        handlesDeformGeo = self.node.node('OUT_HANDLES_DEFORMED').geometry()
        primu_list = handlesDeformGeo.pointFloatAttribValues('u')
        posOffset_list = handlesDeformGeo.pointFloatAttribValues('posOffset')
        #print posOffset_list
        parmidx_list = handlesDeformGeo.pointFloatAttribValues('parmidx')

        for i, parmidx in enumerate(parmidx_list):
            primu_parm = self.node.parm('primu_%d' % int(parmidx))
            primu_parm.set(primu_list[i])

            posOffset_parmT = self.node.parmTuple('posOffset_%d' % int(parmidx))
            #print posOffset_parmT
            ### Using pointFloatAttribValues on vectors returns one long list. We have to extract each 3 floats
            posOffset_value = [posOffset_list[i * 3], posOffset_list[i * 3 + 1], posOffset_list[i * 3 + 2]]
            #print posOffset_value
            # print value
            posOffset_parmT.set(posOffset_value)

        self.log('Baked Sliding Values!')

    def intersectGeo(self, collisionGeo, origin, dir, intersectTolerance, doSnapping=True):
        ### Try intersect the collision geo from the mouse position in the viewport

        gi = su.GeometryIntersector(collisionGeo, tolerance=intersectTolerance)
        gi.intersect(origin, dir, snapping=doSnapping)
        # print (gi.prim_num)
        # print (gi.geometry)
        # print (gi.position)
        # print (gi.snapped_point_num)
        return gi.prim_num, gi.position, gi.normal, gi.uvw

    def snapToNearestPointOfPrim(self, geometry, primnum, referencePos):
        ### Find the nearest real point on a primitive to a reference position by comparing to all primpoint positions.

        snap_pos = None
        pt_num = -1
        pt_u = -1

        if primnum != -1:
            min_dist = 1000000
            snap_pos = None
            pt_num = None

            for pt in geometry.prim(primnum).points():
                pos = pt.position()
                dist = (pos - referencePos).lengthSquared()
                if dist < min_dist:
                    min_dist = dist
                    snap_pos = pos
                    pt_num = pt.number()
                    pt_u = pt.attribValue("u")
        # print "pt_num:", pt_num
        # print "snap pos:", snap_pos
        return pt_num, pt_u, snap_pos

    def getNearestPointToCursor(self, origin, dir):
        ### Try intersect geometry from the mouse position ray, then get the nearest point on the prim

        primnum, position, normal, uvw = self.intersectGeo(self.geometry, origin, dir, 0.5, False)
        #self.log("primnum=", primnum)
        #self.log("uvw=", uvw)
        pt_num, pt_u, snap_pos = self.snapToNearestPointOfPrim(self.geometry, primnum, position)

        return primnum, pt_num, pt_u, snap_pos

    def getNearestHandleToCursor(self, origin, dir):
        ### Try intersect handle geometry from the mouse position ray to get the nearest point

        primnum, position, normal, uvw = self.intersectGeo(self.geometryHandles, origin, dir, 0.5, False)
        pt_num = primnum

        if not pt_num < 0:
            snap_pos = self.geometryHandles.point(pt_num).position()
        else:
            snap_pos = hou.Vector3(0, 0, 0)
        #self.log("handle primnum=", primnum)
        #self.log("handle uvw=", uvw)

        return pt_num, snap_pos

    def intersectOriginPlane(self, origin, direction):
        ### Intersect a flat plane to calculate a flat position offset vector

        planePos = hou.hmath.intersectPlane(hou.Vector3(0, 0, 0), hou.Vector3(0, 1, 0), origin, direction)
        return hou.Vector3(planePos)

    def highlightPoint(self, point_num, position):
        ### Display a pystate drawable at a points position

        if point_num != -1:
            if point_num != self.currentPoint:
                ### We're only updating currentPoint when it is different to minimize update calls to Drawables.
                self.currentPoint = point_num
                #u = self.geometry.prim(self.currentPrimid).attribValueAtInterior("u", self.currentPrimu, 0, 0)
                u = self.geometry.point(self.currentPoint).attribValue("u")
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

        #MOUSEX = ui_event.device().mouseX()
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
            pt_num, snap_pos = self.getNearestHandleToCursor(origin, dir)
            if (pt_num < 0):
                self.isHandle = False
                primnum, pt_num, pt_u, snap_pos = self.getNearestPointToCursor(origin, dir)

                ### TODO: get the agent_id on the prim rather than the primnum. More stable when removing agents
                self.currentPrimid = primnum
                self.currentPrimu = pt_u
                #self.log("pt_num: ", pt_num)
            else:
                self.isHandle = True

            self.highlightPoint(pt_num, snap_pos)
        #self.log("Primid:", self.currentPrimid)

        if MIDDLEBUTTON and self.isHandle is True:
            ### If we pressed with MMB, then try remove the handle at that point
            self.removeHandleAtPoint(pt_num)

        if LEFTBUTTON and not self.currentPoint < 0:
            if MOUSEDOWN:

                ### self.currentPoint is the nearest point to the mouse position (last set by highlightPoint)
                #self.log("click:", self.currentPoint)
                self.log("Primid:", self.currentPrimid)
                self.log("Primu:", self.currentPrimu)

                if self.isHandle is True:
                    ### If we are on an existing Handle entry at current Point then just update it
                    existingHandleIdx = self.findHandleIndexAtHandlePoint(self.currentPoint)

                    # self.log("existingHandleIdx", existingHandleIdx)
                    if CTRL:
                        ### Reset existing handle position offset
                        with hou.undos.group("Reset Handle"):
                            self.setHandlePosition(existingHandleIdx, hou.Vector3(0, 0, 0))
                    else:

                        self.scene_viewer.beginStateUndo("Move Handle")
                        self.handleStartPos = self.getHandlePosition(existingHandleIdx)
                        self.currentHandleIdx = existingHandleIdx
                        self.dragAction = True
                else:
                    ### If there is no existing Handle entry, create a new one and set it's values
                    self.scene_viewer.beginStateUndo("Add Handle and Move")
                    pos_offset = self.geometry.point(self.currentPoint).attribValue("deltaP")

                    ### u is the real u of the primitive curve. primu is the adjusted u after length constraint
                    #primu = self.geometry.prim(self.currentPrimid).attribValueAtInterior("primu", self.currentPrimu, 0, 0)
                    #self.currentHandleIdx = self.insertHandle(self.currentPrimid, primu, pos_offset)
                    self.currentHandleIdx = self.insertHandle(self.currentPrimid, self.currentPrimu, pos_offset)
                    self.handleStartPos = hou.Vector3(pos_offset)
                    self.dragAction = True

                ### Start the Drag state and set the start position for calculating offset
                if self.dragAction:
                    self.cursorStartPos = self.intersectOriginPlane(origin, dir)
                #self.dragAction = True

                ### Picked is a fast mouse press. It skips the mouse up event, so we need to treat is as a mouse up.
                if reason == hou.uiEventReason.Picked:
                    self.dragAction = False
                    self.scene_viewer.endStateUndo()

            ### If we are dragging with an active dragAction then update the Handle's position offset
            elif MOUSEDRAG and self.dragAction:
                planePos = self.intersectOriginPlane(origin, dir)
                deltaCursor = planePos - self.cursorStartPos
                self.setHandlePosition(self.currentHandleIdx, self.handleStartPos + deltaCursor)

        ### On Mouse Up we end the dragging state and the undo entry
        elif MOUSEUP and self.dragAction:
            #self.log("MOUSEUP")
            self.dragAction = False
            self.currentHandleIdx = -1
            self.currentPoint = -1
            if self.autoSlide:
                self.bakeAutoSlideToParms()
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
    state_typename = "crowdTrajectoryHandles_state"
    state_label = "Crowd Trajectory Handles"
    state_cat = hou.sopNodeTypeCategory()

    template = hou.ViewerStateTemplate(state_typename, state_label, state_cat)
    template.bindFactory(State)
    #template.bindIcon(kwargs["type"].icon())

    return template
