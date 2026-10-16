# Optics Workbench

A new offline optical bench editor and arbitrary-route 3D geometric ray tracer.
It reuses the existing GVD simulator's vector reflection, reflective grating,
pose-frame, thin-lens and spherical/Snell utilities. It has its own UI, layout
format and nearest-hit tracing engine. The original GVD app remains separate.

## Start

Double-click **Start_New_App.cmd** in this folder. Keep the console open while using the app.
It opens a local browser at `http://127.0.0.1:8787`, choosing another available
port if needed. No internet connection or account is required.

This repository is self-contained: the shared GVD optical primitives are bundled
in `optics.py` and `doublet.py`. No neighbouring project is required.

On another computer, install Python 3.10+ and run:

```text
git clone https://github.com/matoug24/optical_simulator.git
cd optical_simulator
python -m pip install -r requirements.txt
python app.py
```

Optional: `python app.py --port 8788 --no-browser`.

Every app opening starts with a **blank 30 × 15 cm bench**. Previously used bench
layouts are not automatically restored. Open a saved layout explicitly when needed.

## Product Management

1. Open the **Product Management** tab and choose Lens, Laser, Mirror, Grating or Polarization optics.
2. Choose a default template or a previously saved product.
3. Enter a product name and edit its optical properties.
4. Click **Save as new product** to create a reusable variant, or **Update saved
   product** to update the selected saved definition.
5. Return to **Workbench**. Under **Add to the bench**, choose an element category,
   then choose its default or saved product from the second dropdown and add it.

Lens templates include **Edmund 45-805 · doublet**, **Generic lens · editable
doublet**, and **Generic lens · ideal thin lens**. The editable doublet starts with
custom constant glass indices, exposing both refractive indices directly. Radii,
diameters, thicknesses and glass selection remain editable. You can save different
lens or laser prescriptions, up to 500 saved products overall.

Products are saved to **New_app/products.json** when you press a save button.
They remain available after restarting the server, changing its port or using a
different browser. Back up this file to preserve your library. Product definitions
contain optical properties; positions and orientation belong to bench instances.
Editing a saved product affects subsequently added instances. Existing bench
elements retain their own values. The inspector's **Save this configuration as a
product** button opens the manager with that element's optical properties.

For an isolated library, use `python app.py --product-library path/to/products.json`.

## Use the workbench

1. Set width and depth in **cm**. The default bench is **30 × 15 cm**.
   Working height defaults to 10 cm; rays stop at any face of this 3D volume.
2. Choose Laser, Mirror, Grating or Lens in the first dropdown, choose a product
   in the second, and click **Add selected product**. Mirror defaults include B,
   C and E. Multiple copies and multiple lasers work.
3. Click an element in the scene or list. Edit its X/Y/Z in **mm**, its angles
   in **degrees**, and its optical properties in the inspector.
4. Drag optics in Top view to move X/Y, or Side view to move X/Z. Arrow keys
   on the focused canvas move the selected optic by 0.1 mm; Shift uses 1 mm.
   Shift-drag pans, the mouse wheel zooms, and Fit view resets the view.
5. Use 3D to inspect height/tilt; drag to orbit. U/V fine controls rotate about
   the element's local aperture axes by the specified **mrad** step.
6. Click **Run simulation**. The tracer chooses the nearest physical optic
   intersection at every step; moving one element never realigns the others.
   Gold is the chief ray. Faint rays show the sampled Gaussian bundle; red
   sampled rays stop at an obstruction or other failed interaction.
   **Wavelength colours** displays shorter wavelengths in blue and longer ones in
   red, with the numerical wavelengths in the legend. This is false colour for
   infrared light. **Centre rays / λ** adds a central-position guide for every
   spectral sample. These guides do not add power to the simulation. Switch off
   Ray bundle to see the centre rays clearly. Colours also appear on surface
   scatter plots, with red crosses indicating clipped samples.
7. Inspect the encounter record, aperture clearances, path length, transmitted
   power at the work-volume boundary, and warnings. An old trace fades after edits;
   rerun to update it.
8. **Save layout** downloads JSON; **Open layout** reloads it. **Export results**
   downloads configuration, chief paths, displayed bundle paths, surface summaries,
   encounters, metrics and completed analyses. Large bundles export a path subset;
   aggregate surface/bench metrics use the complete ray ensemble.

