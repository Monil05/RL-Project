"""Pre-compute a full RL simulation and render it as an interactive HTML5 Canvas page.

The entire simulation (all 300 steps with real agent decisions) is collected into
a JSON blob, embedded inside a self-contained HTML page, and played back with
smooth 60 fps requestAnimationFrame animation — zero flicker, full controls.
"""

import json

from baseline import FixedTimeController
from config import ProjectConfig
from environment.traffic_environment import TrafficEnvironment, DIRECTIONS


def run_full_simulation(config: ProjectConfig, agent, algorithm: str) -> list[dict]:
    """Run the complete simulation collecting state at every step."""
    env = TrafficEnvironment(config)
    env.reset(config.simulation.random_seed)

    controller = (
        FixedTimeController(config.signal.maximum_green_time)
        if algorithm == "Fixed Time"
        else None
    )

    steps: list[dict] = []
    done = False
    while not done:
        action = (
            controller.choose_action(env)
            if controller
            else agent.choose_action(env.get_state(), explore=False)
        )
        result = env.step(action)

        queues = {
            d: [
                {"id": v.vehicle_id, "m": v.movement.value, "l": v.lane_index}
                for v in env.queues[d]
            ]
            for d in DIRECTIONS
        }
        departed = [
            {"id": v.vehicle_id, "d": v.direction, "m": v.movement.value, "l": v.lane_index}
            for v in env.last_departed_vehicles
        ]
        m = env.metrics()
        steps.append(
            {
                "q": queues,
                "dep": departed,
                "ph": env.signal.current_phase.name,
                "ad": env.signal.active_direction,
                "t": m["time"],
                "tp": m["throughput"],
                "aw": round(float(m["average_waiting_time"]), 2),
                "mw": int(m["maximum_waiting_time"]),
                "rw": round(float(m["cumulative_reward"]), 1),
            }
        )
        done = result.done

    return steps


def build_simulation_page(steps: list[dict], lane_count: int, algorithm: str) -> str:
    """Return a self-contained HTML page with interactive Canvas-based simulation."""
    payload = json.dumps(
        {"lc": lane_count, "alg": algorithm, "steps": steps},
        separators=(",", ":"),
    )
    return _PAGE_TEMPLATE.replace("/*__DATA__*/null", payload)


# ---------------------------------------------------------------------------
# Complete self-contained HTML / CSS / JS page
# ---------------------------------------------------------------------------

_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#0f172a;
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  color:#e2e8f0;
  padding:10px 12px;
}
.wrap{max-width:780px;margin:0 auto}

