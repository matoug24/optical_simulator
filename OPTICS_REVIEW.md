# Lens, grating and pulse review — 13 October 2026

The nominal geometric lens and reflective grating models passed independent
checks. Each ray retains its own wavelength, position and incoming direction;
the grating's dispersed bundle is refracted individually at every lens interface.
The coherent field lens is still a first-order equivalent and is not the same
accuracy level as the spherical ray model for high-order/off-axis aberrations.

## Lens

The default Edmund 45-805 prescription matches the manufacturer's current page:
25 mm blank, 24 mm clear aperture, radii +43.96 / −42.90 / −392.21 mm, 6 + 4 mm
thicknesses, and N-LAK22 / N-SF6 glasses. At 880 nm, the independent catalog targets
are 75.00 mm effective focal length and 69.06 mm back focal length. The solver
calculates **74.996425 mm EFL** and **69.060445 mm BFL** from near-axis Snell rays.

New tests check tangential wavevector conservation at all three spherical surfaces,
unit direction vectors, and optical reciprocity for 760, 780, 800, 880 and 1050 nm,
with shifted/angled rays, arbitrary 3D orientation, and both lens flips. Glass
indices are checked against SCHOTT's nominal d-line values. Tests also confirm
that the actual grating-dispersed rays enter the doublet at different positions and
angles and are individually refracted, rather than assigned one shared direction.

The editable `focal_length_mm` controls only the ideal thin lens. The doublet's
power follows its radii, thicknesses and wavelength-dependent glass indices.
EFL is measured from the principal plane; BFL is measured from the outer exit
vertex. The element position datum is the midpoint of its two outer vertices.

## Grating

The vector law conserves the groove-parallel component and changes the transverse
tangential component by m λ × groove density. The reflective branch places the
outgoing normal component on the opposite side of the incoming propagation
component. This works for conical incidence and rotated/tilted grooves as well as
the usual planar setup. An independent derivative test verifies angular dispersion.

The grazing-order cutoff now tolerates floating-point roundoff while rejecting
genuinely evanescent orders. The selected order remains −1 by default. No common
fixed −11° kick is applied to different wavelengths: −11° is an optional geometric
target for the central wavelength, solved through the grating law.

Spectrogon's 715.702.620 reference has 1400 lines/mm, a 30×30×6 mm blank, an 800 nm
design wavelength, 12° catalog deviation and ≥90% efficiency under its design
conditions. The selected 27×27 mm clear aperture and scalar 0.90 efficiency remain
nominal assumptions; measured spectral/angular/polarization curves are not supplied.

## Phase and waveform corrections

- Source wavefront-curvature phase is now included in sampled-ray phase records,
  consistent with the launch curvature used for ray angles and coherent fields.
- The pulse comparison now shows the **actual source waveform**, including its
  source GDD/TOD, alongside the propagated output and transform-limited reference.
  Previously the input curve was only the transform-limited reference.
- The temporal transform uses exp(−iωt), consistent with the positive propagation
  phase. Positive GDD produces an up-chirp: instantaneous wavelength decreases
  with time. A test checks this sign directly.
- Cubic interpolation of continuous spectral phase preserves quadratic GDD,
  avoiding the phase errors caused by piecewise-linear interpolation.
- Temporal-window selection accounts for both input and output duration, including
  a chirped source that is compressed by the optics or supplied opposite GDD.
- A compensation benchmark verifies that +20,000 fs² source GDD and −20,000 fs²
  added GDD recover the transform-limited duration without changing the input curve.
- Local coherent-field pulse sampling now honors the selected field grid instead
  of silently capping it at 128. Its envelope wavelength sampling also refines with
  the pulse sampling control over the full spectral window. Field-grid convergence
  must still be checked separately, especially near a small focused spot.

The Pulse & Dispersion tab displays intensity envelopes, source/output spectral
phase, instantaneous wavelength versus time, and an optical-carrier field view.
At 780 nm, the carrier period is **2.601800 fs**. Carrier oscillations are synthesized
on a fine display grid from native-resolution complex envelopes. A dominant
transverse component is shown; absolute carrier-envelope phase is not known and
the carrier's phase is illustrative. Constant propagation delay is removed for
comparison. Normalization is explicit and can be disabled to compare peak loss.

The source spectrum and supplied chirp determine its pulse. These curves are not a
measurement of the installed Calmar laser. Chief-family mode is a temporal model
along tracked spectral rays. Optional local field sampling includes spatial
spectral filtering using the existing approximate coherent field solver. Neither
mode is a full space-time/vector Maxwell calculation or a nonlinear THz model.
In local-field mode, the reported GDD/TOD cards describe the ray/eikonal and
supplied phase. The waveform additionally includes the complex field transfer;
those cards are not a fit to every polarization component's local field phase.

## Wavelength-coloured rays

Bundles and surface scatter points are coloured by wavelength. One additional
central-position ray per spectral sample makes spectral crossings visible even
when the display subsamples a large stochastic bundle. These centre rays are
visual guides and do not add power to the ensemble metrics. Each source gets its
own blue→green→red scale, with actual wavelengths in the legend. This is false
colour, including for infrared light.

The opt-in `spectral_focus.json` example contains source → grating → doublet →
fold mirror → boundary. Its extreme spectral centre rays cross within the working
volume after the fold mirror, verified by a geometric intersection test. The
source uses an illustrative 10 nm bandwidth and +20,000 fs² chirp. It is not a
measured instrument configuration. All regular startup benches remain empty.

Spectral crossing indicates spatial overlap of wavelengths; it does not certify
the smallest monochromatic beam waist, overlap in 3D, or shortest temporal pulse.
Use Top plus Side/3D views and the surface/field/pulse diagnostics together.

## Primary references

- [Edmund 45-805 prescription and focal specifications](https://www.edmundoptics.com/p/25mm-dia-x-75mm-fl-nir-ii-coated-achromatic-lens/6253/).
- [SCHOTT nominal glass dispersion data](https://www.schott.com/en-gb/products/optical-glass/-/media/Project/OnEx/Products/O/optical-glass/Downloads/schott-optical-glass-collection-datasheets-english-may2019.pdf?rev=5358bb64e13a44f2b37f5065490509af).
- [Spectrogon pulse-compression grating specifications](https://www.spectrogon.com/products/holographic-gratings/pulse-compression-gratings/).
- [Newport grating equation](https://www.newport.com.cn/n/the-grating-equation).
- [Newport pulse-shaping spectral phase and GDD](https://www.newport.com/medias/sys_master/images/images/hbe/h76/8797051944990/Automated-Control-of-Amplified-Pulse-Duration-App-Note-38.pdf).

58 regression tests passed, including eleven new review checks. The first-order
field lens is checked against analytic Gaussian q propagation, and doublet glass
GDD against an independent derivative of its material spectral phase. Browser
verification is recorded in `VERIFICATION.md`. Coating transmission, grating
efficiency, source data and lens fabrication tolerances still need measurements
for calibrated predictions of the user's hardware.