The `examples` folder includes `empty_bench.json`, `folded_beam.json`, and
`grating_spectrum.json`. Open them with **Open layout**. The grating example uses
seven wavelength samples across a 20 nm Gaussian spectrum to show spatial spread.

The folded example traces laser → B → C → lens → E → boundary. Use **Start with
an empty bench** for a new design. Resize freely; an enabled laser's centre must
remain inside the volume. An optic outside the volume is reported and interacts
only if its optical surface intersects the volume.

## Editable optical models

The Laser category also includes **Calmar Mendocino · 780 nm (assumed)**.
Its catalog reference and estimated beam parameters are documented in
`CALMAR_780_REFERENCE.md`; the installed model has not been confirmed.

- Laser: central wavelength, spectral FWHM, power, Gaussian 1/e² beam radius,
  1/e² angular half-divergence, ray count, wavelength sampling, pose and roll.
  Position and angle are independently sampled using a repeatable seed. A single
  ray is the on-axis chief ray. Spectral sampling uses Gaussian quadrature;
  compare 3, 5 and 7 samples for wavelength-sensitive layouts.
- B/E mirrors: blank diameter, clear diameter and scalar reflectance. Defaults
  follow the existing B (16 mm) and E (28 mm) models; dimensions are editable.
- C mirror: circular diameter plus a cut at local V = upper edge. The physical
  circular blank is truncated at this edge; roll rotates the cut orientation.
  The default follows the existing 10 mm C aperture with its 1.8 mm upper edge.
- Grating: blank and clear width/height, groove density, integer selected order
  (including zero), scalar order efficiency, normal and groove roll. Defaults
  use the existing Spectrogon 715.702.620 inputs: 1400 lines/mm, order −1,
  30 × 30 mm blank, 27 × 27 mm assumed clear aperture, efficiency 0.90.
- Lens: choose the exact spherical cemented doublet or ideal paraxial thin lens.
  Both expose blank/clear diameters and per-traversal transmission. Thin mode
  exposes positive or negative focal length. Doublet mode exposes three signed
  radii, two centre thicknesses, glass A/B, constant custom indices, and A/B flip.
  The default reproduces the established Edmund 45-805 lens prescription:
  R = +43.96, −42.90, −392.21 mm; thickness = 6 + 4 mm; N-LAK22 / N-SF6.
  N-LAK22/N-SF6 use the existing wavelength-dependent glass data. Custom constant
  indices apply only to a glass set to “Custom constant index”. Zero radius/plane
  faces are not supported in doublet mode; use a large signed radius instead.
  The thin-lens focal length field does not control the doublet.

For optics, azimuth/elevation specify the **surface normal**, not the mirror's
plane angle. Azimuth 0° points +X; positive azimuth turns toward +Y; positive
elevation turns toward +Z. Roll rotates U/V about the normal. The grating grooves
follow local V. For the laser the same normal vector is its propagation direction.
The exact lens positioning datum is the midpoint between its outer axial vertices.

## Analysis tabs

The middle area has **Optical Layout**, **Beam Tracker**, **Surface Beams**,
**Grating Angles**, **Accuracy**, **Sensitivity**, **Physical Optics**,
**Pulse & Dispersion**, and **Polarization** tabs. Choose a laser, an optical
element and its encounter visit in the shared selectors. **Edit element** opens
that optic in the inspector. Analysis inputs are saved with the layout; computed
analysis results are included in the Beam Tracker's **Export results** download.
Changing inputs or selection clears computed analyses and rejects results from
requests started with older inputs. Geometry edits mark the ray record stale.

**Surface Beams** shows weighted incident ray density and individual ray hits in
the element's local U/V plane, its blank and clear aperture, clipped samples,
incident/after power, centroid and 2σ equivalent radii. Diagnostics are attached
only to element surfaces. Choose individual doublet interfaces and repeated visits.
**Zoom to beam** uses a finer histogram centered on the beam. The 2σ radius equals
the 1/e² radius for a Gaussian; it is a second-moment description for other shapes.
Up to 800 paths and 2,000 scatter points per surface are drawn; metrics use all rays.

