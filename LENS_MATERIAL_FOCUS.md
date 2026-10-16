# Surface prescriptions, materials and focus analysis

## Configure a lens

In **Product Management → Lens**, select **Generic singlet · surface prescription**,
or change an existing doublet's **Lens model** to **Surface prescription · exact Snell**.
An empty surface list is initialized from that doublet's current prescription.
The former doublet and ideal thin-lens editors remain available.

Each of 2–32 surfaces specifies:

- Signed spherical radius in mm; **0 means a flat surface**.
- Axial vertex distance in mm to the next surface; the final distance is zero.
- Its own circular clear diameter, within the lens's common clear/blank diameters.
- The material **after** that surface, copied from the material library.

The incident medium and final medium are air, approximated as index 1. The position
datum is the midpoint of the first and last vertices. Positive radius places the
centre of curvature downstream along the forward prescription axis. Flip reverses
the complete assembly, including media order. Add, remove and move surfaces to
construct singlets, cemented multi-element lenses or air-spaced assemblies. A
cemented interface is one surface between two glasses. An air gap requires a
glass-to-air surface followed by an air-to-glass surface with positive spacing.

Save as a product for reuse. Surface prescriptions and their embedded materials
are included in layout JSON files. Opening older layouts requires no migration.
Separate optics must remain outside the complete assembly volume; other bench
elements are not intersected in the middle of its internal sequential traversal.
Aspheres, cylindrical/GRIN/birefringent lenses, non-air exterior media and internally
reflected branches are not included in this update.

## Material library

The **Material library** section below the product editor supports:

- Constant index, including air and illustrative nondispersive glass.
- Three-term Sellmeier: n² = 1 + Σ Bᵢ λ²/(λ² − Cᵢ). Wavelength is in **μm** and
  C coefficients are in **μm²**, while the user-facing wavelength range is in nm.
- Measured wavelength/index pairs, interpolated linearly without extrapolation.

Specify a valid wavelength range and manufacturer/data reference, then use
**Save as new material** or **Update saved material**. Data is saved in
`materials.json`. An alternative test library can be supplied with
`--material-library path/to/materials.json`, independently of `--product-library`.
The built-in SCHOTT glasses use the same nominal coefficients as the established
doublet model; their new library entries restrict evaluation to 365–2500 nm.
Confirm manufacturer validity and temperature for a particular application.

Existing lenses retain material snapshots when the library changes. Explicitly
select the updated saved material in each desired surface and save the lens again
to adopt it. This prevents an unrelated material edit from silently changing a
saved experiment. Manufacturer coefficients, valid ranges and references are user
data; the software does not verify their provenance.

Checks reject invalid indices, reversed/duplicate table wavelengths, insufficient
table coverage, Sellmeier poles inside the declared interval, crossed surfaces and
invalid apertures. Wavelengths outside material ranges raise an error rather than
silently extrapolating. Piecewise-linear tables can give reasonable ray angles,
but their derivative discontinuities make them unsuitable for precision material
GDD/TOD; pulse analysis warns when one lies on the traced route. A constant index
also omits material dispersion.

## Find focus

Run the bench trace, open **Focus Analysis**, choose a laser and the element whose
outgoing bundle you want to examine, set a maximum search distance, and press
**Find beam focus**. A lens is the usual target; a fold mirror is also valid.

The calculation retains all sampled rays, including those omitted from the layout
display for performance. It minimizes the power-weighted RMS geometric radius
analytically for each wavelength and for the combined spectrum on planes normal
to the central chief ray. The combined radius includes wavelength-centroid
separation. The calculation reports:

- Distance from the central chief's exit and the minimum's centroid XYZ position.
- RMS radius, 2σ U/V radii, and an 80% encircled-power radius about the centroid.
- Longitudinal chromatic focal shift between resolved interior minima.
- Maximum separation of wavelength centroids at the combined minimum plane.
- Curves versus axial distance and a wavelength-coloured spot diagram at the
  combined minimum. At most five representative wavelength curves are plotted;
  the table and combined calculation include all sampled wavelengths.

The same surviving cohort is used throughout the search. The interval starts after
all those rays leave the selected element and ends before any of them encounters
another optic or a bench wall. This prevents aperture loss during a scan from
artificially shrinking a spot. Rays lost before/at the target are excluded and
reported. A minimum at a search endpoint is labelled **At search limit**, not
claimed as a resolved interior focus. A bundle with too few samples or no angular
spread is labelled **Not resolved**. Search beyond a mirror by selecting that mirror.

These are geometric blur/aberration diagnostics, not diffraction-limited waist
predictions. Residual spot spread includes the source divergence and alignment as
well as lens aberrations. Best spatial overlap does not guarantee a shortest pulse;
use Pulse & Dispersion for spectral-phase effects. Check ray/wavelength sampling
with the Accuracy controls before trusting small changes.

## Verification

`test_prescriptions.py` verifies the manufacturer-index match, custom formula/table
validation and persistence, independent thick lensmaker focal length, oblique
plane-plate Snell law, forward/reverse multi-surface reciprocity, four-surface
air-spaced refraction, individual aperture clipping, portable product snapshots,
legacy-doublet equivalence, first-order field and pulse compatibility, complete
ray retention, chromatic focus and next-optic/divergence search bounds.

The ray model uses exact local surface normals and each ray's own wavelength and
incoming direction. Physical Optics still uses a first-order ABCD equivalent,
the common entrance pupil, and scalar diffraction; individual internal stops and
higher-order wave aberrations remain outside that field approximation.
