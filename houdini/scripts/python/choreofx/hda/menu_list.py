from .. import const
import crowdstoolutils
import hou


class MenuListCreator():
    """
    This class will return a menu list with all of it's public classes
    It wraps menu list functionality from crowdstoolutils

    Gotcha:
        If a parm is specified and that parm is on the default value and
        auto_set_if_notset==True then this parm will be auto set to the first
        item of the returned list.
    """

    def __init__(self, node=None, input=0, sorted=True, parm=None, auto_set_if_notset=False):
        assert (isinstance(input, int))
        if node:
            assert (isinstance(node, hou.Node))
        # if a node is specified that overwrites the value in kwargs
        self.node = node
        self.parm = parm

        self.auto_set_if_notset = auto_set_if_notset
        self.sorted = sorted
        self.input = input

    def geo(self):
        """Returns the geometry for the given node and input"""

        if self.node:
            output = self.node.inputGeometry(self.input)
            if output:
                return output
            else:
                raise ValueError("No Geometry connected to {}'s input {}".format(
                    self.node, self.input
                ))
        else:
            raise ValueError("Node {} is not valid".format(self.node))

    def __get_geometry_point_attrib_strings(self, attrib_name):
        attrib = self.geo().findPointAttrib(attrib_name)
        if attrib:
            return attrib.strings()
        else:
            return None

    def __get_geometry_prim_attrib_strings(self, attrib_name):
        attrib = self.geo().findPrimAttrib(attrib_name)
        if attrib:
            return attrib.strings()
        else:
            return None

    def build_menu_string_list(self, items):
        items = list(items)
        if self.sorted:
            items.sort()
        if self.parm and self.auto_set_if_notset:
            if self.parm.eval() == "notset" and len(items) > 0:
                # set to the first item value
                self.parm.set(items[0])
        return crowdstoolutils.buildMenuStringList(items)

    def point_float_attrib_names(self):
        attrib_names = []
        for attrib in self.geo().pointAttribs():
            if (attrib.type() == hou.attribType.Point and
                    attrib.dataType() == hou.attribData.Float and
                    attrib.size() == 1
            ):
                attrib_names.append(attrib.name())
        return self.build_menu_string_list(attrib_names)

    def agent_names(self):
        agent_names = self.__get_geometry_point_attrib_strings(const.AGENTNAME_ATTRIB_NAME)
        if agent_names:
            return self.build_menu_string_list(agent_names)
        else:
            return []

    def foot_plant_channels(self, agentname):
        channels = []
        # get the correct agent point to read the foot channels from
        agent_point = None
        for point in self.geo().points():
            if point.attribValue("agentname") == agentname:
                agent_point = point
                break
        if agent_point:
            attrib = self.geo().findPrimAttrib("agentrig_footchannels")
            planted_channels = None
            if attrib:
                planted_channels = agent_point.stringListAttribValue("agentrig_footchannels")

            if planted_channels:
                for idx, planted_channel in enumerate(planted_channels):
                    channels.append(idx - 1)
                    channels.append(planted_channel)

        return channels

    def clip_names(self, agentnames=None):
        """
        agentnames: can be a single group string or a split group string
            Limits the clips returned to the ones in the given agent's clip catalogs.
        """
        if not self.node:
            raise ValueError("No node specified")
        if agentnames:
            defns = []
            group = " ".join(["@agentname=" + agentname for agentname in agentnames])
            points = self.geo().globPoints(group)
            processed_agentnames = set()
            for point in points:
                agentname = point.stringAttribValue("agentname")
                if agentname not in processed_agentnames:
                    processed_agentnames.add(agentname)
                    defn = point.prims()[0].definition()
                    defns.append(defn)
        else:
            defns = hou.crowds.findAgentDefinitions(self.geo())

        clip_names = []
        for defn in defns:
            # assert(isinstance(defn, hou.AgentPrimitive))
            for clip in defn.clips():
                clip_names.append(clip.name())

        return self.build_menu_string_list(clip_names)

    def traj_names(self, agentnames=None):
        # make sure there is an agentname attrib
        agentname_attrib = self.geo().findPrimAttrib("agentname")
        if not agentname_attrib:
            return []

        trajname_attrib = self.geo().findPrimAttrib("trajname")
        if not trajname_attrib:
            return []

        traj_prims = [prim for prim in self.geo().prims() if prim.attribValue("agentname") in agentnames]
        traj_names = [prim.attribValue("trajname") for prim in traj_prims]

        if traj_names:
            return self.build_menu_string_list(traj_names)
        else:
            return []