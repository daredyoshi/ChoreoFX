import hou


def makeGeometryDrawableGroup(sceneviewer, groupname):
    # Construct a geometry drawable group
    line = hou.GeometryDrawable(sceneviewer, hou.drawableGeometryType.Line, "line",
                                params={
                                    "color1": (0.0, 0.0, 1.0, 1.0),
                                    "style": hou.drawableGeometryLineStyle.Plain,
                                    "line_width": 3}
                                )

    face = hou.GeometryDrawable(sceneviewer, hou.drawableGeometryType.Face, "face",
                                params={
                                    "style": hou.drawableGeometryFaceStyle.Plain,
                                    "color1": (0.0, 1.0, 0.0, 1.0)}
                                )

    point = hou.GeometryDrawable(sceneviewer, hou.drawableGeometryType.Point, "point",
                                 params={
                                     "num_rings": 2,
                                     "radius": 10,
                                     "color1": (1.0, 0.0, 0.0, 1.0),
                                     "style": hou.drawableGeometryPointStyle.LinearCircle}
                                 )

    groupgeo =hou.GeometryDrawableGroup(groupname)

    groupgeo.addDrawable(face)
    groupgeo.addDrawable(line)
    groupgeo.addDrawable(point)

    return groupgeo

class HighlighterKnob(object):
    def __init__(self, sceneviewer):

        self.scene_viewer = sceneviewer

        self.knob_geo = hou.Geometry()
        self.knob_pt = self.knob_geo.createPoint()

        self.knob_drawable = hou.GeometryDrawable(
            self.scene_viewer,
            hou.drawableGeometryType.Point,
            "highlighter_knob",
            params={
                'style': hou.drawableGeometryPointStyle.SmoothCircle,
                'color1': hou.Vector4(1.0, 1.0, 1.0, 1.0),
                'radius': 8,
                'fade_factor': 0.5
            }
        )

        self.knob_drawable.setGeometry(self.knob_geo)

        self.show(False)

    def setKnobPosition(self, pos):
        self.knob_pt.setPosition(pos)
        self.knob_geo.findPointAttrib("P").incrementDataId()
        self.knob_geo.incrementModificationCounter()

    def show(self, onoff):
        self.knob_drawable.show(onoff)

    def setParam(self, paramname, value):
        self.knob_drawable.setParams(params={
            paramname : value
        })

    def draw(self, handle):
        self.knob_drawable.draw(handle)

    def setTransform(self, pivot, scale):
        svec = hou.Vector3(scale, scale, scale)
        xform = hou.hmath.buildTransform({
            'translate': pivot,
            'rotate': hou.Vector3(0, 0, 0),
            'scale': svec
        })
        self.knob_drawable.setTransform(xform)


class SingleTextDrawable(object):
    def __init__(self, sceneviewer, name,  position, value):

        self.scene_viewer = sceneviewer
        self.geoViewport = self.scene_viewer.curViewport()
        pos2 = self.geoViewport.mapToScreen(position)
        pos3 = hou.Vector3(pos2[0], pos2[1], 0)
        scale = 0.5
        self.text_drawable = hou.TextDrawable(self.scene_viewer,
                                name,
                                params = {
                                    'text': "<font size=7>"+str(value)+"</font>",
                                    'translate': pos3,
                                    'scale': hou.Vector3(scale, scale, scale),
                                    'origin': hou.drawableTextOrigin.BottomLeft
                                }
                            )
        self.show(False)


    def show(self, onoff):
        self.text_drawable.show(onoff)

    def draw(self, handle):
        self.text_drawable.draw(handle)

    def setParam(self, paramname, value):
        self.text_drawable.setParams(params={
            paramname : value
        })


class TextOnPoints(object):
    def __init__(self, sceneviewer, name):

        self.scene_viewer = sceneviewer
        self.textDrawableList = []
        self.show(False)
        self.name = name

    def updateTextPoints(self, geo, attribname, isInt=True):
        positions = geo.pointFloatAttribValues("P")
        values = geo.pointFloatAttribValues(attribname)
        self.textDrawableList = []


        for i in range(len(values)):
            name = self.name + str(i)
            position = hou.Vector3(positions[i*3], positions[i*3+1], positions[i*3+2])
            #print position
            value = values[i]
            if isInt:
                value = int(value)
            ptTextDrawable = SingleTextDrawable(self.scene_viewer, name, position, value)
            self.textDrawableList.append(ptTextDrawable)

    def show(self, onoff):
        for text in self.textDrawableList:
            text.show(onoff)

    def draw(self, handle):
        for text in self.textDrawableList:
            text.draw(handle)


