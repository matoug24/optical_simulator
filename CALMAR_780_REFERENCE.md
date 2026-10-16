# Calmar 780 nm source reference

Research date: 13 October 2026. The installed model is unknown. The user authorized
a reasonable assumption; the app therefore includes the separately labelled
**Calmar Mendocino · 780 nm (assumed)** product template.

TeraView identifies a high-powered Calmar Mendocino module in the TeraPulse Lx:
https://teraview.com/2020/12/17/december-newsletter/

This confirms the family used in that product, without identifying the user's
specific laser or confirming a Calmar model for the TeraCota service-guide variant.
The local TeraCota guide describes a Menlo replacement procedure.

The provisional catalog reference is **FPL-M4RFF**, from Calmar's 780 nm high-power
OEM datasheet, Rev. E, 25 August 2022:
https://calmarlaser.com/docs/datasheets/oem/OEM.780.High.Power.pdf

| App property | Preset | Basis |
|---|---:|---|
| Central wavelength | 780 nm | Catalog nominal; tolerance ±3 nm |
| Spectral FWHM | 5 nm | Approximate catalog spectrum width |
| Average optical power | 150 mW | Reference near the specified >150 mW minimum, not measured output |
| Gaussian 1/e² radius | 0.50 mm | Assumed 1.00 mm diameter at the source plane |
| Gaussian 1/e² half-divergence | 0.50 mrad | Estimate for a near-ideal beam with its waist at the source plane |
| Rays per wavelength | 33 | Numerical sampling choice |
| Wavelength samples | 7 | Numerical sampling choice: 231 bundle rays total |

The radius and divergence are not supplied by this datasheet. The estimate is
consistent with the ideal Gaussian relation theta = wavelength/(pi × waist radius),
which gives approximately 0.497 mrad at 780 nm and a 0.50 mm waist radius. A real
beam's waist position and M² must be measured; this app does not infer them.
Gaussian beam reference: https://www.newport.com/n/gaussian-beam-optics/

The catalog lists pulse duration <110 fs, M² <1.1, polarization extinction >20 dB,
and collimated free-space output. These are reference specifications, not measured
inputs for this installed laser. Pulse analysis now derives its reference duration
from the configured spectrum and phase. A Gaussian 5 nm FWHM spectrum at 780 nm
implies about 179 fs transform-limited intensity FWHM, so the default Gaussian does
not reproduce the catalog's <110 fs duration. A sech² spectral model implies about
128 fs in the narrow-band limit. Enter a measured spectrum width/profile and
dispersion to represent the actual source. Polarization is editable; the reference
default assumes a linear state rather than fitting the specified extinction.

The catalog specification table lists 100 MHz repetition rate, while its front-page
description mentions an 80 MHz RF synchronization output. Do not treat that text
as confirmation of the installed unit's repetition rate. Calmar also offers custom
rates. Repetition rate is not an input to the present tracer.

Change the source power, beam radius and divergence to measured values when known.
The source coordinates should refer to the optical launch plane represented in
the simulation. Changing the power scales calculated transmitted power but does
not change ray directions or fractional transmission in this linear model.
