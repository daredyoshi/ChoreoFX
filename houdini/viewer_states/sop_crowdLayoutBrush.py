"""
Author:         ChoreoFX
"""

import hou
import viewerstate.utils as su
import stateutils
import math


class CrowdBrush(object):

    mode_info = []
    mode_info.append({'name': 'create',
                          'prompt': '1) Click to add points',
                          'hotkey': None,
                          'auto_start': False,
                          'allow_drag': True,
                          'quick_select': True,
                          'geometry_types': (hou.geometryType.Primitives,),
                          'secure_selection': hou.secureSelectionOption.Ignore})

    BRUSHSHAPES = ('surface', 'screen')

    BRUSHSOURCES = [
        ("circleScatter", "Circle Scatter"),
        ("tempStash", "Temp Stash"),
        ("fileLoad", "File Load"),
    ]

    BRUSHMODES = ('add_points', 'edit_override', 'edit_scale', 'xform_handle')

    #EDITEFFECTS = ('Model', 'Scale', 'Sink', 'Twist', 'SurfaceUp')

    EDITEFFECTS = [
        ("doEditScale", "Scale"),
        ("doEditTwist", "Twist"),
        ("doEditSurfaceUp", "SurfaceUp"),
        ("doEditModel", "Model"),
    ]

    HANDLEEFFECTS = [
        ("handle_pos", "Handle Position"),
        ("handle_rot", "Handle Rotation"),
        ("handle_scale", "Handle Scale"),
    ]

    BRUSHOPS = {
        "none": 0,
        "add": 1,
        "remove": 2,
        "relax": 3,
        "smudge": 4,
        "smudge_up": 5,
        "edit": 6,
        "blur": 7,
        "xform": 8,
    }


    def __init__(self, state_name, scene_viewer):
        self.state_name = state_name
        self._scene_viewer = scene_viewer


        # HOUDINI REFERENCES

        self._node = None
        self._rayGeometry = None
        self._hasRayGeoInput = False

        # INTERNAL PARMS
        self._pressed = False
        self._firstPress = True
        self._isSelectionEvent = False
        self._eyedropModeActive = False
        self._quickCloneActive = False
        self._currentPoint = 0
        self._camPivot = hou.Vector3(0, 0, 0)
        self._orientBrushToCam = 0
        self._lastBrushMode = 0

        #self._lastModel = 0
        self._lastPlacedPos = hou.Vector3(0, 0, 0)
        self._lastPosValid = False
        self._mouseActive = False
        self._lastMouseX = 0
        self._lastMouseY = 0

        self.LASTBUTTON = -1
        self._currentBrushOp = ''
        self._currentBrushMode = ''
        self._textBrushModeContents = ''
        # self._brushDeltaPosition = 0
        self._sustainedAction = False
        self._ValueSnappingActive = False
        self._brushScreenPosition = 0
        self._mouse_origin = hou.Vector3(0, 0, 0)

        self._singlePointID = -1

        # POINT GUIDE PARMS

        self._brushPosition = hou.Vector3(0, 0, 0)
        self._surfaceN = hou.Vector3(0, 1, 0)
        self._surfaceMix = 0
        self._rot = 0
        self._size = 1
        self._pointScale = 1
        self._model = 0
        self._cursorXform = 0

        # AGENT ATTRIBS

        self._displayNode = None

        # BRUSH VARIABLES THAT READ FROM NODE

        self._useBrush = True

        self._brushShape = 'surface'
        self._brushSize = 1
        self._brushPixelMult = 100
        self._modelcount = 0

        self._rayGroundPlane = True
        self._useStroke = False
        self._orientBrushToSurface = 0
        self._orientSurfaceRandom = 0

        self._scaleRandom = 0
        self._rotRandom = 0
        self._strokeSpacing = 0

        self._useRandModel = False

        #self._enable_add_points = True

        self._handleXform = hou.Handle(self._scene_viewer, "editsop_handle")



    ############################### LIFE CYCLE EVENTS #######################################
    def onEnter(self, kwargs):
        """ Called on node bound states when it starts
        """
        self._node = kwargs["node"]
        state_parms = kwargs["state_parms"]

        self._stasherAllPoints = self._node.node("OUT_ALL_POINTS_EDITED")
        self._stasherStamp = self._node.node("OUT_STAMP_POINTS")
        self._stasherSmartRay = self._node.node("OUT_SMART_RAY_POINTS")

        # print kwargs in the viewer state console if "Debug log" is
        # enabled
        self.log("onEnter=", kwargs)

        # Guide Geometry

        # self._guide = hou.GeometryDrawable(self._scene_viewer, hou.drawableGeometryType.Face, "my_guide", geo)
        #self._guideBrush = hou.SimpleDrawable(self._scene_viewer, hou.drawablePrimitive.Circle, "my_guideBrush")

        if self._node.input(1) is not None:
            if len(self._node.inputGeometry(1).prims()) > 0:
                self._hasRayGeoInput = True

        geo = self._node.node("OUT_GUIDE").geometry()
        self._guideGeo = hou.SimpleDrawable(self._scene_viewer, geo, "my_guidegeo")
        self._guideGeo.setDisplayMode(hou.drawableDisplayMode.CurrentViewportMode)
        self._guideGeo.enable(True)
        self.setGuideGeoVisible(True)

        geobrush = self._node.node("OUT_GUIDE_BRUSH").geometry()
        self._guideBrush = hou.SimpleDrawable(self._scene_viewer, geobrush, "my_guidebrush")
        self._guideBrush.setDisplayMode(hou.drawableDisplayMode.CurrentViewportMode)
        self._guideBrush.enable(True)
        self._guideBrush.show(True)

        self._textBrushMode = hou.TextDrawable(self._scene_viewer, 'textBrushMode')
        self._textBrushMode.show(True)

        self.setNodeParm('brush_source', 0)
        self.setNodeParm('isQuickClone', 0)

        self.initFromNodeParms()
        #self.updateGuideTransform(self._scene_viewer.curViewport())

        self.setNodeParm("isCursorInViewport", 1)

        self._node.removeAllEventCallbacks()
        self._node.addEventCallback((hou.nodeEventType.ParmTupleChanged, ), self.nodeParmChanged)
        #print self._node.eventCallbacks()
        self.updateDisplayNode()
        print self._scene_viewer.pwd()
        print self._scene_viewer.currentNode()
        #state_parms['raygroundplane']['value'] = False


    def initFromNodeParms(self):
        self._rayGroundPlane = self.evalNodeParm("raygroundplane")
        self._useStroke = self.evalNodeParm("usestroke")
        self._orientBrushToSurface = self.evalNodeParm("orientBrushToSurface")
        #self._ValueSnappingActive = self.evalNodeParm("useValueSnapping")

        self._useBrush = self.evalNodeParm('useBrush')

        self._scaleRandom = self.evalNodeParm("pscalerand")
        self._rotRandom = self.evalNodeParm("rotrand")

        self._strokeSpacing = self.evalNodeParm("strokeSpacing")
        self._useRandModel = self.evalNodeParm("modelrand")

        #self._modelcount = self.evalNodeParm("modelcount")
        self.setBrushModelNum(self.evalNodeParm("brush_model"))
        self.updateModelCountFromCollection()

        self._useFirstClickRandom = self.evalNodeParm("useFirstClickRandom")

        self._brushShape = self.evalNodeParm("brush_shape")
        self._brushPixelMult = self.evalNodeParm("mouse_pixelMult")

        self.updateBrushShape()
        self.setBrushMode(self.BRUSHMODES[self.evalNodeParm('brush_mode')])

        #self.setBrushPoint(hou.Vector3(0, 0, 0))
        self.setBrushRot(self.evalNodeParm("brush_rot"))

        self.setBrushSize(self.evalNodeParm("brush_rad"))
        self._pointScale = self.evalNodeParm("pscaleBase")

        self._orientBrushToCam = self.evalNodeParm("brush_orientMode")
        self._brushPosition = self.getNodeParmTuple('brush_position')
        self.updateViewTransformParm()

    def resetBrushParms(self):
        self.setBrushPoint(hou.Vector3(0, 0, 0))
        self.setBrushRot(0)
        self.setBrushModelNum(0)
        self.setBrushSize(1)


    def onDraw( self, kwargs ):
        # draw the text in the viewport upper left
        handle = kwargs['draw_handle']

        (x, y, width, height) = self._scene_viewer.curViewport().size()
        margin = 20
        params = {
            'text': self._textBrushModeContents,
            'multi_line': True,
            'color1': hou.Color(1.0, 1.0, 1.0),
            'translate': hou.Vector3(0, height, 0),
            'origin': hou.drawableTextOrigin.UpperLeft,
            'scale': hou.Vector3(1, 1, 1),
            'margins': hou.Vector2(margin, -margin)}

        self._textBrushMode.draw( handle, params)

    def updateTextBrushModeContents(self):
        self.log('update text')
        self._textBrushModeContents = 'ex v00.05 <br> <br>'
        if self._currentBrushMode == 'add_points':
            self._textBrushModeContents += ("ADD POINTS:<br> <br>"
                                          "LMB: Add Points <br>"
                                          "MMB: Relax Positions <br>"
                                          "Wheel: Change Point Density or Model <br> <br>"
                                          "Shift+LMB: Brush Size <br>"
                                          "Shift+MMB: Brush Falloff <br>"
                                          "Shift+Wheel: Brush Strength <br>"
                                          "Shift+Ctrl+Wheel: Change Model Collection <br> <br>"
                                          "Ctrl+LMB: Remove Points <br>"
                                          "Ctrl+MMB: Smudge Positions <br>"
                                          "Ctrl+Wheel: None <br>")

        elif self._currentBrushMode == 'edit_override':
            self._textBrushModeContents += ("OVERRIDE:<br> <br>"
                                          "LMB: Override Attributes <br>"
                                          "MMB: Relax Positions <br>"
                                          "Wheel: None <br> <br>"
                                          "Shift+LMB: Brush Size <br>"
                                          "Shift+MMB: Brush Falloff <br>"
                                          "Shift+Wheel: Brush Strength <br> <br>"
                                          "Ctrl+LMB: Remove Points <br>"
                                          "Ctrl+MMB: Smudge Positions <br>"
                                          "Ctrl+Wheel: None <br>")

        elif self._currentBrushMode == 'edit_scale':
            self._textBrushModeContents += ("MODIFY:<br> <br>"
                                          "LMB: Smudge Attribute <br>"
                                          "MMB: Blur or Randomize Attrib <br>"
                                          "Wheel: None <br> <br>"
                                          "Shift+LMB: Brush Size <br>"
                                          "Shift+MMB: Brush Falloff <br>"
                                          "Shift+Wheel: Brush Strength <br> <br>"
                                          "Ctrl+LMB: Smudge Up <br>"
                                          "Ctrl+MMB: Smudge Positions <br>"
                                          "Ctrl+Wheel: None <br>")

        elif self._currentBrushMode == 'xform_handle':
            self._textBrushModeContents += ("XFORM HANDLE:<br> <br>"
                                          "SAME OPTIONS AS A TRANSFORM NODE <br>" 
                                          "T: Translate Handle <br>"
                                          "R: Rotate Handle <br>"
                                          "E: Scale Handle <br> <br>"
                                          "M: Cycle Handle Alignment <br>"
                                          'Insert : Toggle Move Pivot Mode <br>')


    def nodeParmChanged(self, node, event_type, **kwargs):

        # AGENT PARM CHANGES
        if kwargs['parm_tuple'] == None:
            return
        parmname = kwargs['parm_tuple'].name()
        #if parmname in ["clipTimeOffset", "clipName", "agentName", "costumeName"]:
        #    print kwargs['parm_tuple']

        if parmname == "agentName":
            if self.evalNodeParm(parmname) != '':
                self.setNodeParm("agentNameChanged", 1, True)

        if parmname == "costumeName":
            if self.evalNodeParm(parmname) != '':
                self.setNodeParm("costumeNameChanged", 1, True)

        if parmname == "clipName":
            if self.evalNodeParm(parmname) != '':
                self.setNodeParm("clipNameChanged", 1, True)

        if parmname == "clipTimeOffset":
            if self.evalNodeParm(parmname) != 0:
                self.setNodeParm("clipTimeOffsetChanged", 1, True)

        if parmname == "vignetteName":
            if self.evalNodeParm(parmname) != '':
                self.setNodeParm("vignetteNameChanged", 1, True)


    def nodeEventRemoved(self):
        print "REMOVED EVENT CALLBACK"

    def tryStampAgentAttribs(self):
        #print "try stamp agents"
        doStamp = False
        if self.evalNodeParm("agentNameChanged") == 1:
            doStamp = True
        if self.evalNodeParm("costumeNameChanged") == 1:
            doStamp = True
        if self.evalNodeParm("clipNameChanged") == 1:
            doStamp = True
        if self.evalNodeParm("clipTimeOffsetChanged") == 1:
            doStamp = True
        if self.evalNodeParm("vignetteNameChanged") == 1:
            doStamp = True

        if doStamp:
            self.stashAllPoints()
            print "stamp agent attribs"
            self.clearAgentParms()

    def clearAgentParms(self):
        self.setNodeParm("agentName", "", False)
        self.setNodeParm("costumeName", "", False)
        self.setNodeParm("clipName", "", False)
        self.setNodeParm("clipTimeOffset", "0", False)
        self.setNodeParm("vignetteName", "", False)

        self.setNodeParm("agentNameChanged", 0)
        self.setNodeParm("costumeNameChanged", 0)
        self.setNodeParm("clipNameChanged", 0)
        self.setNodeParm("clipTimeOffsetChanged", 0)
        self.setNodeParm("vignetteNameChanged", 0)

    def onExit(self, kwargs):
        """ Called when the state terminates
        """
        state_parms = kwargs["state_parms"]
        self._node.removeAllEventCallbacks()
        self.tryStampAgentAttribs()
        #self._node.removeEventCallback([hou.nodeEventType.ParmTupleChanged], self.nodeEventRemoved())
        self.setNodeParm("isCursorInViewport", 0)

    def onInterrupt(self, kwargs):
        """ Called when the state is interrupted e.g when the mouse moves outside the viewport
        """
        if self._mouseActive == False:
            self.setGuideGeoVisible(False)
            self._guideBrush.show(False)

        self.tryStampXformChange()
        self.setNodeParm("isCursorInViewport", 0)


    def onResume(self, kwargs):
        """ Called when an interrupted state resumes
        """
        self.setNodeParm("isCursorInViewport", 1)
        self.setGuideGeoVisible(True)
        self._guideBrush.show(True)

        # Init the settings parms as they may have changed
        self.initFromNodeParms()
        self.updateViewTransformParm()
        self.tryStampAgentAttribs()
        self.updateDisplayNode()
        self.log("Resume")


    def setGuideGeoVisible(self, show):
        if self._currentBrushMode == 'add_points' and show == True and self._lastPosValid:
            self._guideGeo.show(True)
        else:
            self._guideGeo.show(False)

    def updateViewTransformParm(self):
        viewXF = self._scene_viewer.curViewport().viewTransform()
        res = self._scene_viewer.curViewport().resolutionInPixels()
        self.setNodeParmTuple("testxf", viewXF.asTuple())

        rotation = viewXF.extractRotates()
        translation = viewXF.extractTranslates()

        self._camPivot = translation
        self.setNodeParmTuple("cam_pivot", tuple(translation))
        self.setNodeParmTuple("cam_rot", tuple(rotation))
        self.setNodeParmTuple("screenRes", hou.Vector3(res[0], res[1], 0))

    def updateGuideTransform(self, viewport):
        # parent = ancestorObject(kwargs["node"])
        # parent_xform = parent.worldTransform()
        xform = hou.Matrix4(1)
        #self.log('brushShape', self._brushShape)

        if self._brushShape == 0:   ### surface:
            xform = self.getBrushSurfaceXform()
        elif self._brushShape == 1:   ### screen:
            xform = self.getBrushScreenXform(viewport)

        self._cursorXform = xform
        self.setBrushXform(xform)

        ### TMP Force guide geo to update
        geo = self._node.node("OUT_GUIDE").geometry()
        self._guideGeo.setGeometry(geo)
        

        self._scene_viewer.curViewport().draw()


    def setBrushXform(self, xform):
        # self._guide.setTransform(xform)
        #self._guidefalloff.setTransform(xform)
        self._guideBrush.setTransform(xform)
        xf = self._guideBrush.transform()
        #self.setNodeParmTuple("testxf", xf.asTuple())


    def getBrushSurfaceXform(self):
        up = hou.Vector3(0, 1, 0)
        identQ = hou.Quaternion()
        surfaceQ = hou.Quaternion()

        if self._orientBrushToCam == 1:
            camdir = (self._camPivot - hou.Vector3(self._brushPosition)).normalized()
            identQ.setToVectors(up, camdir)

        xform = hou.hmath.buildScale(hou.Vector3(1, 1, 1))
        xform *= hou.hmath.buildRotateAboutAxis(hou.Vector3(1, 0, 0), 90)

        world_pos = self._brushPosition
        m = hou.hmath.buildScale(hou.Vector3(1, 1, 1) * self._brushSize)
        rotm = hou.hmath.buildRotateAboutAxis(up, self._rot * 360)
        surfaceQ.setToVectors(up, self._surfaceN)
        surfaceQblend = identQ.slerp(surfaceQ, self._surfaceMix)

        rotm *= hou.Matrix4(surfaceQblend.extractRotationMatrix3())
        m *= rotm
        m *= hou.hmath.buildTranslate(world_pos)

        # self.log("surfaceQ= ", surfaceQ)
        # self.log("self._surfaceMix= ", self._surfaceMix)
        # self._guideGeo.setTransform(m)

        xform *= m
        return xform


    def getBrushScreenXform(self, viewport):
        vp = viewport

        self.model_xform = vp.windowToViewportTransform() * vp.viewportToNDCTransform() * vp.ndcToCameraTransform() * vp.cameraToModelTransform()
        self.mouse_xform = self.model_xform# * vp.modelToGeometryTransform()

        self.mouse_xform = self.mouse_xform.inverted()
        self.setNodeParmTuple("brushscreenxform", self.mouse_xform.asTuple())


        center = hou.Vector4(self._mouse_origin)
        center *= self.mouse_xform
        center /= center.w()
        # We want it offset to avoid falling over the clipping plane.
        center[2] = -0.999

        rotate = (0, 0, self._rot * 360)
        scale = self._brushPixelMult * self._brushSize

        srt = {
            'translate': (center[0], center[1], center[2]),
            'scale': (scale, -scale, scale),
            'rotate': rotate
        }

        xform = hou.hmath.buildTransform(srt)
        return xform * self.model_xform


    def onParmChangeEvent(self, kwargs):
        parm_name = kwargs['parm_name']
        parm_value = kwargs['parm_value']
        state_parms = kwargs['state_parms']

        # if parm_name == 'raygroundplane':

        #self.log("parm_name= ", parm_name)
        #self.log("parm_value= ", parm_value)



    ###################################### SELECTION EVENTS ###########################################################
    def onStopSelection(self, kwargs):
        """ Called when a bound selector has been terminated
        """
        selector_name = kwargs["name"]
        self.log(selector_name + " has stopped")

    def onSelection(self, kwargs):
        """ Called when a selector has selected something
        """
        selection = kwargs["selection"]
        sel_name = kwargs["name"]
        self.log(sel_name)
        self.log(".selections()= ", selection.selections())
        #self.log(".selectionstring = ", selection.mergedSelectionString())

        with hou.undos.group('brush: Edit Selection Mask'):
            self.setIsSelectionEvent(True)
            self.setNodeParm('maskgroup', selection.mergedSelectionString(), True)
            self.clearAgentParms()

        self.tryStampXformChange()


        # Must return True to accept the selection
        return False

    def onStartSelection(self, kwargs):
        """ Called when a bound selector has been started
        """
        selector_name = kwargs["name"]
        self.log(selector_name + " has started")
        #self._displayNode = self._scene_viewer.pwd().displayNode()
        #self._node.setDisplayFlag(True)
        #print self._node.isDisplayFlagSet()
        #print self._displayNode

    def onStopSelection(self, kwargs):
        #self._displayNode.setDisplayFlag(1)
        pass

    ################################## DEVICE EVENTS ##################################################################
    def onMouseEvent(self, kwargs):
        """ Process mouse events
        """
        ui_event = kwargs["ui_event"]
        if self._node is None:
            self._node = kwargs["node"]

        device = ui_event.device()
        vp = ui_event.curViewport()

        MOUSEUP = ui_event.reason() == hou.uiEventReason.Changed
        MOUSEDOWN = ui_event.reason() == hou.uiEventReason.Start
        PICKED = ui_event.reason() == hou.uiEventReason.Picked
        DRAGGING = ui_event.reason() == hou.uiEventReason.Active
        MOVED = ui_event.reason() == hou.uiEventReason.Located

        SHIFT = device.isShiftKey()
        CTRL = device.isCtrlKey()

        LEFT_BUTTON = device.isLeftButton()
        MIDDLE_BUTTON = device.isMiddleButton()
        RIGHT_BUTTON = device.isRightButton()

        MOUSEX = device.mouseX()
        MOUSEY = device.mouseY()

        SCREEN = self._brushShape == 1 ### Screen

        if self._currentBrushMode == 'xform_handle':
            self.setBrushOp('xform')
            return


        ### Get valid intersection point of mouse ray
        mouse_origin, mouse_dir = ui_event.ray()
        hitPrim, hitPos, surfaceRay, uvw = self.rayIntersect(mouse_origin, mouse_dir)
        validPos = not (self._rayGroundPlane == False and hitPrim < 0) or SCREEN
        self.setValidPos(validPos)

        if self._mouseActive == False:
            # store the surface normal under the mouse
            self._surfaceN = self.getPrimNormalAtLocation(hitPrim, uvw)
            self.setNodeParmTuple("mouse_point", mouse_origin)
            self.setNodeParmTuple("mouse_dir", mouse_dir)



        #self.log("valid", validPos)
        #self.log("reason", ui_event.reason())
        #self.log("mode: ", self._currentBrushOp)

        #self.log(ui_event.curViewport().defaultCamera().translation())
        #self.setNodeParmTuple("cam_pivot", hou.Vector3(ui_event.curViewport().defaultCamera().translation()))
        #xform *= ui_event.curViewport().viewTransform()
        #self.setNodeParmTuple("brushscreenxform", xform.asTuple())

        #return



        ### PICKED executes on mouseup when we click fast.
        ### It blocks MOUSEDOWN and MOUSEUP events, so we have to remember the state of past things
        if PICKED:
            if self.LASTBUTTON == 0:
                LEFT_BUTTON = 1
            elif self.LASTBUTTON == 1:
                MIDDLE_BUTTON = 1

        ### Hide Guides when not over valid geo
        if not validPos:
            if self._mouseActive == False:
                self.setGuideGeoVisible(False)
            if not SCREEN:
                self._guideBrush.show(False)
        elif self._eyedropModeActive == False:
            self.setGuideGeoVisible(True)
            self._guideBrush.show(True)


        ### Eyedrop Mode and QuickClone Start
        if self._eyedropModeActive == True:

            self.setBrushOp('none')

            if self._quickCloneActive == False:
                if self._useBrush == False:
                    self.getPrimUnderMouse(MOUSEX, MOUSEY)

                self.updateGuideTransform(vp)
                self.setBrushPoint(hitPos)
                self.setBrushScreenPosition(mouse_origin, MOUSEX, MOUSEY)

            if LEFT_BUTTON:
                self.eyeDropSelectedToBrush()
            elif MIDDLE_BUTTON:
                if MOUSEDOWN or PICKED:
                    self.quickCloneMode()
                    #self.log('_eyedropModeActive')
                    # self._eyedropModeActive = False

        ### Handle Everything that isn't sustained
        elif not self._sustainedAction:
            ### Update Brush Display
            if not DRAGGING:
                if CTRL:
                    if self._currentBrushMode == "edit_scale":
                        self.setBrushOp('none')
                    else:
                        self.setBrushOp('remove')
                else:
                    self.setBrushOpAdd()

            ### Update NodeParm to drive sops
            if MOUSEDOWN or PICKED:
                self.setIsMouseDown(True)
            else:
                self.setIsMouseDown(False)
                #self._guidefalloff.show(False)


            ### Brush Edit Mode Stuff
            if SHIFT:
                self.setBrushOpAdd()
                self.setIsMouseDown(False)
                # self.log("shift")

                if MIDDLE_BUTTON:
                    self.setBrushOp('none')
                    if PICKED:
                        # Increase presses to reseed randoms in sops
                        self.incrementPressCount()
                        #self.log("Middle picked")
                    elif MOUSEDOWN:
                        pass
                        #self.updateGuideTransform(vp)
                        #self._guidefalloff.show(True)
                        #self.log("Middle down")
                        self._lastMouseX = MOUSEX
                        self._lastMouseY = MOUSEY

                    elif DRAGGING:
                        if CTRL:
                            #self.log("Middle shift ctrl drag")
                            self.incMouseBrushStrength(MOUSEX)
                        else:
                            #self.log("Middle shift drag")
                            self.incMouseBrushFalloff(MOUSEX)
                            #self.incMouseBrushStrength(MOUSEY)

                elif self._mouseActive == False:
                    self._lastMouseX = MOUSEX
                    self._lastMouseY = MOUSEY
                    self._mouseActive = True
                else:
                    if LEFT_BUTTON:
                        #self.scaleBrush(MOUSEX)
                        if CTRL:
                            self.scalePointScale(MOUSEX)
                        else:
                            self.scaleBrushSize(MOUSEX)
                            self.updateGuideTransform(vp)

                        if PICKED:
                            #self.setBrushOpAdd()
                            self.setIsMouseDown(True)
                            self.stampAddBrush()
                            self.setIsMouseDown(False)
                    else:
                        self.rotateBrush(MOUSEX)
                        self.updateGuideTransform(vp)

            ### When not in Brush Edit Mode, check for presses
            elif LEFT_BUTTON or MIDDLE_BUTTON:

                if MIDDLE_BUTTON and DRAGGING and not CTRL:
                    self.setBrushOp('relax')

                # TODO currently not showing correct action as undo. Possible move startPress and stamping to end.
                self.startPress()

                ### Hide the Guide when the cursor is NOT over ray geo and ray ground plane is off
                #self.setBrushPoint(hitPos)
                self.updateBrushSurfaceOrient()
                self.updateGuideTransform(vp)

                if validPos:
                    validSpacing = True
                    inStroke = DRAGGING and self._useStroke == True
                    SINGLECLICK = MOUSEDOWN or PICKED

                    # set spacing attribs for SURFACE or SCREEN brush
                    brushpos = hitPos
                    spacing = self._strokeSpacing
                    if SCREEN:
                        brushpos = hou.Vector3(MOUSEX, MOUSEY, 0)
                        spacing *= self._brushPixelMult

                    # Always place first click, else place if distance is greater than stroke spacing
                    if SINGLECLICK:
                        self._lastPlacedPos = brushpos
                        self.setBrushDeltaPosition(hitPos)
                        self.setBrushDeltaScreenPosition(MOUSEX, MOUSEY)
                    elif inStroke:
                        validSpacing = brushpos.distanceTo(self._lastPlacedPos) > spacing
                        if self._firstPress:
                            self.setIsFirstPress(False)

                    if MOUSEDOWN and self._currentBrushMode == 'add_points' and self._useStroke == False:
                        self._sustainedAction = True

                    elif inStroke or SINGLECLICK:
                        if self._useBrush == False:
                            #self.log('single drag')
                            #self.getPrimUnderMouse(MOUSEX, MOUSEY)
                            pass

                        self.setBrushPoint(hitPos)
                        self.setBrushScreenPosition(mouse_origin, MOUSEX, MOUSEY)

                        if validSpacing:
                            #self.log("validSpacing: ", validSpacing)
                            self.setIsMouseDown(True)

                            if LEFT_BUTTON:
                                if CTRL:
                                    if self._currentBrushMode == "edit_scale":
                                        self.setBrushOp('smudge_up')
                                        self._sustainedAction = True
                                        self.setBrushDeltaPosition(hitPos)
                                        self.setBrushDeltaScreenPosition(MOUSEX, MOUSEY)
                                    else:
                                        self.stampEditBrush()

                                else:
                                    #self.setBrushOp('add')
                                    if self._currentBrushMode == 'edit_scale':
                                        self.setBrushOp('edit')
                                        self.setBrushIsSubtract(False)
                                        self._sustainedAction = True
                                        self.setBrushDeltaPosition(hitPos)
                                        self.setBrushDeltaScreenPosition(MOUSEX, MOUSEY)
                                    elif self._currentBrushMode == "edit_override":
                                        self.setBrushOp('edit')
                                        self.stampEditBrush()
                                    else:
                                        self.stampAddBrush()


                            elif MIDDLE_BUTTON:
                                if CTRL:
                                    self.setBrushOp('smudge')
                                    self._sustainedAction = True
                                    self.setBrushDeltaPosition(hitPos)
                                    self.setBrushDeltaScreenPosition(MOUSEX, MOUSEY)
                                else:
                                    if self._currentBrushMode == 'edit_scale':
                                        #self.setBrushIsSubtract(True)
                                        #self.setBrushOp('edit')
                                        self.setBrushOp('blur')
                                        self._sustainedAction = True
                                        self.setBrushDeltaPosition(hitPos)
                                        self.setBrushDeltaScreenPosition(MOUSEX, MOUSEY)
                                        #self.stampEditBrush()
                                    else:
                                        self.setBrushOp('relax')
                                        self.stampEditBrush()

                            self._lastPlacedPos = brushpos
                            self.incrementPressCount()
                            self.setIsMouseDown(False)

            ### When not pressing buttons just end actions and update guides
            else:
                self._mouseActive = False
                self.finishPress()

                self.setBrushPoint(hitPos)
                self.setBrushScreenPosition(mouse_origin, MOUSEX, MOUSEY)
                self.updateBrushSurfaceOrient()
                self.updateGuideTransform(vp)

                if self._currentBrushMode == 'edit_scale':
                    self.setBrushIsSubtract(False)

                if self._useBrush == False:
                    self.getPrimUnderMouse(MOUSEX, MOUSEY)


        ### Handle a sustained action like smudge
        if self._sustainedAction == True:
            #self.log("Sustained Action")

            # Cancel Action (Doesn't register Rclick here. Rclick is a messy button)
            #if RIGHT_BUTTON:
            #    self.log("CANCELLED")
            #    self._sustainedAction = False
            #    self.finishPress()
            #    self.setBrushOp('none')


            ### Update the Delta Position of the surface and screen brush
            if validPos:
                self.setBrushDeltaPosition(hitPos)
            self.setBrushDeltaScreenPosition(MOUSEX, MOUSEY)

            ### Keep track of CTRL for snapping. Trying to minimize parm sets here
            if CTRL:
                if self._ValueSnappingActive == False:
                    self._ValueSnappingActive = True
                    self.setNodeParm("useValueSnapping", True)
            else:
                if self._ValueSnappingActive == True:
                    self._ValueSnappingActive = False
                    self.setNodeParm("useValueSnapping", False)

            ### End the sustained action
            if MOUSEUP or PICKED:
                self.log("FREEZE")
                self.setIsMouseDown(True)

                if self._quickCloneActive == True:
                    with hou.undos.group('brush: Quick Clone'):
                        self.setBrushOpAdd()
                        self.stampAddBrush()
                    self._quickCloneActive = False
                    self.setNodeParm('isQuickClone', False)

                else:
                    self.stampEditBrush()

                self.setIsMouseDown(False)
                self.incrementPressCount()
                self._sustainedAction = False
                self.finishPress()
                self.setBrushOp('none')


        ### Remember last button press to fix PICKED
        if LEFT_BUTTON:
            self.LASTBUTTON = 0
        elif MIDDLE_BUTTON:
            self.LASTBUTTON = 1

        return False


    def startPress(self):
        # Start Undo State
        if not self._pressed:
            self._scene_viewer.beginStateUndo("brush: " + self._currentBrushOp)
        self._pressed = True


    def finishPress(self):
        # End Undo State
        if self._pressed:
            self._scene_viewer.endStateUndo()
        self._pressed = False

        self.setIsFirstPress(True)


    def onMouseWheelEvent(self, kwargs):
        """ Process a mouse wheel event
        """
        ui_event = kwargs["ui_event"]
        state_parms = kwargs["state_parms"]
        vp = ui_event.curViewport()
        #self.log("reason:", ui_event.reason())

        device = kwargs["ui_event"].device()
        scroll = device.mouseWheel()

        SHIFT = device.isShiftKey()
        CTRL = device.isCtrlKey()

        if SHIFT:
            #self.incrementBrushSize(scroll)
            if CTRL:
                self.incrementActiveCollection(scroll)
            else:
                self.incrementBrushStrength(scroll)
                self.updateGuideTransform(vp)
        else:
            if self._currentBrushMode == 'add_points':
                if self._useBrush:
                    self.incrementBrushDensity(scroll)
                else:
                    self.incrementBrushModelNum(scroll)


        return False


    def onKeyEvent(self, kwargs):
        """ Called for processing a keyboard event
        """
        ui_event = kwargs['ui_event']

        # Log some key event info in the Viewer State Browser console
        #self.log('key string', ui_event.device().keyString())
        #self.log('key value', ui_event.device().keyValue())
        #self.log('isAutoRepeat', ui_event.device().isAutoRepeat())

        '''
        # Use the key string to decide if the event should be consumed or not.
        # Store the pressed key for use in other handlers.
        self.key_pressed = ui_event.device().keyString()
        if self.key_pressed in ('a', 'shift a', 'ctrl g'):
            # returns True to consume the event
            return True

        # Consume the event only if the 'f', 'p' or 'v' key is held
        if ui_event.device().isAutoRepeat():
            ascii_key = ui_event.device().keyValue()
            if ascii_key in (102, 112, 118):
                self.key_pressed = ui_event.device().keyString()
                return True

        self.key_pressed = None
        '''

        # return False if the event is not consumed
        return False


    def onKeyTransitEvent(self, kwargs):
        """ Called for processing a transitory key event
        """
        ui_event = kwargs["ui_event"]
        state_parms = kwargs["state_parms"]

        # Log the key state
        #self.log('key', ui_event.device().keyString())
        #self.log('key up', ui_event.device().isKeyUp())
        #self.log('key down', ui_event.device().isKeyDown())

        if ui_event.device().keyString() == 'a':
            #self.log('key', ui_event.device().keyString())
            if ui_event.device().isKeyDown():
                self._eyedropModeActive = True
                self._scene_viewer.setPromptMessage('EYEDROPPER: LMB on asset to copy attribs')
                self.setGuideGeoVisible(False)
                #self.scene_viewer.selectGeometry(prompt="Select a Prim or Point to Copy", quick_select=True, use_existing_selection=False)

            elif ui_event.device().isKeyUp():
                self._eyedropModeActive = False
                self._scene_viewer.clearPromptMessage()
                self.setGuideGeoVisible(True)

        if ui_event.device().keyString() == 'shift+s':
            self.log('invert selection')
            self.setInvertSelection(not self.evalNodeParm('useInvertMask'))


        # return True to consume the key transition
        if ui_event.device().isKeyDown():
            return True

        return False

    ###################################### HANDLES #################################################################


    def onHandleToState(self, kwargs):

        # NOT USED. DOESN'T WORK WITH STATIC HANDLE
        # Called when the user manipulates a handle
        self.log("HERE")
        handle_name = kwargs["handle"]
        parms = kwargs["parms"]
        prev_parms = kwargs["prev_parms"]

        print("User edited handle:", handle_name)
        for parm_name in kwargs["mod_parms"]:
            old_value = prev_parms[parm_name]
            new_value = parms[parm_name]
            print("%s was: %s now: %s" % (parm_name, old_value, new_value))

    def onStateToHandle(self, kwargs):

        # NOT USED. DOESN'T WORK WITH STATIC HANDLE
        # Called when the user changes parameter(s), so you can update
        # dynamic handles if necessary
        self.log("HERE")
        parms = kwargs["parms"]
        print("Parameters are now:", parms)
        for p in parms:
            print(p)

    ###################################### PARM CALLS #################################################################



    def evalNodeParm(self, parmname):
        return self._node.parm(parmname).eval()

    def setNodeParm(self, parmname, value, undo=False, undoname=''):
        if undo:
            if undoname != '':
                with hou.undos.group('brush: ' + undoname):
                    self._node.parm(parmname).set(value)
            else:
                self._node.parm(parmname).set(value)
        else:
            with hou.undos.disabler():
                self._node.parm(parmname).set(value)

    def getNodeParmTuple(self, parmname):
        return self._node.parmTuple(parmname).eval()

    def setNodeParmTuple(self, parmname, value, undo=False):
        if undo:
            self._node.parmTuple(parmname).set(value)
        else:
            with hou.undos.disabler():
                self._node.parmTuple(parmname).set(value)

    def incrementNodeParm(self, parmname, increment):
        value = self.evalNodeParm(parmname)
        value = self.evalNodeParm(parmname)
        self.setNodeParm(parmname, value + increment)

    def resetNodeParm(self, parmname):
        self._node.parm(parmname).resetToDefaults()


    ###################################### BRUSH #################################################################

    def rotateBrush(self, mouseX):
        newrot = self._rot + self.getMouseDeltaX(mouseX) * 0.002
        self.setBrushRot(newrot)

    def stampAddBrush(self):
        self.stashAllPoints()
        self._currentPoint += 1
        self.setStampNumber()
        self.log(self._currentBrushOp)

        if self._isSelectionEvent:
            self.setIsSelectionEvent(False)

    def stampEditBrush(self):
        #if self._currentBrushOp == none:
        #    return
        self.stashAllPoints()
        self.log(self._currentBrushOp)

        if self._isSelectionEvent:
            self.setIsSelectionEvent(False)

    def stashAllPoints(self):
        stashPoints = self._stasherAllPoints.geometry().freeze(True, True)
        self.setNodeParm('stash_all_points', stashPoints, True, "brush: Stash All")


    def stashSelectedToStamp(self):
        stashPoints = self._stasherStamp.geometry().freeze(True, True)
        self.setNodeParm('stash_stamp_points', stashPoints, True, "brush: New Stamp From Selection")
        self.setBrushMode('add_points')
        self.setNodeParm('brush_source', 1)
        self.setBrushSize(1)
        self.setBrushRot(0)
        self.setPointScale(1)

    def clearAllPointsStash(self):
        self.resetNodeParm('stash_all_points')

    def setIsFirstPress(self, isfirst):
        self._firstPress = isfirst
        self.setNodeParm('isfirstpress', isfirst)

    def setStampNumber(self):
        self.setNodeParm('stampnumber', self._currentPoint)

    def setBrushDeltaPosition(self, position):
        #self._brushDeltaPosition = position
        self.setNodeParmTuple('brush_position_delta', position)

    def setBrushDeltaScreenPosition(self, mouseX, mouseY):
        #self._brushDeltaPosition = position
        self.setNodeParmTuple('brush_screen_delta', (mouseX, mouseY, 0))

    def setBrushPoint(self, position):
        self._brushPosition = hou.Vector3(position)
        self.setNodeParmTuple('brush_position', position)

    def setBrushScreenPosition(self, mouse_origin, mouseX, mouseY):
        self._brushScreenPosition = (mouseX, mouseY, 0)
        self._mouse_origin = mouse_origin
        self.setNodeParmTuple("mouse_screenP", (mouseX, mouseY, 0))

    def setBrushRot(self, rot):
        self._rot = rot
        self.setNodeParm('brush_rot', rot)

    def updateBrushSurfaceOrient(self):
        self._surfaceMix = self._orientBrushToSurface
        self.setNodeParmTuple('brush_surfaceN', self._surfaceN)
        self.setNodeParm('brush_surfaceMix', self._surfaceMix)

    def setBrushModelNum(self, index):
        self._model = index
        self.setNodeParm('brush_model', index)

    def incrementBrushModelNum(self, increment):
        num = self.evalNodeParm('brush_model')
        num += increment
        num = int(self.clampModelNum(num))
        self.setBrushModelNum(num)

    def clampModelNum(self, num):
        max = self._modelcount
        num = int(hou.hmath.wrap(num, 0, max))
        return num

    def updateModelCountFromCollection(self):
        count = self._node.node('OUT_ActiveCollection').geometry().intAttribValue('modelCount')
        self.setNodeParm('modelcount', count)
        self._modelcount = count
        self.setBrushModelNum(self.clampModelNum(self._model))
        #self.log('self._model: ', str(self._model))

    def incrementActiveCollection(self, increment):

        colCount = self._node.node('OUT_ActiveCollection').geometry().intAttribValue('collectionCount')
        activeCol = self.evalNodeParm('activeCollection')
        activeCol = int(hou.hmath.wrap(activeCol + increment, 0, colCount))
        self.setNodeParm('activeCollection', activeCol)
        self.updateModelCountFromCollection()
        self.log('activeCol: ', str(activeCol))

    def incrementBrushSize(self, increment):
        size = self.evalNodeParm('brush_rad')
        size *= (1 + increment * 0.1)
        self.setBrushSize(size)

    def scaleBrushSize(self, mouseX):
        # self.log("_scaleBrush")
        newscale = self._brushSize * (1 + self.getMouseDeltaX(mouseX) * 0.01)
        self._brushSize = newscale
        self.setBrushSize(newscale)

    def setBrushSize(self, size):
        size = hou.hmath.clamp(size, 0.01, 10000000)
        self._brushSize = size
        self.setNodeParm('brush_rad', size)

    def setPointScale(self, scale):
        scale = hou.hmath.clamp(scale, 0.01, 10000000)
        self._pointScale = scale
        self.setNodeParm('pscaleBase', scale)
        #self.setNodeParm('pscaleBase', scale)

    def scalePointScale(self, mouseX):
        newscale = self._pointScale * (1 + self.getMouseDeltaX(mouseX) * 0.01)
        self.setPointScale(newscale)

    def incrementBrushDensity(self, increment):
        #self.log("incrementBrushDensity:")
        density = self.evalNodeParm('brush_density')
        density += increment * hou.hmath.fit(density, 0.5, 100, 0.25, 5)
        self.setBrushDensity(density)

    def setBrushDensity(self, density):
        density = hou.hmath.clamp(density, 0.01, 100)
        self.setNodeParm('brush_density', density)

    def incMouseBrushFalloff(self, mouseX):
        value = self.evalNodeParm('brush_falloff')
        value += self.getMouseDeltaX(mouseX) * -0.01
        value = hou.hmath.clamp(value, 0, 1)
        self.setNodeParm('brush_falloff', value)

    def incrementBrushStrength(self, increment):
        value = self.evalNodeParm('brush_strength')
        value += increment * 0.1
        value = hou.hmath.clamp(value, 0, 1)
        self.setNodeParm('brush_strength', value)

    def incMouseBrushStrength(self, mouseX):
        value = self.evalNodeParm('brush_strength')
        value += self.getMouseDeltaX(mouseX) * 0.01
        value = hou.hmath.clamp(value, 0, 1)
        self.setNodeParm('brush_strength', value)

    def setValidPos(self, isValid):
        self.setNodeParm('validPos', isValid)
        self._lastPosValid = isValid

    def setBrushOp(self, opname):
        value = CrowdBrush.BRUSHOPS[opname]
        if self._currentBrushOp != opname:
            self.setNodeParm('brush_op', value)
        self._currentBrushOp = opname

    def setBrushOpAdd(self):
        if self._currentBrushMode == 'add_points':
            self.setBrushOp('add')
        else:
            self.setBrushOp('none')

    def setBrushMode(self, modename):
        old = self._currentBrushMode
        self._lastBrushMode = old

        if old == 'xform_handle' and modename != old:
            self.tryStampXformChange()

        self._currentBrushMode = modename
        if modename == 'xform_handle':
            self._guideBrush.show(False)
            self.resetXformHandlePivot()
            self._handleXform.show(True)
        else:
            self._handleXform.show(False)
            self._guideBrush.show(True)


        self.setGuideGeoVisible(True)

        if modename != old:
            self.updateTextBrushModeContents()

        self.setNodeParm('brush_mode', self._currentBrushMode)

    def setBrushIsSubtract(self, state):
        self.setNodeParm('isBrushSubtract', state)

    def updateBrushShape(self):
        self._brushShape = self.evalNodeParm('brush_shape')
        self.updateGuideTransform(self._scene_viewer.curViewport())

    def quickCloneMode(self):
        self.log('start QUICK CLONE')
        self.setBrushMode('add_points')
        self._sustainedAction = True
        self._quickCloneActive = True
        self.setNodeParm('isQuickClone', True)

    def eyeDropSelectedToBrush(self):
        self.log('try eyedrop!')
        if self._singlePointID != -1:
            point = self._node.node("OUT_EyeDrop").geometry().point(0)

            if point != None:
                pscale = point.attribValue('pscale')
                sink = point.attribValue('sink') / pscale
                scalecomp = point.attribValue('scalecomp')
                pscale *= scalecomp
                modelnum = point.attribValue('modelnum')

                self.setBrushSize(pscale)
                self.setPointScale(1)
                self.setNodeParm('sinkBase', sink)
                self.setBrushModelNum(modelnum)

                colname = point.stringAttribValue('collection')
                colmenu = self._node.parm('activeCollection').menuLabels()

                if colname in colmenu:
                    idx = colmenu.index(colname)
                    self.setNodeParm('activeCollection', idx)

                self.log('eyedropped collection: ' + str(colname))
                self.log('eyedropped model: ' + str(modelnum))
                self.log('eyedropped pscale: ' + str(pscale))
                self.log('eyedropped sink: ' + str(sink))

                self.setBrushMode('add_points')

        else:
            self.log('no Point')

    def resetXformHandlePivot(self):
        self.log('reset handle')
        centerp = self._node.node("out_handle_center").geometry().point(0)
        if centerp != None:
            pos = centerp.position()
            self.setNodeParmTuple('edt_p', pos)
            rot = centerp.attribValue('rot')
            # Needs fixing. Outside handle doesn't match inside one
            self.setNodeParmTuple('edt_pr', rot)

        zero = hou.Vector3(0, 0, 0)
        self.setNodeParmTuple('edt_t', zero)
        self.setNodeParmTuple('edt_r', zero)
        self.setNodeParmTuple('edt_s', hou.Vector3(1, 1, 1))
        #self.setNodeParmTuple('edt_pr', zero)

    def tryStampXformChange(self):
        if self._currentBrushMode == 'xform_handle':
            self.log('stamp handle')
            self.stampEditBrush()
            self.resetXformHandlePivot()

    def setEditAffected(self, parmname):
        for toggleName, label in CrowdBrush.EDITEFFECTS:
            self.setNodeParm(toggleName, 0)
        self.setNodeParm(parmname, 1)




    ###################################### MOUSE AND OTHER #################################################################


    def getPrimUnderMouse(self, mouseX, mouseY):
        gv = self._scene_viewer.curViewport()
        # self.log(gv.queryInspectedGeometry())
        # pos, normal, test = gv.queryWorldPositionAndNormal(4, 4)
        # node = gv.queryNodeAtPixel(MOUSEX, MOUSEY)

        ### Ideally we would want to override the node below to query the geo of the currently displayed node,
        ### But it does not work on agents if you change it to another node (eg. displayNode), or to None (unrestricted)
        prim = gv.queryPrimAtPixel(None, int(mouseX), int(mouseY))
        if prim != None:
            num = prim.number()

            if num != self._singlePointID:
                self.setNodeParm('grp_single', str(num))
                self._singlePointID = num
                #self.log('num', num)
        else:
            if self._singlePointID != -1:
                self.setNodeParm('grp_single', str(-1))
                self._singlePointID = -1

        # self.log('node', node)
        # self.log('pos', pos)
        # self.log('normal', normal)

    def updateDisplayNode(self):
        self._displayNode = self._scene_viewer.pwd().displayNode()
        #print "Display Node: ", self._displayNode


    def getPrimNormalAtLocation(self, primnum, uvw):
        normal = hou.Vector3(0, 1, 0)
        #self.log('primnum', str(primnum))
        if primnum >= 0:
            prim = self._rayGeometry.prim(primnum)
            # We can read volume N but only if it has an N attribute. So we read a volumegradient in sops
            #if prim.type() != hou.primType.Volume and prim.type() != hou.primType.VDB:
            normaltuple = prim.attribValueAtInterior("N", uvw[0], uvw[1], uvw[2])
            normal = hou.Vector3(normaltuple).normalized()

            if prim.type() == hou.primType.Volume:
                #self.log('vollie')
                normal = -normal
        return normal

    def getMouseDeltaX(self, mouseX):
        delta = mouseX - self._lastMouseX
        self._lastMouseX = mouseX
        return delta

    def getMouseDeltaY(self, mouseY):
        delta = mouseY - self._lastMouseY
        self._lastMouseY = mouseY
        return delta

    def incrementPressCount(self):
        self.incrementNodeParm('pressCount', 1)

    def setIsMouseDown(self, state):
        self.setNodeParm('isMouseDown', state)

    def setIsSelectionEvent(self, state):
        self._isSelectionEvent = state
        self.setNodeParm('isSelectionEvent', state, True)

        if state == False:
            self.setNodeParm('maskgroup', "", True)

    def setInvertSelection(self, state):
        self.setNodeParm('useInvertMask', state, True,  'Invert Selection Mask')

    def clearSelected(self):
        with hou.undos.group('brush: Clear Selected'):
            oldOp = self._currentBrushOp
            self.setBrushOp('remove')
            self.setNodeParm('isKillSelected', True)
            self.stampEditBrush()
            self.setNodeParm('isKillSelected', False)
            self.setBrushOp(oldOp)
            #print self._scene_viewer.currentGeometrySelection()
            #self._scene_viewer.setCurrentGeometrySelection(hou.geometryType.Points, "", "")


    def rayIntersect(self, origin, direction):

        # Find intersection with geometry or ground
        position = (0, 0, 0)
        intersected = -1
        rayToSurface = None
        uvw = None

        # Try cache geometry if node has input
        if self._hasRayGeoInput:
            if self._rayGeometry == None:

                self.log("caching geo")
                self._rayGeometry = self._node.node("OUT_raycast_geo").geometry()
                #if inputs and inputs[1]:
                #   self._rayGeometry = inputs[0].geometry()

            # Try intersect with cached geometry
            else:
                intersected, position, rayToSurface, uvw = stateutils.sopGeometryIntersection(self._rayGeometry, origin, direction)

        # If we didn't hit any geometry, intersect with the ground plane
        if intersected < 0 and self._rayGroundPlane == True:
            position = stateutils.cplaneIntersection(self._scene_viewer, origin, direction)

        return [intersected, position, rayToSurface, uvw]


    ###################################### CONTEXT MENU #################################################################

    def onMenuPreOpen(self, kwargs):
        menu_id = kwargs['menu']
        node = kwargs['node']
        menu_states = kwargs['menu_states']
        menu_item_states = kwargs['menu_item_states']

        #self.log('menu_id', menu_id)
        #self.log('menu_states', menu_states)
        #self.log('menu_item_states', menu_item_states)

        if menu_id == 'select_brush_shape':
            self.updateBrushShape()
            menu_states['value'] = CrowdBrush.BRUSHSHAPES[self._brushShape]

        elif menu_id == 'select_brush_mode':
            menu_states['value'] = self._currentBrushMode


        elif menu_id == 'select_edit_affected':
            active = 'doEditScale'
            for toggleName, label in CrowdBrush.EDITEFFECTS:
                if self.evalNodeParm(toggleName) == True:
                    active = toggleName
            menu_states['value'] = active

        elif menu_id == 'select_brush_source':
            menu_states['value'] = CrowdBrush.BRUSHSOURCES[self.evalNodeParm('brush_source')][0]

        #elif menu_id == 'menu_editAffected':
        #    for toggleName, label in CrowdBrush.EDITEFFECTS:
        #        menu_item_states[toggleName]['value'] = self.evalNodeParm(toggleName)

        elif menu_id == 'brush_menu':
            menu_item_states['toggle_invert_mask']['value'] = self.evalNodeParm('useInvertMask')

            menu_item_states['toggle_select_instances']['value'] = self.evalNodeParm('selectAllModelInstances')

            self._useBrush = self.evalNodeParm('useBrush')
            menu_item_states['toggle_use_brush']['value'] = self._useBrush

            for toggleName, label in CrowdBrush.HANDLEEFFECTS:
                #menu_item_states[toggleName]['enable'] = 0
                menu_item_states[toggleName]['value'] = self.evalNodeParm(toggleName)

    def onMenuAction(self, kwargs):
        menu_item = kwargs['menu_item']
        node = kwargs['node']

        self.setNodeParm('brush_shape', kwargs['select_brush_shape'])
        self.updateBrushShape()

        self.setBrushMode(kwargs['select_brush_mode'])

        self.setNodeParm('brush_source', kwargs['select_brush_source'])

        self.setEditAffected(kwargs['select_edit_affected'])


        if kwargs["menu_item"] == "action_ClearAll":
            with hou.undos.group('brush: Clear All Points'):
                node.parm('clearAll').pressButton()

        if kwargs["menu_item"] == "action_ClearSelected":
            self.clearSelected()

        if kwargs["menu_item"] == "action_StampFromSelected":
            self.stashSelectedToStamp()

        if kwargs["menu_item"] == "action_NextCollection":
            self.log('action_NextCollection')
            self.incrementActiveCollection(1)

        #if kwargs["menu_item"] == "action_EyeDropToBrush":
        #    self.eyeDropSelectedToBrush()

        if kwargs["menu_item"] == "toggle_invert_mask":
            self.setInvertSelection(kwargs['toggle_invert_mask'])

        if kwargs["menu_item"] == "toggle_use_brush":
            self.setNodeParm('useBrush', kwargs['toggle_use_brush'], True, 'Toggle Use Brush')
            self._useBrush = self.evalNodeParm('useBrush')

        if kwargs["menu_item"] == "toggle_select_instances":
            self.setNodeParm('selectAllModelInstances', kwargs['toggle_select_instances'], True, 'Toggle All Instances')

        #with hou.undos.group("brush: toggle Edit Effects"):
        for toggleName, label in CrowdBrush.HANDLEEFFECTS:
            if kwargs["menu_item"] == toggleName:
                self.setNodeParm(toggleName, kwargs[toggleName])

    ########## END OF STATE CLASS ###########


