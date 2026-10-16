# Analysis models and references

The new analyses reuse the established app's surface-coordinate projections,
central alignment differences, FFT/FWHM method and optical primitives. They extend
them to freely placed components, multiple sources, repeated visits and individual
lens interfaces. No automatic route or realignment is imposed.

| Analysis | Model | Practical boundary |
|---|---|---|
| Surface footprints | Weighted geometric hits in local U/V; before/after power and second moments | Sampling dependent; ray heatmaps are not wave intensity |
| Grating | Tangential momentum shift m λ density; unchanged groove component; reflective normal branch | One selected order; supplied efficiency; no groove microstructure |
| Sensitivity | Central differences of chief hit and angular slopes | Local derivative; missing/changed routes invalid; not bundle coupling |
| Convergence | Power, centroid and 2σ radius refinements; separate field/pulse refinements | Numerical stability only; hardware/model accuracy separate |
| Coherent field | Two complex transverse components; padded, band-limited angular spectrum; physical aperture masks and pupil remapping | One chief route/wavelength at a time; scalar diffraction, no coherent multi-source/order branching |
| Field lens | Wavelength-dependent ABCD inferred from near-axis exact Snell rays | First-order lens field; off-axis/high-order wave aberrations omitted |
| Pulse | Eikonal k×optical path + grating ramp; coating/source/fibre spectral phase; componentwise FFT | Chief spectral family or optional local field; not complete vector space-time propagation or nonlinear THz generation |
| Polarization | Global 3D Jones transport; supplied S/P factors/phases; ideal finite-extinction polarizer and retarder; optional Fresnel loss | Coating response and waveplate dispersion must be supplied; no depolarizing/scattering material model |

The ray grating law and spectral phase use the same sign convention. With surface
dispersion axis U, Δ(d·U) = m λ density and the grating phase is
φ = 2π m density × U. Pulse phase is evaluated at a fixed actual target point,
including k d·(point−chief hit); fitting only path lengths to moving ray hits would
give an incorrect dispersion. The grating angular-dispersion benchmark is
GDD = −L λ³ density² / (2π c² cos²β), where L is the path from grating to a plane
normal to its central outgoing ray and β is diffraction from the grating normal.
This is a benchmark geometry; arbitrary paths are traced directly, not assigned
this formula everywhere.

Pulse GDD/TOD are the second/third derivatives of spectral phase with respect to
angular frequency. Constant phase and linear delay are removed before temporal
reconstruction. Supplied quadratic/cubic phase is added as GDD Δω²/2 + TOD Δω³/6.
Time-domain resolution uses spectral zero padding and an adaptive FFT extent.
Before/after target controls exclude or include the target interaction, respectively.
The time transform uses exp(−iωt), paired with positive propagation phase. Positive
GDD gives an up-chirp. Continuous phase is interpolated with cubic Hermite segments
that preserve a quadratic phase. Actual source GDD/TOD is included in the input
waveform; the transform-limited reference is a separate curve. Instantaneous
wavelength is derived from the time derivative of the complex envelope, with
dark intervals left undefined. Fine carrier oscillations are displayed from the
native-resolution envelopes, with unspecified absolute carrier-envelope phase.

Jones power coefficients are applied once. S/P factors multiply the common
reflectance/transmission/efficiency; Fresnel amplitudes are normalized for power
flux. Lens interfaces show their actual cumulative Fresnel transmission, with the
common per-pass transmission and additional supplied Jones action applied at the
last interface. Transverse Stokes bases can rotate along a folded route; ellipse
angles should be read in the indicated local beam basis.

Primary technical references used to verify the implementation:

- [Newport: diffraction grating equation and sign conventions](https://www.newport.com/f/050r-plane-ruled-diffraction-gratings).
- [Matsushima & Shimobaba, 2009: band-limited angular spectrum propagation](https://kansai-u.repo.nii.ac.jp/record/11127/files/KU-1100-20091015-50.pdf).
- [Brown University ultrafast optics lecture: dispersion and grating compressors](https://www.brown.edu/research/labs/mittleman/sites/brown.edu.research.labs.mittleman/files/uploads/lecture10_5.pdf).
- [Newport: polarization control, Fresnel coefficients and waveplates](https://www.newport.com.cn/n/polarization-control-with-optics).
- [Newport: Gaussian beam optics](https://www.newport.com/n/gaussian-beam-optics/).

The band-limited propagation implementation is a practical padded scalar engine,
not a claim to reproduce every geometry or numerical variant in the cited paper.
Use convergence controls and measured source/component data before making physical
alignment decisions. No hardware calibration was performed.


## General prescriptions and focus

Sequential spherical/planar lenses now accept 2–32 interfaces, individual circular
clear apertures, air gaps and embedded material definitions. The established vector
Snell primitive is used at every hit, with each ray's wavelength and actual local
normal. Material snapshots support constant, Sellmeier and linear index-table
models. No extrapolation is allowed. Exterior air is approximated as n = 1.

Focus analysis minimizes the weighted transverse variance analytically along the
next uninterrupted segment. A fixed surviving cohort and common chief-normal
plane avoid artificial minima caused by rays dropping out during the scan. RMS,
2σ and 80% encircled-power radii describe geometric blur, including source divergence,
chromatic centroid separation and alignment. Endpoint minima and unresolved bundles
are flagged. These metrics do not predict diffraction-limited waists or pulse
compression. Details are in LENS_MATERIAL_FOCUS.md.

Physical Optics derives its ABCD equivalent from the new exact surface tracer but
still applies the common entrance pupil and omits individual internal stops and
higher-order wave aberrations. Linear n(λ) tables have derivative discontinuities;
pulse analysis warns when they lie on the traced route.