**Grating Angles** reports chief-ray incidence/diffraction measured from the normal
and a signed deviation from the incoming beam's return direction, around the groove
axis. A target such as −11° solves the grating orientation while holding its groove
direction, order, density and central wavelength fixed. Other optics stay fixed;
check the resulting route. There is no universal −11° grating deflection.

**Accuracy** compares incident power, centroid and beam radii over 2–4 ray/spectral
refinements. Two consecutive comparisons must pass the chosen tolerance. You can
apply the finest sampling to the source. This measures numerical stability, not
hardware calibration. **Sensitivity** follows the established app's central
finite-difference method, extended to any enabled component. It reports target
U/V position, angular slopes and chief-ray power responses to XYZ translation,
local U/V tilt and roll. Missing or changed routes invalidate the derivative;
these chief-ray derivatives do not estimate complete bundle coupling losses.

**Physical Optics** propagates a coherent Gaussian Jones field along the selected
chief route. Choose wavelength, field span, grid and before/after target interaction.
Padded, band-limited angular spectrum propagation includes aperture diffraction
and interference within that coherent field. Oblique optics remap the pupil,
including grating anamorphism. Wavelength-dependent doublet ABCD matrices come from
the exact Snell solver, retaining first-order power and principal-plane shifts.
Intensity, envelope phase, power, beam radii and numerical sampling warnings are
reported. Grid convergence compares two resolutions; repeat with increased span
to test the window. Independent stochastic ray-angle divergence is not added to
this single coherent Gaussian mode. Its diffraction follows radius and wavefront
curvature. This mode does not combine separate lasers or split diffraction orders
into a coherent interferometer.

**Pulse & Dispersion** reconstructs the pulse by Fourier transforming its spectral
Jones components. It includes continuous traced optical path through air/glass,
grating phase ramps, source/coating GDD and TOD, and optional supplied fibre β₂/β₃
and length. The spectrum can be Gaussian or sech², and must have nonzero bandwidth.
The reference duration is derived from that spectrum. Choose a fixed surface U/V
sample point and before/after interaction. Chief-family mode tracks spectral rays;
optional local coherent-field sampling includes spatial spectral filtering and
diffraction at that point. Local sampling uses the selected field grid and increases its envelope wavelength count
with pulse spectral sampling; refine the independent field analysis and inspect warnings. GDD/TOD
are fits near the centre frequency, while the FFT uses the full sampled phase.
The additional source/user/fibre inputs are summed separately. Pulse convergence
refines spectral sampling. This is a linear optical pulse model; it does not
predict nonlinear THz emission or fully resolve pulse-front tilt across the beam.

**Polarization** shows the chief-ray ellipse and normalized Stokes Q/U/V after each
element, plus polarization-sensitive throughput. Laser ellipse angle and
ellipticity are editable. Mirror/grating/lens S/P power factors and phase multiply
the common optical coefficient. Optional bare Fresnel transmission follows each
doublet interface; avoid double-counting loss already in the specified transmission.
Polarizers expose pass axis/extinction, and waveplates expose fast axis, retardance,
reference wavelength and wavelength law. Both are available as savable products.

The **Load 780 nm analysis example** button explicitly loads a grating → doublet →
waveplate → end-mirror route. Startup still opens an empty bench. This example is
illustrative and is not a measured layout of your instrument.

**Load spectral-focus example** adds an illustrative 10 nm bandwidth and chirped
source, with grating → doublet → fold mirror → boundary. The spectral centre rays
cross after the mirror within the bench. Their crossing locates spectral overlap;
the monochromatic waist and shortest pulse can be at different locations. Compare
Top with Side/3D to confirm overlap in three dimensions.

To visualize the femtosecond pulse, open **Pulse & Dispersion**, select the source
and an element, and press **Calculate pulse & dispersion**. The intensity plot
shows the actual laser input, the propagated output and a transform-limited
reference. The input now includes source GDD/TOD. **Normalize each curve** compares
their shapes; switch it off for their relative peak levels. **Calculation settings**
opens the spectral sampling, surface U/V point, additional GDD/TOD and fibre inputs.
Source/output spectral phase and instantaneous wavelength versus time reveal chirp.