def highlightPosition(self, drawable, position):
    ### Display a pystate drawable at a point position
    new_geo = hou.Geometry()
    point = new_geo.createPoint()
    point.setPosition(position)

    # update the drawable
    drawable.setGeometry(new_geo)
    drawable.show(True)




def addRadioStripList(menu, menu_name, menu_description, options, default):
    menu.addRadioStrip(menu_name, menu_description, default)
    for option_name, option_description in options:
        menu.addRadioStripItem(menu_name, option_name, option_description)

def addToggleListSubmenu(parentmenu, menu_name, menu_description, options):
    newmenu = hou.ViewerStateMenu(menu_name, menu_description)
    for option_name, option_description in options:
        newmenu.addToggleItem(option_name, option_description, False)
    parentmenu.addMenu(newmenu)

def addToggleList(parentmenu, options):
    for option_name, option_description in options:
        parentmenu.addToggleItem(option_name, option_description, False)


### From Kinefx
class RollerBall(object):
    def __init__(self, scene_viewer):
        self.geo = hou.Geometry()
        self.knob_geo = hou.Geometry()
        self.knob_pt = self.knob_geo.createPoint()
        self.scene_viewer = scene_viewer
        self.sphere_verb = hou.sopNodeTypeCategory().nodeVerb("sphere")
        self.sphere_verb.setParms({
            'type': 2,
            'rows': 32,
            'cols': 32
        })

        self.sphere_verb.execute(self.geo, [])

        self.circle_verb = hou.sopNodeTypeCategory().nodeVerb("circle")
        self.circle_verb.setParms({
            'type': 1,
            'divs': 32
        })

        self.circle_geo = hou.Geometry()
        self.circle_verb.execute(self.circle_geo, [])

        self.drawable = hou.GeometryDrawable(
            self.scene_viewer,
            hou.drawableGeometryType.Face,
            "rollerball",
            params={
                'style': hou.drawableGeometryFaceStyle.Plain,
                'backface_culling': 1,
                'color1': hou.Vector4(0.2, 0.2, 0.2, 0.5),
                'fade_factor': 0.2
            }
        )

        self.knob_drawable = hou.GeometryDrawable(
            self.scene_viewer,
            hou.drawableGeometryType.Point,
            "rollerball_knob",
            params={
                'style': hou.drawableGeometryPointStyle.SmoothCircle,
                'color1': hou.Vector4(1.0,1.0,1.0,1.0),
                'radius': 6,
                'fade_factor': 0.5
            }
        )
        self.knob_drawable.setGeometry(self.knob_geo)
        self.drawable.setGeometry(self.geo)

        self.is_behind = False
        self.is_ball = True

        self.circle_N = hou.Vector3(0,1,0)


        self.start_transform = hou.Matrix4(1)
        self.start_vec = hou.Vector3()
        self.start_mouse_x = 0.0
        self.start_mouse_y = 0.0
        self.start_ray_dir = hou.Vector3(0,0,0)
        self.start_ray_origin = hou.Vector3(0,0,0)

        # vector for twist
        self.primary_axis = hou.Vector3(0,0,1)
        # vector for bend
        self.secondary_axis = hou.Vector3(1,0,0)

        self.axis = hou.Vector3(0,0,1)

    def setBall(self):
        if self.is_ball:
            return False
        self.drawable.setGeometry(self.geo)
        self.is_ball = True
        return True

    def setCircle(self, N):
        if not self.is_ball and self.circle_N == N:
            return False
        self.axis = N
        self.drawable.setGeometry(self.circle_geo)
        self.is_ball = False
        return True

    def setTransform(self, pivot, scale, normal=None):
        svec = hou.Vector3(scale, scale, scale)
        if normal:
            xform = hou.Vector3(0,0,1).matrixToRotateTo(normal)
            xform *= hou.hmath.buildTranslate(pivot)
            xform = xform.preMult(hou.hmath.buildScale(svec))
        else:
            xform = hou.hmath.buildTransform({
                'translate': pivot,
                'rotate': hou.Vector3(0,0,0),
                'scale': svec
            })
        self.drawable.setTransform(xform)
        self.knob_drawable.setTransform(xform)

    def setKnobPosition(self, pos):
        self.knob_pt.setPosition(pos)
        self.knob_geo.findPointAttrib("P").incrementDataId()
        self.knob_geo.incrementModificationCounter()

    def show(self, on):
        self.knob_drawable.show(on)
        self.drawable.show(on)

    def draw(self, handle):
        self.drawable.draw(handle, params={
            'backface_culling': 1 if self.is_ball else 0
        })
        params = {
            'color1': hou.Vector4(0.2, 0.2, 0.2, 0.5) if self.is_behind else hou.Vector4(1.0, 1.0, 1.0, 1.0),
        }
        self.knob_drawable.draw(handle, params=params)
