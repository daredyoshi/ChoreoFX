import hou
import viewerstate.utils as su

def intersectGeo(collisionGeo, origin, dir, intersectTolerance, doSnapping=True):
    ### Try intersect the collision geo from the mouse position in the viewport

    gi = su.GeometryIntersector(collisionGeo, tolerance=intersectTolerance)
    gi.intersect(origin, dir, snapping=doSnapping)
    # print (gi.prim_num)
    # print (gi.geometry)
    # print (gi.position)
    # print (gi.snapped_point_num)

    return gi.prim_num, gi.position, gi.normal, gi.uvw

def intersectCurves(collisionGeo, origin, dir, intersectTolerance, doSnapping=True):

    prim_num, position, normal, uvw = intersectGeo(collisionGeo, origin, dir, intersectTolerance, doSnapping=True)


    if doSnapping:
        if prim_num >= 0:
            position = collisionGeo.prim(prim_num).positionAtInterior(uvw[0], uvw[1] )

    return prim_num, position, normal, uvw[0]


def snapToNearestPointOfPrim(geometry, primnum, referencePos):
    ### Find the nearest real point on a primitive to a reference position by comparing to all primpoint positions.

    snap_pos = None
    pt_num = -1
    pt_u = -1
    hasu = True

    if primnum != -1:
        min_dist = 1000000
        snap_pos = None
        pt_num = None

        if geometry.findPointAttrib("u") == None:
            hasu = False

        for pt in geometry.prim(primnum).points():
            pos = pt.position()
            dist = (pos - referencePos).lengthSquared()
            if dist < min_dist:
                min_dist = dist
                snap_pos = pos
                pt_num = pt.number()
                if hasu:
                    pt_u = pt.attribValue("u")
    # print "pt_num:", pt_num
    # print "snap pos:", snap_pos
    return pt_num, pt_u, snap_pos


def getNearestPointToCursor(geometry, origin, dir, intersecttolerance=0.5, doSnapping=False):
    ### Try intersect geometry from the mouse position ray, then get the nearest point on the prim

    primnum, position, normal, uvw = intersectGeo(geometry, origin, dir, intersecttolerance, doSnapping)
    # self.log("primnum=", primnum)
    # self.log("uvw=", uvw)
    pt_num, pt_u, snap_pos = snapToNearestPointOfPrim(geometry, primnum, position)
    #pt_num = 5
    #pt_u = uvw[0]
    #snap_pos = hou.Vector3(1,2,3)
    return primnum, pt_num, pt_u, snap_pos


def getNearestHandleToCursor(geometryHandles, origin, dir, intersecttolerance=0.5, doSnapping=False):
    ### Try intersect handle geometry from the mouse position ray to get the nearest point

    primnum, position, normal, uvw = intersectGeo(geometryHandles, origin, dir, intersecttolerance, doSnapping)
    pt_num = primnum

    if not pt_num < 0:
        snap_pos = geometryHandles.point(pt_num).position()
    else:
        snap_pos = hou.Vector3(0, 0, 0)
    # self.log("handle primnum=", primnum)
    # self.log("handle uvw=", uvw)

    return pt_num, snap_pos


def intersectOriginPlane(origin, direction):
    ### Intersect a flat plane to calculate a flat position offset vector

    planePos = hou.hmath.intersectPlane(hou.Vector3(0, 0, 0), hou.Vector3(0, 1, 0), origin, direction)
    return hou.Vector3(planePos)

def getPrimUnderMouse(node, mouseX, mouseY):
    gv = node.scene_viewer.curViewport()
    # self.log(gv.queryInspectedGeometry())
    # pos, normal, test = gv.queryWorldPositionAndNormal(4, 4)
    # node = gv.queryNodeAtPixel(MOUSEX, MOUSEY)
    num = -1
    prim = gv.queryPrimAtPixel(node, int(mouseX), int(mouseY))
    if prim != None:
        num = prim.number()

    return num