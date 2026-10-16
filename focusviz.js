'use strict';
function renderFocus(){
 const r=analysisCache.focus;if(!r){clearPlot('focus-spot','No geometric spot yet.');clearPlot('focus-canvas','Select an optic and find the focus of the outgoing bundle.');empty('focus-readout','No focus calculation yet.');$('focus-table').replaceChildren();return}
 const c=r.combined;
 plot('focus-canvas',r.scan_distance_mm,[...r.wavelengths.filter((row,i)=>r.wavelengths.length<=5||[0,Math.floor((r.wavelengths.length-1)/4),Math.floor((r.wavelengths.length-1)/2),Math.floor(3*(r.wavelengths.length-1)/4),r.wavelengths.length-1].includes(i)).map(row=>({name:number(row.wavelength_nm,1)+' nm',color:wavelengthColor(row.wavelength_nm,$('analysis-source').value),values:row.curve_rms_mm.map(v=>1000*v)})),{name:'Combined',color:'#ffffff',values:c.curve_rms_mm.map(v=>1000*v)}],'Distance / mm','RMS radius / μm');
 readout('focus-readout',[['Combined minimum RMS radius',number(c.rms_radius_mm*1000,3)+' μm'],['80% encircled-power radius',number(c.encircled_80_radius_mm*1000,3)+' μm'],['Lateral colour at combined plane',number(r.lateral_colour_separation_mm*1000,3)+' μm'],['Distance from chief exit',number(c.distance_mm,3)+' mm'],['Centroid X / Y / Z',c.position_mm.map(v=>number(v,3)).join(' / ')+' mm'],['2σ radii U / V',c.radius_2sigma_mm.map(v=>number(v*1000,3)).join(' / ')+' μm'],['Resolved chromatic focal shift',number(r.chromatic_focal_shift_mm,4)+' mm'],['Surviving power',number(r.surviving_power_mw,4)+' mW'],['Search interval',r.search_interval_mm.map(v=>number(v,3)).join(' – ')+' mm'],['Minimum status',!c.resolved?'Not resolved':c.boundary_limited?'At search limit':'Interior minimum']]);
 table('focus-table',['λ / nm','Distance / mm','RMS radius / μm','80% radius / μm','Centroid X / Y / Z / mm','Rays','Status'],r.wavelengths.map(row=>[number(row.wavelength_nm,2),number(row.distance_mm,4),number(row.rms_radius_mm*1000,3),number(row.encircled_80_radius_mm*1000,3),row.position_mm.map(v=>number(v,3)).join(' / '),row.ray_count,!row.resolved?'Not resolved':row.boundary_limited?'Search limit':'Interior minimum']));notes('focus-result',r);drawFocusSpot(r);
}
$('run-focus').onclick=()=>requestAnalysis('focus','run-focus','focus-result',{max_distance_mm:$('focus-distance').valueAsNumber});
$('focus-distance').onchange=()=>{analysisEpoch++;delete analysisCache.focus;$('focus-result').replaceChildren();renderFocus()};

function drawFocusSpot(r){
 const d=drawing('focus-spot');if(!d)return;const {x,w,h}=d,points=r.spot_samples,extent=Math.max(.00001,...points.flatMap(p=>p.uv_mm.map(Math.abs)))*1.1,scale=Math.min(w-110,h-65)/(2*extent),cx=w/2,cy=h/2;
 x.strokeStyle='#355465';x.beginPath();x.moveTo(cx-extent*scale,cy);x.lineTo(cx+extent*scale,cy);x.moveTo(cx,cy-extent*scale);x.lineTo(cx,cy+extent*scale);x.stroke();
 for(const p of points){x.fillStyle=wavelengthColor(p.wavelength_nm,$('analysis-source').value);x.beginPath();x.arc(cx+p.uv_mm[0]*scale,cy-p.uv_mm[1]*scale,2,0,2*Math.PI);x.fill()}
 x.fillStyle='#9bb2c3';x.font='11px Segoe UI';x.fillText('U / μm',cx-15,h-5);x.fillText('V / μm',8,18);x.fillText('±'+number(extent*1000,3)+' μm',12,h-20);
}
