(() => {
  const G = {
    hipY: 0, hipZ: -12,
    bendY: 44.1672955930064, bendZ: -37.5,
    ankleY: 11.2273845388904, ankleZ: -71.1398672165212,
    cgY: 21.88279175285118, cgZ: -46.02412489617628,
    qMin: -20, qMax: 0,
    maxTravel: 20.904119999,
  };

  const passive = [
    [0,0],[32.273458,-2.5],[45.915031,-5],[56.584125,-7.5],[65.760371,-10],
    [74.017255,-12.5],[81.650508,-15],[88.837920,-17.5],[95.697752,-20]
  ];
  const qGrid = [0,-2.5,-5,-7.5,-10,-12.5,-15,-17.5,-20];
  const stanceGrid = [-20,-15,-10,-5,0];
  const rollMap = {
    "-20": [-17.072720785,-15.218287020,-13.311679411,-11.354109100,-9.342953356,-7.266372834,-5.087515747,-2.677312440,0],
    "-15": [-15.806840710,-13.781275122,-11.653625674,-9.394503779,-6.933883801,-4.060042178,0,3.412976057,5.087515747],
    "-10": [-13.548224874,-11.134438604,-8.434835157,-5.173491182,0,4.642433123,6.933883801,8.389721215,9.342953356],
    "-5":  [-9.694828020,-6.111354967,0,5.661369074,8.434835157,10.304509994,11.653625674,12.631214147,13.311679411],
    "0":   [0,6.527022708,9.694828020,11.893973445,13.548224874,14.824062309,15.806840710,16.546191622,17.072720785]
  };

  const el = id => document.getElementById(id);
  const sideCanvas = el('sideCanvas'), frontCanvas = el('frontCanvas');
  const sctx = sideCanvas.getContext('2d'), fctx = frontCanvas.getContext('2d');
  let mode = 'passive', playing = false, progress = 0, last = performance.now();

  function resizeCanvas(canvas) {
    const dpr = window.devicePixelRatio || 1;
    const r = canvas.getBoundingClientRect();
    const w = Math.max(320, Math.round(r.width * dpr));
    const h = Math.max(200, Math.round(r.height * dpr));
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
  }
  function rotYZ(y,z,qDeg, hy=G.hipY,hz=G.hipZ) {
    const a=qDeg*Math.PI/180, yy=y-hy, zz=z-hz;
    return [hy+yy*Math.cos(a)-zz*Math.sin(a), hz+yy*Math.sin(a)+zz*Math.cos(a)];
  }
  function ankleY(q){ return rotYZ(G.ankleY,G.ankleZ,q)[0]; }
  function travel(q){ return Math.max(0, ankleY(0)-ankleY(q)); }
  function qForTravel(mm){
    let lo=G.qMin, hi=0;
    for(let i=0;i<60;i++){
      const m=(lo+hi)/2;
      if(travel(m)>mm) lo=m; else hi=m;
    }
    return (lo+hi)/2;
  }
  function passiveQAt(ms){
    for(let i=0;i<passive.length-1;i++) if(ms>=passive[i][0]&&ms<=passive[i+1][0]){
      const [t0,q0]=passive[i],[t1,q1]=passive[i+1]; const u=(ms-t0)/(t1-t0); return q0+u*(q1-q0);
    }
    return ms<=0?0:-20;
  }
  function passiveTimeAtQ(q){
    const qq=Math.max(-20,Math.min(0,q));
    for(let i=0;i<passive.length-1;i++){
      const [t0,q0]=passive[i],[t1,q1]=passive[i+1];
      if(qq<=q0&&qq>=q1){ const u=(qq-q0)/(q1-q0); return t0+u*(t1-t0); }
    }
    return 95.697752;
  }
  function rootAt(qStance,qSwing){
    const qs=Math.max(-20,Math.min(0,qStance));
    const qw=Math.max(-20,Math.min(0,qSwing));
    let si=0; while(si<stanceGrid.length-2 && qs>stanceGrid[si+1]) si++;
    let qi=0; while(qi<qGrid.length-2 && qw<qGrid[qi+1]) qi++;
    const s0=stanceGrid[si], s1=stanceGrid[si+1];
    const q0=qGrid[qi], q1=qGrid[qi+1];
    const a=(qs-s0)/(s1-s0||1), b=(qw-q0)/(q1-q0||1);
    const r00=rollMap[String(s0)][qi], r01=rollMap[String(s0)][qi+1];
    const r10=rollMap[String(s1)][qi], r11=rollMap[String(s1)][qi+1];
    const r0=r00+b*(r01-r00), r1=r10+b*(r11-r10);
    return r0+a*(r1-r0);
  }
  function ease(u){ return u<.5?2*u*u:1-Math.pow(-2*u+2,2)/2; }
  function lerp(a,b,u){ return a+(b-a)*u; }

  function currentState(p){
    const qStance=parseFloat(el('stanceSlider').value);
    const targetMm=parseFloat(el('stepSlider').value);
    const qTarget=mode==='full'?-20:qForTravel(targetMm);
    const tdRoll=rootAt(qStance,qTarget);
    let qSwing=0, roll=0, contact=false, phase=0, physicalMs=null;
    if(mode==='passive'){
      phase=0; const cycle=p<.78?p/.78:1; physicalMs=cycle*95.697752; qSwing=passiveQAt(physicalMs); roll=0; contact=p>.78;
    } else if(mode==='roll'){
      phase=Math.floor(p*4)%4; roll=14*Math.sin(p*Math.PI*2); qSwing=qStance; contact=true;
    } else {
      if(p<.18){ phase=0; qSwing=0; roll=lerp(0,12,ease(p/.18)); }
      else if(p<.62){ phase=1; const u=(p-.18)/.44; const tTarget=passiveTimeAtQ(qTarget); physicalMs=tTarget*u; qSwing=passiveQAt(physicalMs); roll=12; }
      else if(p<.84){ phase=2; const u=ease((p-.62)/.22); qSwing=qTarget; roll=lerp(12,tdRoll,u); }
      else { phase=3; qSwing=qTarget; roll=tdRoll; contact=true; }
    }
    return {qSwing,qStance,roll,contact,phase,qTarget,tdRoll,targetMm,physicalMs};
  }

  function setupCtx(ctx,canvas){
    const dpr=window.devicePixelRatio||1; ctx.setTransform(dpr,0,0,dpr,0,0); return [canvas.width/dpr,canvas.height/dpr];
  }
  function line(ctx,a,b,w=2,color='#cbd5e1'){ ctx.strokeStyle=color; ctx.lineWidth=w; ctx.beginPath(); ctx.moveTo(...a); ctx.lineTo(...b); ctx.stroke(); }
  function circle(ctx,p,r,color,fill=true){ ctx.beginPath();ctx.arc(p[0],p[1],r,0,Math.PI*2); if(fill){ctx.fillStyle=color;ctx.fill();}else{ctx.strokeStyle=color;ctx.stroke();} }
  function label(ctx,text,x,y,color='#94a3b8',align='left'){ctx.fillStyle=color;ctx.font='12px system-ui';ctx.textAlign=align;ctx.fillText(text,x,y);}

  function drawSide(st){
    resizeCanvas(sideCanvas); const [w,h]=setupCtx(sctx,sideCanvas); sctx.clearRect(0,0,w,h);
    const scale=Math.min(w/160,h/130); const ox=w*.46, oz=h*.20;
    const map=([y,z])=>[ox+y*scale, oz+(-z-5)*scale];
    const hip=[G.hipY,G.hipZ], bend=rotYZ(G.bendY,G.bendZ,st.qSwing), ankle=rotYZ(G.ankleY,G.ankleZ,st.qSwing), cg=rotYZ(G.cgY,G.cgZ,st.qSwing);
    const H=map(hip), B=map(bend), A=map(ankle), C=map(cg);
    const groundY = h-36; line(sctx,[24,groundY],[w-24,groundY],2,'#475569'); label(sctx,'floor reference',w-28,groundY-8,'#64748b','right');
    sctx.save(); sctx.translate(H[0],H[1]-14); sctx.fillStyle='#263244';sctx.strokeStyle='#475569';sctx.lineWidth=1.5;sctx.fillRect(-24,-28,48,28);sctx.strokeRect(-24,-28,48,28);sctx.restore();
    sctx.setLineDash([4,5]);[-20,0].forEach(q=>{const p=rotYZ(G.ankleY,G.ankleZ,q);line(sctx,H,map(p),1,'#334155');});sctx.setLineDash([]);
    line(sctx,H,B,10,'#60a5fa'); line(sctx,B,A,10,'#60a5fa'); circle(sctx,H,7,'#e2e8f0'); circle(sctx,B,4,'#64748b');
    const footHalf=28, qa=st.qSwing*Math.PI/180, dy=Math.cos(qa)*footHalf, dz=Math.sin(qa)*footHalf;
    const f1=map([ankle[0]-dy,ankle[1]-dz]), f2=map([ankle[0]+dy,ankle[1]+dz]); line(sctx,f1,f2,11,st.contact?'#86efac':'#a78bfa');
    if(el('cgToggle').checked){ circle(sctx,C,6,'#fcd34d'); line(sctx,H,C,1.5,'#fcd34d'); label(sctx,'shape-CG proxy',C[0]+8,C[1]-7,'#fcd34d'); }
    label(sctx,`q swing = ${st.qSwing.toFixed(2)}°`,18,25,'#67e8f9');
    label(sctx,`ankle travel = ${travel(st.qSwing).toFixed(2)} mm`,18,43,'#cbd5e1');
    label(sctx,'q=0° stop',w-18,28,'#94a3b8','right'); label(sctx,'q=-20° stop',w-18,46,'#94a3b8','right');
  }

  function drawFront(st){
    resizeCanvas(frontCanvas); const [w,h]=setupCtx(fctx,frontCanvas); fctx.clearRect(0,0,w,h);
    const cx=w*.5, cy=h*.57, scale=Math.min(w/160,h/135); const a=st.roll*Math.PI/180;
    const R=p=>[cx+(p[0]*Math.cos(a)-p[1]*Math.sin(a))*scale,cy-(p[0]*Math.sin(a)+p[1]*Math.cos(a))*scale];
    const ground=h-38; line(fctx,[24,ground],[w-24,ground],2,'#475569');
    const body=[[-31,45],[31,45],[31,-18],[-31,-18]]; fctx.beginPath();body.forEach((p,i)=>{const m=R(p);i?fctx.lineTo(...m):fctx.moveTo(...m)});fctx.closePath();fctx.fillStyle='#263244';fctx.fill();fctx.strokeStyle='#64748b';fctx.stroke();
    const wh=R([0,22]);circle(fctx,wh,22*scale,'#172554');circle(fctx,wh,18*scale,'#2563eb',false);circle(fctx,wh,4,'#e2e8f0');
    const sides=[[-25,'L'],[25,'R']];
    sides.forEach(([x,name])=>{
      const top=R([x,-5]),bot=R([x,-58]);line(fctx,top,bot,8,'#60a5fa');
      const low=R([x,-72]); line(fctx,[low[0]-19*scale,low[1]],[low[0]+19*scale,low[1]],8,name==='L'&&st.contact?'#86efac':'#a78bfa');
    });
    const boundary=rootAt(st.qStance,st.qSwing); const swingCanTouch=st.roll<=boundary+0.15;
    const lPos=R([-25,-72]),rPos=R([25,-72]);
    circle(fctx,[rPos[0],ground-2],5,'#86efac');
    circle(fctx,[lPos[0],ground-2],5,swingCanTouch?'#86efac':'#334155');
    label(fctx,`roll θ = ${st.roll.toFixed(2)}°`,18,25,'#67e8f9');
    label(fctx,`touchdown boundary = ${boundary.toFixed(2)}°`,18,43,'#cbd5e1');
    label(fctx,swingCanTouch?'swing foot: floor reachable':'swing foot: unloaded / above floor',18,61,swingCanTouch?'#86efac':'#fcd34d');
    label(fctx,'L swing',30,ground-10,'#94a3b8'); label(fctx,'R stance',w-30,ground-10,'#94a3b8','right');
  }

  const phaseNames={
    passive:['重力スイング','ストッパ到達','保持','リセット'],
    roll:['右荷重','中央通過','左荷重','中央通過'],
    full:['遊脚を除荷','ストッパまで受動スイング','RWで接地側へロール','初回接地'],
    early:['遊脚を除荷','目標qまで受動スイング','RWで早期接地境界へ','初回接地']
  };
  function updateUI(st){
    el('stepControl').style.opacity=mode==='early'?1:.35; el('stepSlider').disabled=mode!=='early';
    el('stanceControl').style.opacity=(mode==='early'||mode==='full')?1:.35; el('stanceSlider').disabled=!(mode==='early'||mode==='full');
    el('stepValue').textContent=parseFloat(el('stepSlider').value).toFixed(1); el('stanceValue').textContent=parseFloat(el('stanceSlider').value).toFixed(1);
    const phys=st.physicalMs==null?'—':`${st.physicalMs.toFixed(1)} ms`;
    const metrics=[
      ['遊脚角 q',`${st.qSwing.toFixed(2)}°`,'STEP hard stop: −20…0°'],
      ['本体ロール θ',`${st.roll.toFixed(2)}°`,'RWが主に制御'],
      ['足首中心移動',`${travel(st.qSwing).toFixed(2)} mm`,`最大 ${G.maxTravel.toFixed(3)} mm`],
      ['接地境界',`${rootAt(st.qStance,st.qSwing).toFixed(2)}°`,'first-contact geometry'],
      ['proxy時間',phys,'脚単独のみscreening']
    ];
    el('metrics').innerHTML=metrics.map(m=>`<div class="metric"><small>${m[0]}</small><strong>${m[1]}</strong><em>${m[2]}</em></div>`).join('');
    const names=phaseNames[mode]; el('phaseGrid').innerHTML=names.map((n,i)=>`<div class="phase ${i===st.phase?'active':''}">${i+1}. ${n}</div>`).join('');
    el('phaseText').textContent=names[st.phase]||names[0];
    el('timelineFill').style.width=`${progress*100}%`; el('timelineCursor').style.left=`${progress*100}%`;
    el('sideBadge').textContent=mode==='passive'?'PASSIVE PROXY':mode==='roll'?'LEG FIXED':'SWING';
    el('frontBadge').textContent=mode==='roll'?'ROLL ONLY':mode==='early'?'EARLY SWITCH':mode==='full'?'FULL STEP':'BODY FIXED';
  }

  function frame(now){
    const dt=(now-last)/1000; last=now;
    if(playing){ progress += dt*parseFloat(el('speedSelect').value)/3.8; if(progress>=1) progress=0; }
    const st=currentState(progress); drawSide(st); drawFront(st); updateUI(st); requestAnimationFrame(frame);
  }
  document.querySelectorAll('.mode').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('.mode').forEach(x=>x.classList.remove('active'));b.classList.add('active');mode=b.dataset.mode;progress=0;}));
  el('playBtn').addEventListener('click',()=>{playing=!playing;el('playBtn').textContent=playing?'❚❚ 一時停止':'▶ 再生';});
  el('resetBtn').addEventListener('click',()=>{progress=0;playing=false;el('playBtn').textContent='▶ 再生';});
  window.addEventListener('resize',()=>{resizeCanvas(sideCanvas);resizeCanvas(frontCanvas);});
  requestAnimationFrame(frame);
})();
