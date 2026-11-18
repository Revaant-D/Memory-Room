"""roomgeom: the geometry behind Memory Room's 3D room, with no model in it.

    roomgeom.fit     line one set of 3D points up with another (Umeyama fit)
    roomgeom.level   turn raw model output into the room frame (floor z = 0, z up)
    roomgeom.place   place a photo from model poses, and decide whether to trust it

Needs only numpy. See README.md in the folder above.
"""