def addRadioStripList(menu, menu_name, menu_description, options, default):
    menu.addRadioStrip(menu_name, menu_description, default)
    for option_name, option_description in options:
        menu.addRadioStripItem(menu_name, option_name, option_description)

def addToggleMenu(parentmenu, menu_name, menu_description, options):
    newmenu = hou.ViewerStateMenu(menu_name, menu_description)
    for option_name, option_description in options:
        newmenu.addToggleItem(option_name, option_description, False)
    parentmenu.addMenu(newmenu)

def addToggleList(parentmenu, options):
    for option_name, option_description in options:
        parentmenu.addToggleItem(option_name, option_description, False)

def create_menu():
    menu = hou.ViewerStateMenu('brush_menu', 'Brush')

    # hotkeys
    state_typename = 'sop_crowdlayoutbrush'


    hk = su.hotkey(state_typename, 'hk_toggle_use_brush', 'b', 'Toggle Use Brush')
    menu.addToggleItem('toggle_use_brush', 'Use Brush', True, hotkey=hk)
    menu.addSeparator()

    menu.addRadioStrip('select_brush_shape', 'Brush Shape', 'surface')
    hk = su.hotkey(state_typename, 'surface_brush', '1', 'Surface Brush', 'Enable Surface Brush')
    menu.addRadioStripItem('select_brush_shape', 'surface', 'Surface', hotkey=hk)
    hk = su.hotkey(state_typename, 'screen_brush', '2', 'Screen Brush', 'Enable Screen Brush')
    menu.addRadioStripItem('select_brush_shape', 'screen', 'Screen', hotkey=hk)

    menu.addSeparator()
    menu_brush_source = hou.ViewerStateMenu('menu_brush_source', 'Brush Sources')
    addRadioStripList(menu_brush_source, 'select_brush_source', 'Brush Source', CrowdBrush.BRUSHSOURCES, 'circleScatter')
    menu.addMenu(menu_brush_source)
    menu.addSeparator()
    #select_parm_menu.addRadioStrip('brush_mode_surface', 'Bend Parm', 'bend', hotkey=hotkeytest1)
    #select_parm_menu.addRadioStripItem('brush_mode_screen', 'bend', 'Bend', hotkey=hotkeytest3)
    #menu.addMenu(select_parm_menu)

    #menu.addSeparator()
    #menu.addToggleItem('toggle_add_points', 'Enable Add Points', True, hotkey=hk)

    menu.addRadioStrip('select_brush_mode', 'Brush Mode', 'add_points')
    hk = su.hotkey(state_typename, 'mode_add', '3', 'Toggle Add Points')
    menu.addRadioStripItem('select_brush_mode', 'add_points', 'Add Points', hotkey=hk)

    hk = su.hotkey(state_typename, 'toggle_edit_override', '4', 'Toggle Edit Override')
    menu.addRadioStripItem('select_brush_mode', 'edit_override', 'Edit Override', hotkey=hk)

    hk = su.hotkey(state_typename, 'toggle_edit_scale', '5', 'Toggle Edit Scale')
    menu.addRadioStripItem('select_brush_mode', 'edit_scale', 'Edit Modify', hotkey=hk)

    hk = su.hotkey(state_typename, 'toggle_xform_handle', '6', 'Toggle Xform Handle')
    menu.addRadioStripItem('select_brush_mode', 'xform_handle', 'Xform Handle', hotkey=hk)


    menu.addSeparator()
    #menu.addRadioStrip('label_editAffected', 'Attribs Affected by Edit Brush', 'hidden1')
    #menu.addRadioStripItem('label_editAffected', 'hidden1', 'hidden1')

    addRadioStripList(menu, 'select_edit_affected', 'Attribute to Affect', CrowdBrush.EDITEFFECTS, 'doEditScale')

    menu.addSeparator()
    #addToggleMenu(menu, 'menu_editAffected', 'Attribs Affected by Edit Brush >>', CrowdBrush.EDITEFFECTS)
    #addToggleList(menu, CrowdBrush.EDITEFFECTS)

    addToggleList(menu, CrowdBrush.HANDLEEFFECTS)


    menu.addSeparator()
    menu.addToggleItem('toggle_invert_mask', 'Invert Mask Selection', False)

    menu.addToggleItem('toggle_select_instances', 'Select All Model Instances', False)
    menu.addSeparator()

    menu.addActionItem('action_ClearAll', 'Clear All Points')

    #hk = su.hotkey(state_typename, 'hk_clearSelected', 'delete', 'Clear Selected')
    menu.addActionItem('action_ClearSelected', 'Clear Selected Points')

    menu.addActionItem('action_StampFromSelected', 'Stamp From Selected')

    #TODO Hotkey doesn't want to work. Dunno why
    #hk = su.hotkey(state_typename, 'hk_nextCollection', '8', 'Go Next Collection')
    menu.addActionItem('action_NextCollection', 'Next Collection')
    #menu.addActionItem('action_EyeDropToBrush', 'EyeDrop Selected to Brush')
    #menu.addActionItem('invert_mask', 'Invert Selection Mask')
    menu.addSeparator()

    return menu


    ###################################### CREATE STATE #################################################################

