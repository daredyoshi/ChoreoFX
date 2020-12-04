"""
State:          crowdGuideBrush_state
Author:         stephenbester
"""

import hou
import viewerstate.utils as su
from choreofx.states import node_parm_utils as pu
from choreofx.states import crowdguidebrush_position_substate
from choreofx.states import crowdguidebrush_timing_substate

reload(pu)
reload(crowdguidebrush_position_substate)
reload(crowdguidebrush_timing_substate)

class CrowdGuideBrush(object):

    PATHMODES = ("position", "timing")

    def __init__(self, state_name, scene_viewer):
        #self._state_name = state_name
        self._scene_viewer = scene_viewer

        self._pathMode = 'position'
        self._node = None
        self._guideHda = None

        self._classTiming = crowdguidebrush_timing_substate.CrowdGuideBrush_Timing(state_name, scene_viewer, self)
        self._classPosition = crowdguidebrush_position_substate.CrowdGuideBrush_Position(state_name, scene_viewer, self)


    def setPathMode(self, modename):
        #self.log(typename)
        value = self.PATHMODES.index(modename)
        self._pathMode = modename
        pu.setNodeParm(self._node, 'path_mode', modename, onlyifchanged=True)

        if self._pathMode == 'position':
            self._classTiming.onInterrupt(kwargs={})
            self._classPosition.onResume(kwargs={})
            self._classTiming.showAgentGuides(False)

        elif self._pathMode == 'timing':
            self._classPosition.onInterrupt(kwargs={})
            self._classTiming.onResume(kwargs={})
            self._classTiming.showAgentGuides(True)

        else:
            self.log("pathMode not set")


    def timingStashEditedPoints(self):
        self._classTiming.stashEditedPoints()

    def initFromNodeParms(self):
        self._pathMode = self.PATHMODES[pu.evalNodeParm(self._node, "path_mode")]

    def childLog(self, childname, message):
        self.log(childname + ":   " + str(message))

    ############################### LIFE CYCLE EVENTS #######################################
    def onEnter(self, kwargs):
        """ Called on node bound states when it starts
        """
        # state_parms = kwargs["state_parms"]
        self.log("onEnter")
        self._node = kwargs["node"]
        self.initFromNodeParms()

        self._classPosition.onEnter(kwargs)
        self._classTiming.onEnter(kwargs)
        '''
        if self._pathMode == 'position':
            self._classPosition.onEnter(kwargs)
        elif self._pathMode == 'timing':
            self._classTiming.onEnter(kwargs)
        else:
            self.log("pathMode not set")
        '''
        self.setPathMode(self._pathMode)


        geoHdaGuides = self._node.node("OUT_GUIDES").geometry()
        if pu.evalNodeParm(self._node, "guideDisplay") == 1:
            self._guideHda = hou.SimpleDrawable(self._scene_viewer, geoHdaGuides, "guidehda_GuideBrush")
            self._guideHda.setDisplayMode(hou.drawableDisplayMode.CurrentViewportMode)
            self._guideHda.enable(True)

        self.showGuides(True)

    def showGuides(self, visible):
        if self._guideHda is not None:
            self._guideHda.show(visible)


    def onExit(self, kwargs):
        """ Called when the state terminates
        """
        self.log("onExit")

        if self._pathMode == 'position':
            self._classPosition.onExit(kwargs)
        elif self._pathMode == 'timing':
            self._classTiming.onExit(kwargs)
        else:
            self.log("pathMode not set")

        self.showGuides(False)


    def onInterrupt(self, kwargs):
        """ Called when the state is interrupted e.g when the mouse moves outside the viewport
        """
        pass
        self._classPosition.onInterrupt(kwargs)
        self._classTiming.onInterrupt(kwargs)
        #self.showGuides(False)


    def onResume(self, kwargs):
        pass
        """ Called when an interrupted state resumes
        """
        #self.log("onResume")
        self.initFromNodeParms()
        #self.showGuides(True)

        '''if self._pathMode == 'position':
            self._classPosition.onResume(kwargs)
        elif self._pathMode == 'timing':
            self._classTiming.onResume(kwargs)
        else:
            self.log("pathMode not set")'''

        self.setPathMode(self._pathMode)

    def onDraw(self, kwargs):
        """ This callback is used for rendering the drawables
        """
        #self.log("onDraw")

        if self._pathMode == 'position':
            self._classPosition.onDraw(kwargs)
        elif self._pathMode == 'timing':
            self._classTiming.onDraw(kwargs)
        else:
            self.log("pathMode not set")

    ###################################### SELECTION EVENTS ###########################################################
    def onStopSelection(self, kwargs):
        #selector_name = kwargs["name"]
        pass

    def onStartSelection(self, kwargs):
        # selector_name = kwargs["name"]
        pass

    def onSelection(self, kwargs):
        """ Called when a selector has selected something
        """
        self.log("onSelection")

        if self._pathMode == 'position':
            self._classPosition.onSelection(kwargs)
        elif self._pathMode == 'timing':
            self._classTiming.onSelection(kwargs)
        else:
            self.log("pathMode not set")

        return False

    ################################## DEVICE EVENTS ##################################################################
    def onMouseEvent(self, kwargs):

        if self._pathMode == 'position':
            self._classPosition.onMouseEvent(kwargs)
        elif self._pathMode == 'timing':
            self._classTiming.onMouseEvent(kwargs)
        else:
            self.log("pathMode not set")

        return False


    def onKeyTransitEvent(self, kwargs):
        """ Called for processing a transitory key event
        """
        if self._pathMode == 'position':
            self._classPosition.onKeyTransitEvent(kwargs)
        elif self._pathMode == 'timing':
            self._classTiming.onKeyTransitEvent(kwargs)
        else:
            self.log("pathMode not set")

        return False


    def onMouseWheelEvent(self, kwargs):
        """ Process a mouse wheel event
        """
        if self._pathMode == 'position':
            self._classPosition.onKeyTransitEvent(kwargs)
        elif self._pathMode == 'timing':
            self._classTiming.onKeyTransitEvent(kwargs)
        else:
            self.log("pathMode not set")

        return False

    ###################################### STATE MENU ACTIONS #################################################################

    def onMenuPreOpen(self, kwargs):

        if self._pathMode == 'position':
            kwargs = self._classPosition.onMenuPreOpen(kwargs)
        elif self._pathMode == 'timing':
            kwargs = self._classTiming.onMenuPreOpen(kwargs)
        else:
            self.log("pathMode not set")


    def onMenuAction(self, kwargs):

        if self._pathMode == 'position':
            self._classPosition.onMenuAction(kwargs)
        elif self._pathMode == 'timing':
            self._classTiming.onMenuAction(kwargs)
        else:
            self.log("pathMode not set")


########## END OF STATE CLASS ###########


###################################### CREATE STATE #################################################################

def create_menu(state_typename):
    menu = crowdguidebrush_position_substate.create_menu(state_typename)

    return menu

def createViewerStateTemplate():
    """ Mandatory entry point to create and return the viewer state
        template to register. """


    #state_typename = kwargs["type"].definition().sections()["DefaultState"].contents()
    state_typename = "crowdGuideBrush_state"
    state_label = "Crowd Guide Brush"
    state_cat = hou.sopNodeTypeCategory()

    template = hou.ViewerStateTemplate(state_typename, state_label, state_cat)
    template.bindFactory(CrowdGuideBrush)
    #template.bindIcon(kwargs["type"].icon())

    template.bindMenu(create_menu(state_typename))


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




