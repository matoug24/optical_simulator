"""Write small, editable starting layouts without changing any user layout."""
import json
from pathlib import Path
from model import default_config, folded_config, analysis_config, spectral_focus_config, element, simulate

def main():
    out=Path(__file__).resolve().parent/'examples'
    out.mkdir(exist_ok=True)
    folded=folded_config()
    empty={**default_config(),'name':'Empty optical bench','elements':[]}
    grating={**default_config(),'name':'Grating spectral spread','elements':[
        element('laser','laser-1',x_mm=20,y_mm=75,z_mm=20,bandwidth_nm=20,wavelength_samples=7),
        element('grating','grating-1',x_mm=150,y_mm=75,z_mm=20,azimuth_deg=-45)]}
    for name,c in [('folded_beam',folded),('empty_bench',empty),('grating_spectrum',grating),('analysis_780',analysis_config()),('spectral_focus',spectral_focus_config())]:
        simulate(c)
        (out/(name+'.json')).write_text(json.dumps(c,indent=2),encoding='utf-8')
    from complex_examples import write_examples
    write_examples()

if __name__=='__main__': main()
