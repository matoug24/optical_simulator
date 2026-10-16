# Verification — 13 October 2026

- 58 Python numerical, product persistence and HTTP checks passed:
  `python -m unittest -v test_workbench test_products test_analysis test_optics_review test_app`.
- Startup/reload shows an empty bench, even after adding an element.
- Three custom doublet lenses with different refractive indices were saved in an
  isolated browser test library and remained available after reopening the page.
- Selecting Lens shows Edmund and generic defaults plus saved variants. Adding a
  saved variant preserved its refractive indices in the bench inspector.
- Defaults remain unchanged when custom definitions are saved. Saved laser
  updates and invalid prescriptions are covered by the persistence checks.
- Browser verification products are in `.qa/products.json`, separate from the
  production `products.json` library.
- JavaScript syntax passed for `workbench.js`, `products.js`, `analyses.js`,
  `spectral.js` and `pulseviz.js`.
- Local browser preview rendered the default bench, optics, beam, inspector and
  encounter record in Top and 3D views.
- Source edits were verified: 11.25 mW input produced 10.861 mW boundary power
  through the folded example. Radius edits persisted in the inspector.
- The 0.1 mrad U fine-tilt control changed B's normal elevation by approximately
  −0.00573° and changed downstream hit heights without moving other components.
- Adding a grating exposed its complete editable aperture, pose, density, order
  and efficiency controls; editing position/orientation updated the scene.
- All supplied example JSON files passed the real HTTP validation and simulation
  endpoints without changing their input settings.

The automated browser file-picker test lost its browser session before attaching
the file. The native file-picker interaction was therefore not verified. Layout
JSON validation/recomputation was verified through the HTTP interface. Results
include geometric rays and approximate coherent fields/pulses; hardware accuracy
has not been calibrated. See `ANALYSIS_MODELS.md` for their separate model limits.

## New analysis checks

- All nine workbench tabs rendered and switched correctly in the local browser.
- Surface diagnostics were checked at mirrors and all three lens interfaces;
  selecting a source/element/visit changed the displayed record. Zoom uses a
  separate beam-centered density histogram; aggregate metrics use all rays.
- The 780 nm example's grating solver reported incidence 38.766°, diffraction
  27.766° and signed return deviation −11.000°, then reran the route.
- B mirror sensitivity gave smooth target derivatives in the browser. An analytic
  test checks the expected factor of two in mirror angular response and the
  oblique target-coordinate projection.
- The Accuracy tab displayed 129→516 rays/wavelength and 7→9 wavelength samples.
  Two levels correctly left convergence unconfirmed, even with a 20% tolerance.
  The test suite also verifies that repeating capped sampling cannot confirm it.
- Folded-layout coherent propagation through the doublet to E gave 9.752 mW and
  about 0.161 mm beam-plane radii at 256 pixels. The 780 nm example's after-lens
  field gave 134.303 mW and 0.548 / 0.486 mm radii. These are numerical outputs,
  not measured hardware values.
- Pulse reconstruction in the 780 nm example displayed 178.87 fs reference FWHM,
  681.11 fs output, net GDD 42,423.1 fs² and net TOD −84,064.1 fs³ in chief-family
  mode at the end mirror. Optional local coherent-field pulse sampling, Gaussian
  broadening, supplied dispersion sums and grating angular-dispersion GDD have
  independent numerical/analytic tests.
- The quarter-wave plate at 45° converted the chief polarization to Q≈U≈0,
  V≈−1. Circular ellipse orientation is reported as undefined, avoiding numerical
  angle noise. Malus' law, Brewster transmission and scalar/S/P power accounting
  have analytic checks.
- A custom 180° waveplate was saved in the isolated QA library, appeared in the
  second Add-to-bench dropdown and remained after reloading. Reloading still
  showed zero bench elements.
- Browser Export results produced finite JSON containing the completed field
  analysis, grid 256, and six surface summaries. Browser console showed no errors.
- `surface_analysis_preview.png` records the tabbed surface-analysis interface.

Numerical checks cover free-space Gaussian spreading, aperture diffraction,
interference of two coherent pupils, reverse field propagation, lens ABCD
determinant/reciprocity, grating momentum and target solving, phase-derived pulse
dispersion, Jones/Fresnel power and local field/pulse serialization. A lens crossing
the bench boundary records only interfaces actually reached inside the volume.

## Lens/grating review and waveform update

The eleven review tests in `test_optics_review.py` cover independent manufacturer
focal values, SCHOTT indices, Snell tangential momentum at all lens interfaces,
tilted/flipped/reverse traversal at five wavelengths, conical grating momentum
and angular dispersion, grazing-order roundoff, the actual dispersed bundle's
per-ray refraction, curvature launch phase, analytic Gaussian q field propagation,
material-phase GDD, chirp sign, quadratic-phase interpolation and pulse compression
by opposite GDD. See `OPTICS_REVIEW.md` for findings and physical-model limits.