Choose **Optical electric field** to see carrier oscillations in a 20, 80 or 200 fs
window around the output peak. At 780 nm the optical period is about 2.602 fs. This
is an illustrative carrier on the calculated complex pulse envelope: absolute
carrier-envelope phase is unspecified, and a dominant transverse component is
shown. Constant propagation delay is removed. The selected source spectrum and
chirp determine the waveform; it is not a measurement of your installed laser.

The lens/grating review, independent optical checks and remaining approximations
are recorded in `OPTICS_REVIEW.md`.

## Scope and verification

This is a geometric alignment simulator. It includes finite apertures, blank
blocking, vector reflection, the reflective vector grating equation, spherical
intersections, Snell refraction, and bidirectional lens traversal. No prescribed
route is used. Closed loops stop at an editable interaction limit.

The coherent field engine is scalar/paraxial with Jones components. It does not
calculate vector Maxwell fields, rigorous groove efficiency, higher-order lens
wave aberrations, nonlinear effects, thermal/mechanical effects or mount collisions.
Exact geometric lens aberrations remain in the separate ray model. Coating and
waveplate coefficients/dispersion are supplied inputs rather than inferred materials.
Each doublet traversal is handled as one element, so keep other elements clear
of its glass volume. Blanks are optical outlines rather than complete solids.
Monte Carlo bundle clipping depends on ray count; compare 33 and 81 rays near an
aperture edge. Default coordinates are illustrative, not measured rack positions.

Run the numerical checks from this folder:

```text
python -m unittest -v test_workbench test_products test_analysis test_optics_review test_app
```

The checks cover the default route/loss, free-space bounds, nearest-hit order,
3D reflection, missed and clipped optics, cut-edge roll, valid/evanescent grating
orders, thin-lens focus, agreement with the established doublet, reverse traversal,
custom prescriptions, exiting inside lens glass, closed loops, Gaussian spectral
weighting and invalid inputs. These verify the code, not calibration to hardware.
HTTP checks also cover the page/assets, JSON result serialization, all three
example layouts through validation/recomputation, analysis endpoint serialization,
and invalid or unauthorized requests. Additional analytic checks cover Gaussian
diffraction, coherent pupil interference, lens invariants/reciprocity, Malus' law,
quarter-waveplate circular polarization, Brewster/Fresnel power, mirror sensitivity,
grating GDD and Gaussian pulse broadening. See `VERIFICATION.md` and
`ANALYSIS_MODELS.md` for verification and model boundaries.


## Surface prescriptions, materials and focus

See [LENS_MATERIAL_FOCUS.md](LENS_MATERIAL_FOCUS.md) for the full workflow and limits.

- Product Management → Lens → **Generic singlet · surface prescription** exposes
  any 2–32 spherical or flat surfaces, their spacing, clear apertures and materials.
  Change a doublet's model to **Surface prescription · exact Snell** to start from
  its existing parameters. Use R = 0 for a plane and Air after a surface for a gap.
- **Material library** below the product editor saves constant indices, three-term
  Sellmeier coefficients or measured n(λ) tables to `materials.json`. Existing lens
  products/layouts keep their own embedded material snapshots. Select an updated
  material explicitly to apply library changes. Declared ranges forbid extrapolation.
- **Focus Analysis** finds per-wavelength and combined geometric minima after the
  selected element, with RMS/80% radii, chromatic shift and a coloured spot diagram.
  Search stops before the next optic or bench boundary and reports limited minima.
- Open `examples/lens_focus.json` for an illustrative dispersive singlet example.
  Startup remains an empty bench. This example is not a hardware calibration.

Measured tables use linear interpolation, so prefer smooth Sellmeier dispersion
for femtosecond GVD. Focus radii are geometric; coherent field propagation retains
its first-order lens approximation and common entrance pupil.


## Lens interfaces, layout views and plane tools

In **Surface Beams**, Visit defaults to **All**, overlaying every recorded visit to
the selected interface in one diagram. Visit outlines and a legend identify each
beam on shared local U/V axes. Density and power readouts sum repeated passes. Choose a numbered
visit for a single plot. Other analysis tabs retain their numbered visit selection.

Physical lenses show their prescribed curved or flat surfaces and glass regions
in the layout. Select a lens for coloured first/last face labels and its midpoint
position datum. The inspector and Product Management also show an enlarged,
true-scale cross-section and a table of each surface's signed radius, vertex
offset from the datum and following material. Flipping a lens reverses the faces
and offsets in both drawings. Ideal thin lenses retain their symbolic drawing,
because they have no physical thickness or surface prescription.