/* Header row */
.hdr{display:flex;align-items:center;gap:8px;padding:4px 0 8px;flex-wrap:wrap}
.badge{
  padding:3px 10px;border-radius:4px;font-size:11px;font-weight:700;
  background:#1e293b;border:1px solid #334155;color:#a78bfa;
  letter-spacing:.4px;text-transform:uppercase;
}
.step-info{font-size:11px;color:#64748b;margin-left:4px}

/* Buttons */
.btn{
  padding:6px 16px;border:none;border-radius:6px;cursor:pointer;
  font-weight:600;font-size:12px;transition:all .15s;font-family:inherit;
}
.btn:hover{filter:brightness(1.15);transform:translateY(-1px)}
.btn:active{transform:translateY(0)}
.bp{background:#22c55e;color:#fff}
.bpa{background:#f59e0b;color:#fff}
.br{background:#475569;color:#e2e8f0}

/* Speed */
.spd{display:flex;align-items:center;gap:5px;margin-left:auto;font-size:11px;color:#94a3b8}
.spd input[type=range]{width:72px;accent-color:#8b5cf6}
#spdV{font-weight:700;color:#c4b5fd;min-width:28px;text-align:center}

/* Canvas */
#sim{display:block;width:100%;border-radius:10px;box-shadow:0 4px 24px rgba(0,0,0,.4)}

/* Progress */
.prog{
  height:6px;background:#1e293b;border-radius:3px;margin:8px 0 6px;
  overflow:hidden;cursor:pointer;position:relative;
}
.prog:hover{height:8px}
.prog-fill{
  height:100%;border-radius:3px;
  background:linear-gradient(90deg,#3b82f6,#8b5cf6);
  width:0%;transition:width .12s linear;
}

/* Legend */
.leg{display:flex;gap:14px;justify-content:center;padding:4px 0;font-size:11px;color:#94a3b8}
.leg-i{display:flex;align-items:center;gap:4px}
.leg-d{width:10px;height:10px;border-radius:2px;display:inline-block}

/* Metrics */
.mets{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-top:4px}
.met{
  background:#1e293b;padding:8px 6px;border-radius:8px;text-align:center;
  border:1px solid #334155;
}
.met-v{font-size:18px;font-weight:700;color:#38bdf8}
.met-l{font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:.4px;margin-top:2px}

/* Status overlay */
.status{
  position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
  font-size:15px;font-weight:700;color:#94a3b8;pointer-events:none;
  text-transform:uppercase;letter-spacing:1px;opacity:0;
  transition:opacity .3s;
}
.status.show{opacity:1}
.cv-wrap{position:relative;display:inline-block;width:100%}
</style>
</head>
<body>
<div class="wrap">

  <div class="hdr">
    <span class="badge" id="algB"></span>
    <button id="playBtn" class="btn bp">&#9654; Play</button>
    <button id="pauseBtn" class="btn bpa">&#10074;&#10074; Pause</button>
    <button id="resetBtn" class="btn br">&#8634; Reset</button>
    <span id="stepL" class="step-info"></span>
    <div class="spd">
      <span>Speed</span>
      <input type="range" id="spdS" min="0.25" max="4" step="0.25" value="1">
      <span id="spdV">1.0x</span>
    </div>
  </div>

  <div class="cv-wrap">
    <canvas id="sim" width="760" height="760"></canvas>
    <div class="status" id="statusMsg">Click Play to start</div>
  </div>

  <div class="prog" id="progB"><div id="progF" class="prog-fill"></div></div>

  <div class="leg">
    <div class="leg-i"><span class="leg-d" style="background:#ef4444"></span>Straight</div>
    <div class="leg-i"><span class="leg-d" style="background:#3b82f6"></span>Left Turn</div>
    <div class="leg-i"><span class="leg-d" style="background:#22c55e"></span>Right Turn</div>
  </div>

  <div class="mets">
    <div class="met"><div id="mT" class="met-v">0s</div><div class="met-l">Time</div></div>
    <div class="met"><div id="mTp" class="met-v">0</div><div class="met-l">Throughput</div></div>
    <div class="met"><div id="mW" class="met-v">0.00s</div><div class="met-l">Avg Wait</div></div>
    <div class="met"><div id="mMw" class="met-v">0s</div><div class="met-l">Max Wait</div></div>
    <div class="met"><div id="mR" class="met-v">0.0</div><div class="met-l">Reward</div></div>
  </div>

</div>
<script>
(function(){
'use strict';

var D = /*__DATA__*/null;
var LC   = D.lc;
var STEPS= D.steps;
var ALG  = D.alg;
var N    = STEPS.length;

var S = 760, C = S/2;
var RW = LC===2?170:250, HRW = RW/2;

var cv = document.getElementById('sim');
var cx = cv.getContext('2d');

var si=0, st=0, spd=1, playing=false, cars=[], lt=0, af=null;

var playB  = document.getElementById('playBtn');
var pauseB = document.getElementById('pauseBtn');
var resetB = document.getElementById('resetBtn');
var spdSl  = document.getElementById('spdS');
var spdLb  = document.getElementById('spdV');
var stepLb = document.getElementById('stepL');
var progFl = document.getElementById('progF');
var progBr = document.getElementById('progB');
var statusEl = document.getElementById('statusMsg');

document.getElementById('algB').textContent = ALG;

playB.onclick  = doPlay;
pauseB.onclick = doPause;
resetB.onclick = doReset;
spdSl.oninput  = function(){ spd=+this.value; spdLb.textContent=spd.toFixed(1)+'x'; };

progBr.onclick = function(e){
  var r = this.getBoundingClientRect();
  si = Math.max(0, Math.min(N-1, Math.round(((e.clientX-r.left)/r.width)*(N-1))));
  st=0; cars=[];
  render(); uiMetrics();
};

function rs(dir,li){
  var o=LC===2?36:42+li*34, s=LC===2?120:150;
  if(dir==='north') return [C+o,C-s];
  if(dir==='south') return [C-o,C+s];
  if(dir==='east')  return [C+s,C+o];
  return [C-s,C-o];
}
function dd(dir,m){
  var T={north:{left:'west',straight:'south',right:'east'},
         south:{left:'east',straight:'north',right:'west'},
         east:{left:'north',straight:'west',right:'south'},
         west:{left:'south',straight:'east',right:'north'}};
  return T[dir][m];
}
function re(dir,m,li){
  var dest=dd(dir,m), o=LC===2?36:42+li*34;
  if(dest==='north') return [C-o,40];
  if(dest==='south') return [C+o,S-40];
  if(dest==='east')  return [S-40,C-o];
  return [40,C+o];
}
function tc(dir,m,li){
  var r=LC===2?58:50+li*36;
  if(dir==='north') return m==='left'?[C-r,C-r]:[C+r,C-r];
  if(dir==='south') return m==='left'?[C+r,C+r]:[C-r,C+r];
  if(dir==='east')  return m==='left'?[C+r,C-r]:[C+r,C+r];
  return m==='left'?[C-r,C+r]:[C-r,C-r];
}
function aa(dir){
  return {north:270,south:90,east:0,west:180}[dir]*Math.PI/180;
}
function sa(dx,dy){ return Math.atan2(dy,dx)+Math.PI; }
function lp(a,b,t){ return [a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t]; }
function qb(p0,p1,p2,t){
  var u=1-t;
  return [u*u*p0[0]+2*u*t*p1[0]+t*t*p2[0], u*u*p0[1]+2*u*t*p1[1]+t*t*p2[1]];
}
function rp(dir,m,li,t){
  var s=rs(dir,li), e=re(dir,m,li);
  if(m==='straight'){
    var p=lp(s,e,t);
    var dx=e[0]-s[0], dy=e[1]-s[1];
    return{x:p[0],y:p[1],a:Math.atan2(dy,dx)};
  }
  var ct=tc(dir,m,li), p=qb(s,ct,e,t);
  var tx=2*(1-t)*(ct[0]-s[0])+2*t*(e[0]-ct[0]);
  var ty=2*(1-t)*(ct[1]-s[1])+2*t*(e[1]-ct[1]);
  return{x:p[0],y:p[1],a:Math.atan2(ty,tx)};
}
function qp(dir,li,qi){
  var p=rs(dir,li), sp=28;
  if(dir==='north') return [p[0],p[1]-sp*qi];
  if(dir==='south') return [p[0],p[1]+sp*qi];
  if(dir==='east')  return [p[0]+sp*qi,p[1]];
  return [p[0]-sp*qi,p[1]];
}

function render(){
  var step=STEPS[si];
  cx.fillStyle='#0f172a';
  cx.fillRect(0,0,S,S);
  drawRoads();
  drawLanes();
  drawStopLines();
  drawLights(step.ph,step.ad);
  drawQueues(step.q);
  drawMoving();
}

function drawRoads(){
  var L=C-HRW;
  cx.fillStyle='#334155';
  cx.fillRect(L,0,RW,S);
  cx.fillRect(0,L,S,RW);
  cx.fillStyle='#1e293b';
  cx.fillRect(L,L,RW,RW);
}

function drawLanes(){
  var total=LC===2?2:4, lw=RW/total, start=C-HRW;
  for(var i=1;i<total;i++){
    var off=start+lw*i, isC=(i===total/2);
    cx.strokeStyle=isC?'#f59e0b':'#64748b';
    cx.lineWidth=isC?2.5:1.5;
    cx.globalAlpha=0.9;
    cx.setLineDash(isC?[]:[8,10]);
    var edge=C-HRW, far=C+HRW;
    cx.beginPath();cx.moveTo(off,0);cx.lineTo(off,edge);cx.stroke();
    cx.beginPath();cx.moveTo(off,far);cx.lineTo(off,S);cx.stroke();
    cx.beginPath();cx.moveTo(0,off);cx.lineTo(edge,off);cx.stroke();
    cx.beginPath();cx.moveTo(far,off);cx.lineTo(S,off);cx.stroke();
  }
  cx.setLineDash([]);cx.globalAlpha=1;
}

function drawStopLines(){
  var L=C-HRW,R=C+HRW;
  cx.strokeStyle='#ffffff';cx.lineWidth=4;
  cx.beginPath();cx.moveTo(L,L);cx.lineTo(R,L);cx.stroke();
  cx.beginPath();cx.moveTo(L,R);cx.lineTo(R,R);cx.stroke();
  cx.beginPath();cx.moveTo(L,L);cx.lineTo(L,R);cx.stroke();
  cx.beginPath();cx.moveTo(R,L);cx.lineTo(R,R);cx.stroke();
}

function drawLights(ph,ad){
  var pos={
    north:[C+HRW+30,C-HRW-30,'NORTH'],
    south:[C-HRW-30,C+HRW+30,'SOUTH'],
    east: [C+HRW+30,C+HRW+30,'EAST'],
    west: [C-HRW-30,C-HRW-30,'WEST']
  };
  for(var dir in pos){
    var p=pos[dir], col=lightCol(ph,ad,dir);
    drawLightBox(p[0],p[1],p[2],col);
  }
}

function lightCol(ph,ad,dir){
  if(ph==='ALL_RED') return 'red';
  if(ph==='YELLOW') return dir===ad?'yellow':'red';
  return dir===ad?'green':'red';
}

function drawLightBox(x,y,label,color){
  rrect(cx,x-15,y-36,30,72,6);
  cx.fillStyle='#0f172a';cx.fill();
  cx.strokeStyle='#475569';cx.lineWidth=2;cx.stroke();
  var L={red:['#ef4444','#450a0a','#450a0a'],yellow:['#450a0a','#f59e0b','#052e16'],green:['#450a0a','#451a03','#22c55e']}[color];
  var ys=[y-22,y,y+22];
  for(var i=0;i<3;i++){
    cx.fillStyle=L[i];
    cx.beginPath();cx.arc(x,ys[i],7,0,Math.PI*2);cx.fill();
  }
  cx.fillStyle='#94a3b8';
  cx.font='700 10px sans-serif';
  cx.textAlign='center';cx.textBaseline='alphabetic';
  cx.fillText(label,x,y+50);
}

function drawQueues(queues){
  var dirs=['north','south','east','west'];
  for(var di=0;di<dirs.length;di++){
    var dir=dirs[di], q=queues[dir], lc={};
    for(var vi=0;vi<q.length;vi++){
      var v=q[vi], li=v.l;
      lc[li]=(lc[li]||0);
      var p=qp(dir,li,lc[li]);
      drawCar(p[0],p[1],aa(dir),v.m,true);
      lc[li]++;
    }
  }
}

function drawMoving(){
  for(var i=0;i<cars.length;i++){
    var c=cars[i];
    if(c.delay>0) continue;
    var pose=rp(c.d,c.m,c.l,c.progress);
    drawCar(pose.x,pose.y,pose.a,c.m,false);
  }
}

function drawCar(x,y,angle,mov,queued){
  cx.save();
  cx.translate(x,y);
  cx.rotate(angle);
  var al=queued?0.75:1.0;
  var cols={left:'#3b82f6',straight:'#ef4444',right:'#22c55e'};
  var col=cols[mov]||'#ef4444';

  cx.globalAlpha=al*0.2;cx.fillStyle='#000';
  rrect(cx,-12,-5,24,10,3);cx.fill();

  cx.globalAlpha=al;cx.fillStyle=col;
  rrect(cx,-13,-6,26,12,3);cx.fill();
  cx.strokeStyle='#0f172a';cx.lineWidth=0.8;cx.stroke();

  cx.fillStyle='rgba(186,230,253,0.85)';
  rrect(cx,-4,-4,8,8,1.5);cx.fill();

  cx.fillStyle='#fef3c7';
  cx.fillRect(10,-5,2,2);cx.fillRect(10,3,2,2);

  cx.globalAlpha=1;
  cx.restore();
}

function rrect(c,x,y,w,h,r){
  c.beginPath();
  c.moveTo(x+r,y);
  c.lineTo(x+w-r,y);
  c.quadraticCurveTo(x+w,y,x+w,y+r);
  c.lineTo(x+w,y+h-r);
  c.quadraticCurveTo(x+w,y+h,x+w-r,y+h);
  c.lineTo(x+r,y+h);
  c.quadraticCurveTo(x,y+h,x,y+h-r);
  c.lineTo(x,y+r);
  c.quadraticCurveTo(x,y,x+r,y);
  c.closePath();
}

function doPlay(){
  if(playing) return;
  if(si>=N-1&&cars.length===0) doReset();
  playing=true;
  lt=performance.now();
  af=requestAnimationFrame(loop);
  statusEl.classList.remove('show');
  uiBtn();
}
function doPause(){
  playing=false;
  if(af) cancelAnimationFrame(af);
  uiBtn();
}
function doReset(){
  doPause();
  si=0;st=0;cars=[];
  render();uiMetrics();uiBtn();
  statusEl.textContent='Click Play to start';
  statusEl.classList.add('show');
}

function loop(ts){
  if(!playing) return;
  var dt=Math.min((ts-lt)/1000,0.1);
  lt=ts;
  update(dt);
  render();
  uiMetrics();
  if(si<N-1||cars.length>0){
    af=requestAnimationFrame(loop);
  } else {
    playing=false;
    statusEl.textContent='Simulation complete';
    statusEl.classList.add('show');
    uiBtn();
  }
}

function update(dt){
  var sd=0.25/spd;
  st+=dt;
  while(st>=sd&&si<N-1){
    st-=sd;
    si++;
    var step=STEPS[si];
    for(var i=0;i<step.dep.length;i++){
      var v=step.dep[i];
      var delay = i * (0.15 / Math.max(1, step.dep.length));
      cars.push({d:v.d,m:v.m,l:v.l,progress:0,delay:delay});
    }
  }
  var cs=1.4*spd;
  for(var i=0;i<cars.length;i++){
    if(cars[i].delay>0){
      cars[i].delay-=dt;
    } else {
      cars[i].progress=Math.min(1,cars[i].progress+dt*cs);
    }
  }
  cars=cars.filter(function(c){return c.progress<1;});
}

function uiMetrics(){
  var s=STEPS[si];
  document.getElementById('mT').textContent=s.t+'s';
  document.getElementById('mTp').textContent=s.tp;
  document.getElementById('mW').textContent=s.aw.toFixed(2)+'s';
  document.getElementById('mMw').textContent=s.mw+'s';
  document.getElementById('mR').textContent=s.rw.toFixed(1);
  progFl.style.width=(si/(N-1)*100).toFixed(1)+'%';
  stepLb.textContent='Step '+(si+1)+' / '+N;
}
function uiBtn(){
  playB.style.opacity=playing?'0.4':'1';
  pauseB.style.opacity=playing?'1':'0.4';
  playB.style.pointerEvents=playing?'none':'auto';
  pauseB.style.pointerEvents=playing?'auto':'none';
}

statusEl.classList.add('show');
render();uiMetrics();uiBtn();

})();
</script>
</body>
</html>"""