The browser displayed seven wavelength colours from 764.07 to 795.93 nm in the
spectral-focus example. Colour controls, central spectral rays, 3D/Top views and
surface scatter colours were checked. The example's ray calculation reached the
bench boundary; the representative spectral intersection is separately tested
to lie inside the volume.

The new waveform view displayed a transform-limited reference of 89.42 fs, a
626.38 fs input including +20,000 fs² source GDD, and a 4,874.06 fs output at the
fold mirror, with 157,580.3 fs² net GDD. These are illustrative configuration
outputs, not measurements. Intensity normalization, source/output phase, chirp,
optical electric-field display and a 20 fs carrier window were checked in the
browser. The carrier caption reported the expected 2.602 fs period at 780 nm.

The pulse settings can be expanded separately from the waveform. Startup/reload
still begins with an empty bench. Updated screenshots are saved as
`wavelength_rays_preview.png` and `pulse_waveform_preview.png`.

## General prescriptions, material library and focus — 14 October 2026

The expanded suite passes **69 tests**. JavaScript syntax checks pass, all HTML
IDs are unique, and new static assets/API routes are served successfully.
New API checks cover saved custom materials, invalid table rejection and finite
focus-response serialization. Existing layouts and all six examples validate and
recompute. Physics/persistence checks are described in LENS_MATERIAL_FOCUS.md.

The illustrative `examples/lens_focus.json` gives an interior combined geometric
minimum 37.960950 mm after the chief exit, 3.347003 micrometres RMS radius and
0.041167 mm longitudinal chromatic focal shift. These are geometric simulation
outputs, not measured or diffraction-limited performance.

Browser interaction verification was attempted using the computer-use skill with
isolated product/material libraries. Computer Use stopped because it could not
reliably determine the current browser URL for policy enforcement. No browser UI
verification or new UI screenshot is claimed for this update. Existing preview
screenshots predate the new prescription, material and focus controls.


## Four side views, corner presets and plane ruler — 14 October 2026

Ten Node checks pass for camera screen/depth conventions, unit/orthogonal camera
axes, plane round trips, edge-on rejection, distances under zoom/pan/reversed
views, plane constraints, all-preset drawing with a mock canvas, corner-to-free
orbit, two-click measurements without element movement, coplanar snapping,
invalid offset rejection and screen-aligned drag/keyboard movement. The four
component checks use a minimal DOM/canvas, not a real browser rendering test.
JavaScript syntax and unique HTML IDs/script load order also pass. No new visual
browser verification or screenshot is claimed for this update.

## Three complex learning examples — 14 October 2026

Four stored-configuration checks and two HTTP loader/asset checks pass. Each
central ray encounters every intended optic and reaches the bench boundary.
All three nominated focusing targets have resolved interior geometric minima.
The telescope's sampled central-wavelength bundle expands by 2.000288×; the 3D
route reaches 25, 90 and 35 mm heights. The folded dispersion example calculates
a finite input/output pulse at its glass plate. JavaScript syntax and unique
HTML IDs pass. This update has no new visual browser verification.

The JSON files and step-by-step experiments are in examples/COMPLEX_EXAMPLES.md.
The new selector loads only the three explicitly listed example files through
read-only API routes. Startup remains empty; product/material libraries are not
modified by loading these self-contained layouts.

## Lens interfaces, plane Pointer and independent scrolling — 14 October 2026

Nineteen Node geometry/component checks pass, covering prescribed spherical and
flat surface positions, Edmund midpoint offsets, flipped orientation, custom
air gaps, all-view rendering, plane-constrained XYZ, invalid/outside positions,
Pointer exclusion from spatial views and ruler mutual exclusion. Selecting an
optic with sub-threshold cursor movement preserves its position and trace.
The HTTP page/asset test passes for the new scripts and stylesheet.

Real browser checks used a separate preview server and tab with isolated product
and material libraries. The folded example showed curved outer faces and the
cemented interface, with an enlarged inspector cross-section and vertex table.
Flipping reversed the layout faces and table offsets. Pointer displayed XYZ on
XY at fixed Z = 20 mm. Switching to a corner view disabled it. Scrolling each
sidebar independently left the central layout stationary. These changes affect
visualization and interaction, not the optical propagation model.

## Standalone GitHub checkout — 15 October 2026

The shared optical primitives are now bundled in optics.py and doublet.py.
AST comparison confirms the nine extracted primitives and the doublet module
match the established GVD code without changes to their calculations. Imports
resolve entirely within this repository; the neighbouring GVD_Simulator folder
is no longer required. All 75 Python tests and 34 Node checks pass. HTTP checks
cover UTF-8 decoding and serving every script and stylesheet linked by the page.
Temporary QA data, caches, virtual environments and secrets files are ignored.
The repository includes a GitHub Actions workflow for the same regression suites.