On desktop screens, the library and inspector scroll independently. The central
layout remains visible; analysis panels and Product Management have their own
scroll areas. Narrow mobile screens retain the stacked layout.

The **View** dropdown in Optical Layout includes Top, Front, Back, Left, Right,
Front-left corner, Front-right corner and Free 3D. Front looks along +Y, Back
along −Y, Left along +X and Right along −X. Side-view dragging and arrow keys
follow the screen axes, preserving the hidden coordinate. Drag a corner/free
view to orbit; Shift-drag pans, the wheel zooms, and Fit view resets framing.

Click **Ruler**, choose **XY horizontal**, **XZ vertical** or **YZ vertical**, and
set the remaining coordinate (Z, Y or X) in mm. Click point A, then point B inside
the bench. The tool shows in-plane distance in mm/cm and endpoint/ΔXYZ values.
It also works from corner/free views by intersecting the chosen plane; edge-on
planes are disabled. It never infers an arbitrary 3D separation from a 2D picture.

**Snap to coplanar optic centres** only snaps to actual centres on the selected
plane. For example, set XY's Z position to 20 mm to measure between optics at
that height. **Snap to 1 mm grid** rounds only the two in-plane coordinates.
Measurements can run diagonally within a plane. Clear measurement resets the
points; a third click starts another measurement; Escape on the canvas exits the
ruler. Shift-drag pans while measuring. Changing to a different orthographic
plane clears the measurement; corner/free views retain the selected plane.
Views and ruler measurements are session tools, not saved optical-layout data.

Click **Pointer** beside Ruler to show cursor X, Y and Z in millimetres. It works
only in Top, Front, Back, Left and Right views, on their XY, XZ or YZ plane. Set
the remaining coordinate in the plane-position field; its initial value uses the
selected optic's hidden coordinate (otherwise zero). This coordinate is fixed,
not inferred from the object beneath the cursor. Outside the working volume,
the tool clears the coordinates. Corner and Free 3D views switch Pointer off.
Pointer and Ruler are mutually exclusive; Escape exits either tool.

Run `node --test test_layout_geometry.cjs test_lens_geometry.cjs test_layout_tools.cjs`
for the camera, surface geometry, plane tools and pointer/keyboard checks.


## Three complex learning examples

Use the left sidebar's **Complex learning examples** selector and **Load learning
example**, or open these JSON files with **Open layout**:

1. `examples/complex_dispersion.json` — folded grating/doublet path, waveplate and
   analyzer, dispersive glass plate, final singlet; 45 × 30 cm bench.
2. `examples/complex_telescope.json` — approximately 2× thick-lens Keplerian
   telescope, two folds and a four-surface air-spaced focusing assembly;
   50 × 30 cm bench.
3. `examples/complex_3d_alignment.json` — five folds through three beam heights,
   doublet focusing, polarization optics and an ideal comparison lens;
   40 × 30 cm bench.

See [the experiment guide](examples/COMPLEX_EXAMPLES.md) for target selections,
recommended adjustments and interpretation limits. The illustrative inputs are
not hardware calibration. Save your experimental variants under new filenames;
loading replaces the current bench. Startup remains empty. These files embed
custom material snapshots and do not change your product/material libraries.

Regenerate the three checked configurations with `python complex_examples.py`.

## Animated beam propagation

Click **Visualize** next to Fit view to calculate the current layout and animate
all displayed bundle rays, spectral centre rays and chief rays at **5 cm/s** of
geometric path length. Every ray advances from its source on the same clock,
following its own reflections, refractions and diffraction direction. The trace
repeats after the longest path reaches its endpoint. Click **Stop visualization**
or press Escape on the layout to return to the complete static trace.

Moving an unlocked component or editing parameters queues a fresh trace and
restarts playback when that calculation completes. Camera changes, zoom and pan
preserve the propagation distance. Hidden browser tabs pause playback. This is
an instructional propagation speed, not physical light speed or a femtosecond
pulse animation. It follows the branches available in the existing ray model;
the selected grating order remains the only calculated order, and large bundles
retain the simulation's existing display sampling limit.
