'use strict';
let learningExampleLoading=false;
$('load-learning-example').onclick=()=>{
 const selector=$('learning-example'),title=selector.options[selector.selectedIndex].text,key=selector.value;
 confirmReplace('Load '+title+'?',async()=>{
  if(learningExampleLoading)return;
  const rev=revision;learningExampleLoading=true;$('load-learning-example').disabled=true;
  try{
   const response=await fetch('/api/examples/'+encodeURIComponent(key)),data=await response.json();if(!response.ok)throw Error(data.error||'Unable to load example.');
   if(revision!==rev){toast('The layout changed while loading. Choose the example again.');return}
   replaceLayout(data.config);await run();toast('Learning example loaded. Suggested experiments are below the selector.');
  }catch(error){toast('Unable to load example: '+error.message)}finally{learningExampleLoading=false;$('load-learning-example').disabled=false}
 });
};
const learningDescriptions={
 complex_dispersion:'Grating → doublet → fold → waveplate/analyzer → glass plate → singlet. Try bandwidth, glass thickness and source GDD. Inspect Pulse & Dispersion at the glass plate and Focus Analysis after the final singlet. Bench: 45 × 30 cm.',
 complex_telescope:'Approximately 2× Keplerian telescope → two folds → four-surface air-spaced focusing assembly → analyzer. Move telescope B ±5 mm; edit the assembly air gap and compare focus. Bench: 50 × 30 cm.',
 complex_3d_alignment:'Five folds carry the beam from 25 to 90 to 35 mm height. Try a 0.1–0.5 mrad mirror tilt and inspect downstream surface spots. Use the side/corner views and Focus Analysis after the return doublet. Bench: 40 × 30 cm.'
};
$('learning-example').onchange=()=>{$('learning-example-description').textContent=learningDescriptions[$('learning-example').value]};
$('learning-example').onchange();
