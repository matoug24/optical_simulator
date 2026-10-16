"""Jones vectors in global 3D coordinates; power coefficients are explicit inputs."""
import numpy as np
from optics import unit, frame, rotate


def pack(e): return [[float(z.real),float(z.imag)] for z in e]
def unpack(e): return np.array([complex(*z) for z in e])


def source_jones(source,u,v):
    theta,chi=np.deg2rad([source.get('polarization_angle_deg',0),source.get('ellipticity_deg',0)])
    return np.cos(chi)*(np.cos(theta)*u+np.sin(theta)*v)+1j*np.sin(chi)*(-np.sin(theta)*u+np.cos(theta)*v)


def transported(e,before,after):
    axis=np.cross(before,after); sine=np.linalg.norm(axis); cosine=float(np.dot(before,after))
    if sine>1e-12: return rotate(e,axis/sine,np.arctan2(sine,cosine))
    if cosine<0: return rotate(e,frame(before)[0],np.pi)
    return e.copy()


def sp_axes(direction,normal,other=None):
    cross=np.cross(direction,normal)
    if np.linalg.norm(cross)<1e-10:
        cross=frame(direction)[0] if other is None else other
    s=unit(cross); return s,unit(np.cross(s,direction))


def fresnel_transmit(e,before,after,normal,n1,n2):
    s,p=sp_axes(before,normal); pout=unit(np.cross(s,after))
    ci=abs(float(np.dot(before,normal))); ct=abs(float(np.dot(after,normal)))
    ts=2*n1*ci/max(n1*ci+n2*ct,1e-30)
    tp=2*n1*ci/max(n2*ci+n1*ct,1e-30)
    flux=np.sqrt(n2*ct/max(n1*ci,1e-30))
    return flux*(ts*np.dot(e,s)*s+tp*np.dot(e,p)*pout)


def element_transfer(e,before,after,normal,field,wavelength,u=None,v=None):
    """Additional Jones action. The common reflectance/transmission is applied separately."""
    kind=e['type']
    if kind in ('polarizer','waveplate'):
        # Project the marked surface axis into the beam's transverse plane.
        axis=u if u is not None else frame(normal)[0]
        axis=axis-before*np.dot(axis,before)
        if np.linalg.norm(axis)<1e-10: axis=frame(before)[0]
        axis=unit(axis); second=unit(np.cross(before,axis))
        a=np.deg2rad(e.get('axis_deg',0)); fast=np.cos(a)*axis+np.sin(a)*second
        slow=-np.sin(a)*axis+np.cos(a)*second
        ef,es=np.dot(field,fast),np.dot(field,slow)
        if kind=='polarizer': es*=10**(-e.get('extinction_db',30)/20)
        else:
            retard=e.get('retardance_deg',90)
            if e.get('retardance_model','inverse_wavelength')=='inverse_wavelength': retard*=e.get('reference_wavelength_nm',780)/wavelength
            es*=np.exp(1j*np.deg2rad(retard))
        return ef*fast+es*slow
    if e.get('polarization_model','scalar')!='sp': return transported(field,before,after)
    s,p=sp_axes(before,normal); pout=unit(np.cross(s,after))
    cs=np.sqrt(e.get('s_factor',1))*np.exp(1j*np.deg2rad(e.get('s_phase_deg',0)))
    cp=np.sqrt(e.get('p_factor',1))*np.exp(1j*np.deg2rad(e.get('p_phase_deg',0)))
    return cs*np.dot(field,s)*s+cp*np.dot(field,p)*pout


def stokes(field,direction,u=None,v=None):
    if u is None: u,v=frame(direction)
    a,b=np.dot(field,u),np.dot(field,v); intensity=float(abs(a)**2+abs(b)**2)
    if intensity<1e-25: return dict(I=0.,Q=0.,U=0.,V=0.,linear_angle_deg=None,ellipticity_deg=None)
    q=float((abs(a)**2-abs(b)**2)/intensity); z=a*np.conjugate(b)
    uu=float(2*z.real/intensity); vv=float(-2*z.imag/intensity)
    return dict(I=intensity,Q=q,U=uu,V=vv,linear_angle_deg=float(np.rad2deg(.5*np.arctan2(uu,q))) if q*q+uu*uu>1e-20 else None,
                ellipticity_deg=float(np.rad2deg(.5*np.arcsin(np.clip(vv,-1,1)))))