def createViewerStateTemplate():
    """ Mandatory entry point to create and return the viewer state
        template to register. """


    #state_typename = kwargs["type"].definition().sections()["DefaultState"].contents()
    state_typename = "sop_crowdlayoutbrush"
    state_label = "Crowd Layout Brush"
    state_cat = hou.sopNodeTypeCategory()

    template = hou.ViewerStateTemplate(state_typename, state_label, state_cat)
    template.bindFactory(CrowdBrush)
    #template.bindIcon(kwargs["type"].icon())

    # Create and bind context menu
    template.bindMenu(create_menu())

    template.bindHandleStatic(
        "xform", "editsop_handle",
        [("edt_tx", "tx"),
         ("edt_ty", "ty"),
         ("edt_tz", "tz"),
         ("edt_rx", "rx"),
         ("edt_ry", "ry"),
         ("edt_rz", "rz"),
         ("edt_sx", "sx"),
         ("edt_sy", "sy"),
         ("edt_sz", "sz"),
         ("edt_px", "px"),
         ("edt_py", "py"),
         ("edt_pz", "pz"),
         ("edt_prx", "pivot_rx"),
         ("edt_pry", "pivot_ry"),
         ("edt_pyz", "pivot_rz")],

        settings="translate(1) rotate(1) scale(1) "
    )

    #template.bindParameter(hou.parmTemplateType.Toggle, name="raygroundplane2", label="Ray Ground PLANE2",
    #                       default_value=True, align=True)

    # Selector Eye Dropper

    template.bindGeometrySelector(
        name="selector_crowd_placement",
        prompt="Select agent points to edit",
        use_existing_selection=False,
        quick_select=True,
        geometry_types=[hou.geometryType.Points],
        #consume_selection=True,
        auto_start=False
    )
    '''
    template.bindGeometrySelector(
        name="selector_eyeDropper2",
        prompt="Select a primitive to Copy2",
        quick_select=True,
        geometry_types=[hou.geometryType.Primitives]
    )
    '''

    return template






