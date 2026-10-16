# Three complex learning configurations

In the left sidebar, choose **Complex learning examples → configuration → Load
learning example**. You can also use **Open layout** to open any JSON below. Save
your current work first; loading replaces the bench. Use **Save layout** to keep
your own experimental variant, then reload the original to reset.

These examples enlarge the working area to fit longer paths. They do not change
the empty 30 × 15 cm startup bench or your saved product/material libraries.
All use an illustrative 780 nm, 8 nm FWHM, 100 mW source with 97 rays per
wavelength and seven spectral samples. These are teaching inputs, not verified
specifications of the installed Calmar laser. Material definitions in custom
prescriptions are embedded in the files.

## 1. Folded spectral dispersion and pulse shaping

**File:** `complex_dispersion.json` · **Bench:** 45 × 30 cm, 12 cm high.

The beam follows:

Laser → 1400 lines/mm grating → 75 mm doublet → E fold mirror → quarter-wave
plate → analyzer → 3 mm N-LAK22 flat plate → dispersive singlet → bench boundary.

The central wavelength has an approximately −11° signed return deviation at the
grating. All elements lie at Z = 30 mm. The source begins with +20,000 fs² GDD.
The doublet refracts the dispersed wavelengths individually; the separate plate
adds material phase without focusing the central ray. The final singlet gives a
second opportunity to compare wavelength-dependent focusing.

Try these experiments one at a time:

1. Run the trace with wavelength colours on. Compare the grating's incoming and
   outgoing bundles. Change source bandwidth from 8 to 2 nm, then 16 nm. Larger
   bandwidth can lead to aperture losses; inspect Surface Beams rather than
   interpreting missing rays as convergence.
2. In **Surface Beams**, select the spectral doublet and inspect all three lens
   interfaces. Compare spectral overlap at different elements.
3. In **Pulse & Dispersion**, select the glass plate and calculate before and
   after its interaction. Change its first surface's distance to the next surface
   from 3 to 9 mm. Compare GDD, phase and the output envelope. Increasing thickness
   also moves the front/back vertices because the datum is their midpoint.
4. Compare source GDD = 0 and +20,000 fs². To explore compensation, try additional
   GDD approximately equal to the negative of the reported net GDD, recalculate,
   and refine. A quadratic correction alone does not remove TOD or spatial
   spectral filtering. The additional-GDD setting is a numerical phase input,
   not an automatically designed physical compressor.
5. Select the final singlet in **Focus Analysis**. Compare per-colour minima and
   the combined spot. A colour crossing does not guarantee the shortest pulse.
6. Rotate the quarter-wave plate from 45° toward 0°, then rotate the analyzer.
   Compare power and the **Polarization** ellipse. This is a convenient way to
   distinguish changes in polarization transmission from aperture clipping.

## 2. Achromatic telescope and air-spaced focusing assembly

**File:** `complex_telescope.json` · **Bench:** 50 × 30 cm, 12 cm high.

Laser → input quarter-wave plate → 75 mm doublet → scaled 150 mm doublet → B
fold mirror → E fold mirror → four-surface focusing assembly → analyzer → boundary.

The two positive doublets form a Keplerian telescope. Their vertex-to-vertex gap
is calculated so that the combined first-order C coefficient is zero at 780 nm,
including thick-lens principal-plane offsets. The second doublet is an illustrative
2× geometric scaling of the original prescription, not an identified catalog item.
The final focusing assembly contains N-LAK22 and N-SF6 singlets separated by a
10 mm air gap. All elements lie at Z = 35 mm.

1. Use **Top** view. Compare the incoming beam with the expanded beam on the
   second telescope lens and first fold mirror. At the central wavelength the
   finite bundle should be approximately twice as wide and nearly collimated.
2. Move Telescope B along X by +5 mm, run, then compare with −5 mm from its original
   position. Watch how the output bundle gains convergence or divergence. Restore
   the original layout before trying another experiment.
3. Select **Two singlets · 10 mm internal air gap**. Its four surfaces are already
   in prescription mode. Surface 2 exits into air and its 10 mm distance defines
   the gap. Change that gap to 5 or 20 mm and recalculate **Focus Analysis** after
   this assembly. Compare focal distance, RMS spot radius and chromatic shift.
4. Replace one singlet's material using the saved material library. Compare it
   with a constant-index glass to see what is lost when material dispersion is
   omitted. Existing material snapshots change only when you explicitly select
   the new material at a surface.
5. Reduce one internal clear diameter to 1–2 mm. Inspect that interface in
   **Surface Beams** and compare power. A clipped bundle can look smaller while
   actually losing useful light.
6. Enable the XY ruler at Z = 35 mm and snap to optic centres. Measure telescope
   centre spacing and compare it with the sum of the focal lengths. Their
   difference illustrates the importance of the thick-lens positioning datum.

## 3. Three-dimensional folded alignment

**File:** `complex_3d_alignment.json` · **Bench:** 40 × 30 cm, 15 cm high.

Laser → upward B fold → high C cut-edge fold → downward E fold → low B fold →
75 mm return doublet → E exit fold → quarter-wave plate → analyzer → ideal 50 mm
comparison lens → boundary.

The beam starts at Z = 25 mm, rises to Z = 90 mm, then descends to Z = 35 mm.
The return doublet produces a geometric focus before the exit fold. The final
ideal lens is included to contrast the thin-lens approximation with exact doublet
refraction; it is not a second manufacturer lens prescription.

1. Switch between **Top**, **Front**, **Left** and both corner presets. Some
   segments overlap in one projection but separate clearly in another. Use
   **Beam Tracker** for their actual XYZ coordinates.
2. Select the upward B fold. Apply 0.1–0.5 mrad of local U or V tilt and run. Use
   **Surface Beams** at the high C mirror and at the return lens to observe the
   downstream centroid shift. Use **Sensitivity** with the chosen target to
   compare the two tilt axes quantitatively.
3. Restore the original, then move the high C mirror by ±0.2 mm in Z. Compare
   intercepted power and outgoing position; translating an optic and tilting it
   are different alignment operations.
4. Change the C mirror's roll or cut-edge height. Watch which parts of the beam
   clip. Inspect the aperture outline and hit samples together.
5. Select the return doublet in **Focus Analysis**. Its search stops before the
   next fold; then select the final ideal lens and compare its minimum.
6. Use XY at Z = 35 mm to measure the lower horizontal path. Use XZ at Y = 50 mm
   to measure the source-to-first-fold leg. The rising/falling legs do not lie
   in a coordinate plane: a ruler on one of these planes gives a projection,
   not their full 3D path length. Coplanar snapping deliberately ignores centres
   at a different plane position.

## Interpretation and verification

Run after every optical edit. Watch for **CHANGES · RUN TO UPDATE** before reading
previous results. Use **Accuracy** to check ray/wavelength convergence before
comparing small differences. Focus measurements are geometric blur measures;
Physical Optics retains its first-order lens approximation. Pulse calculations
describe a chief spectral family unless local field sampling is enabled. The
scalar coating/transmission inputs do not represent measured coating curves.

Each saved configuration is validated and traced before generation. Its central
ray must encounter every intended element in order and reach the bench boundary
with nonzero power. Additional checks cover telescope expansion, 3D heights and
the focus/pulse analyses. Regenerate the three files with `python complex_examples.py`.
