"""Shared optical primitives extracted unchanged from the original GVD simulator.

Bundled locally so Optics Workbench runs as a standalone checkout.
"""
import numpy as np
from doublet import entry_hit


def unit(v):
    v = np.asarray(v, dtype=float)
    norm = np.linalg.norm(v)
    if norm < 1e-12:
        raise ValueError("Degenerate optical direction")
    return v / norm


def frame(normal):
    n = unit(normal)
    u = unit(np.cross([0, 0, 1], n)) if abs(n[2]) < .99 else unit(np.cross([0, 1, 0], n))
    return u, unit(np.cross(n, u))


def rotate(v, axis, angle):
    a = unit(axis)
    return v * np.cos(angle) + np.cross(a, v) * np.sin(angle) + a * np.dot(a, v) * (1 - np.cos(angle))


def reflection(direction, normal):
    return unit(direction - 2 * np.dot(direction, normal) * normal)


def pose_frame(pose):
    """Absolute normal azimuth/elevation, then roll of u/v about that normal."""
    az,el,roll=np.deg2rad([pose[k] for k in ("azimuth_deg","elevation_deg","roll_deg")])
    normal=np.array([np.cos(el)*np.cos(az),np.cos(el)*np.sin(az),np.sin(el)])
    u=np.array([-np.sin(az),np.cos(az),0.])
    v=np.cross(normal,u)
    return normal,rotate(u,normal,roll),rotate(v,normal,roll)


def pose_from_frame(centre,normal,u):
    n=unit(normal); az=np.arctan2(n[1],n[0]); el=np.arcsin(np.clip(n[2],-1,1))
    base_u=np.array([-np.sin(az),np.cos(az),0.]); base_v=np.cross(n,base_u)
    roll=np.arctan2(np.dot(u,base_v),np.dot(u,base_u))
    return dict(zip(("x_mm","y_mm","z_mm","azimuth_deg","elevation_deg","roll_deg"),
                    map(float,[*centre,*np.rad2deg([az,el,roll])])))


class Surface:
    def __init__(self, name, centre, normal, radius=8.0, kind="mirror", half=None, upper=None):
        self.name, self.centre, self.normal = name, np.array(centre, float), unit(normal)
        self.u, self.v = frame(self.normal)
        self.radius, self.kind, self.half, self.upper = radius, kind, half, upper
        self.body_half=None; self.lens_model='thin'; self.lens_flipped=False

    def perturb(self, adjustments):
        a = adjustments[self.name]
        self.centre += [a["dx_mm"], a["dy_mm"], a["dz_mm"]]
        for axis, angle in ((self.u.copy(), a["pitch_mrad"]*.001), (self.v.copy(), a["yaw_mrad"]*.001)):
            self.normal = rotate(self.normal, axis, angle)
            self.u = rotate(self.u, axis, angle)
            self.v = rotate(self.v, axis, angle)
        angle=a.get("roll_mrad",0)*.001
        self.u=rotate(self.u,self.normal,angle)
        self.v=rotate(self.v,self.normal,angle)

    def intersect(self, point, direction):
        if self.kind=='lens' and self.lens_model=='edmund_45805':
            return entry_hit(point,direction,self)
        den = np.dot(direction, self.normal)
        if abs(den) < 1e-10:
            return None
        distance = np.dot(self.centre-point, self.normal)/den
        if distance <= 1e-7:
            return None
        return point + distance*direction, distance

    def local(self, hit):
        q = hit - self.centre
        return float(np.dot(q, self.u)), float(np.dot(q, self.v))

    def margin(self, hit, body=False):
        x, y = self.local(hit)
        extra = .7 if body else 0.0
        if self.half:
            half=self.body_half if body and self.body_half else self.half
            return min(half[0]+extra-abs(x), half[1]+extra-abs(y))
        margin = self.radius+extra - np.hypot(x, y)
        if self.upper is not None:
            margin = min(margin, self.upper+extra-y)
        return float(margin)

    def polygon(self, body=False):
        extra = .7 if body else 0.0
        if self.half:
            half=self.body_half if body and self.body_half else self.half
            x, y = half[0]+extra, half[1]+extra
            uv = [(-x,-y),(x,-y),(x,y),(-x,y)]
        else:
            r = self.radius+extra
            uv = [(r*np.cos(a), r*np.sin(a)) for a in np.linspace(0,2*np.pi,64,endpoint=False)]
            if self.upper is not None:
                # Convex polygon clipping to the machined top edge.
                cap = self.upper+extra
                new=[]
                for p,q in zip(uv,uv[1:]+uv[:1]):
                    if p[1] <= cap: new.append(p)
                    if (p[1] <= cap) != (q[1] <= cap):
                        t=(cap-p[1])/(q[1]-p[1]); new.append((p[0]+t*(q[0]-p[0]),cap))
                uv=new
        return [list(self.centre+x*self.u+y*self.v) for x,y in uv]


def lens_direction(direction, hit, lens, focal_length):
    """Bidirectional paraxial thin-lens slope change in lens-local coordinates."""
    dn = np.dot(direction, lens.normal)
    x,y = lens.local(hit)
    sx=np.dot(direction,lens.u)/abs(dn)-x/focal_length
    sy=np.dot(direction,lens.v)/abs(dn)-y/focal_length
    return unit(np.sign(dn)*lens.normal+sx*lens.u+sy*lens.v)


def fwhm(x,y):
    y=np.asarray(y); i=int(np.argmax(y)); half=y[i]/2
    if half<=0: return None
    left=i; right=i
    while left>0 and y[left]>=half: left-=1
    while right<len(y)-1 and y[right]>=half: right+=1
    if left==0 or right==len(y)-1: return None
    xl=x[left]+(half-y[left])/(y[left+1]-y[left])*(x[left+1]-x[left])
    xr=x[right-1]+(half-y[right-1])/(y[right]-y[right-1])*(x[right]-x[right-1])
    return float(xr-xl)
