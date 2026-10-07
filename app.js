/* ================= AI Haptic Vision Navigation Dashboard =================
 * Real data path:  Python/YOLOv8 --POST /api/state--> server.py --GET /api/state (polled here)--> apply()
 * Payload: {"command":"move_right","detections":[{"object":"person","confidence":0.92,"position":"left",
 *           "box":[x1,y1,x2,y2]  (optional, normalised 0..1)}],"log_message":"Person detected on left","demo":false}
 * Everything the UI does goes through apply() -> renderDetections() + setCommand().
 * ======================================================================== */
const $ = id => document.getElementById(id);
const ARROW = '<path d="M4 9h9V4l8 8-8 8v-5H4z"/>';
const CMD = {
  move_left:        {t:"MOVE LEFT",     say:"Move left.",           ic:ARROW, rot:180, c:"blue",   hap:"L", sub:"Path is clear on the left"},
  move_right:       {t:"MOVE RIGHT",    say:"Move right.",          ic:ARROW, rot:0,   c:"blue",   hap:"R", sub:"Path is clear on the right"},
  move_straight:    {t:"MOVE STRAIGHT", say:"Move straight.",       ic:ARROW, rot:270, c:"green",  hap:"B", sub:"Path ahead is clear"},
  move_backward:    {t:"MOVE BACKWARD", say:"Move backward.",       ic:ARROW, rot:90,  c:"purple", hap:"B", sub:"Path ahead is blocked"},
  stop:             {t:"STOP",          say:"Stop.",                ic:'<rect x="5" y="5" width="14" height="14" rx="2"/>', c:"red", hap:"B", sub:"Obstacle very close"},
  wait_for_a_while: {t:"WAIT FOR A WHILE", say:"Wait for a while.", ic:'<rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/>', c:"orange", hap:"B", sub:"Waiting for the path to clear"},
  start_walking:    {t:"START WALKING", say:"Start walking.",       ic:'<path d="M7 4l13 8-13 8z"/>', c:"green", hap:"B", sub:"Path is clear"},
  obstacle_detected:{t:"OBSTACLE DETECTED", say:"Obstacle detected.", ic:'<path d="M8 2h8l6 6v8l-6 6H8l-6-6V8z"/>', c:"red", hap:"B", sub:"Obstacle in the path"},
  system_ready:     {t:"SYSTEM READY",  say:"System ready.",        ic:'<path d="M9 16.2L4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z"/>', c:"cyan", hap:null, sub:"All modules ready"},
  object_detected:  {t:"OBJECT DETECTED", say:"Object detected.",   ic:'<path d="M12 2a10 10 0 100 20 10 10 0 000-20zm0 4a6 6 0 110 12 6 6 0 010-12zm0 3a3 3 0 100 6 3 3 0 000-6z"/>', c:"purple", hap:null, sub:"Analysing object position"},
  slow_down:        {t:"SLOW DOWN",     say:"Slow down.",           ic:'<path d="M12 3l10 18H2z"/>', c:"orange", hap:"B", sub:"Object ahead"}
};
const COLORS = ["#16a34a","#2563eb","#ef4444","#7c3aed","#f59e0b","#06b6d4"];
const S = {mode:"idle", started:false, lastCmd:null, lastSig:"", lastMsg:null, seq:0, pyAt:0, stream:false, cam:null, played:{}, demoTimer:null, colors:{}};

/* ---------- small helpers ---------- */
const cap = s => s.charAt(0).toUpperCase() + s.slice(1);
const setDot = (id, txt, cls) => { const e = $(id); e.textContent = txt; e.className = "dot " + cls; };
const LOGC = {sys:"#16a34a", det:"#2563eb", nav:"#f59e0b", voice:"#ea580c", hap:"#7c3aed"};
function log(msg, type="sys"){
  const li = document.createElement("li");
  li.innerHTML = `<time>${new Date().toTimeString().slice(0,8)}</time><i style="--c:${LOGC[type]}"></i><span>${msg}</span>`;
  $("log").prepend(li); while ($("log").children.length > 80) $("log").lastChild.remove();
}
setInterval(() => { const d = new Date(); $("date").textContent = d.toLocaleDateString("en-GB",{day:"2-digit",month:"short",year:"numeric"}); $("time").textContent = d.toLocaleTimeString(); }, 1000);

/* ---------- mode / status (camera, AI, pipeline) ---------- */
function setMode(m){
  S.mode = m;
  const chip = {idle:"STANDBY", preview:"CAMERA PREVIEW — AI NOT CONNECTED", demo:"DEMO MODE", python:"AI VISION ACTIVE"}[m];
  $("mode").textContent = chip;
  $("demoTag").hidden = m !== "demo";
  $("camMsg").style.visibility = (m === "demo" || m === "python") && !S.cam ? "hidden" : "visible";
  $("btnDemo").classList.toggle("on", m === "demo");
  $("btnDemo").textContent = m === "demo" ? "◈ Demo Mode: ON" : "◈ Demo Mode";
  const live = $("live");
  if (m === "demo")        { live.textContent = "DEMO"; live.className = "tagpill demo"; }
  else if (S.cam || S.stream){ live.textContent = "● LIVE"; live.className = "tagpill live"; }
  else                     { live.textContent = "OFF"; live.className = "tagpill off"; }
  if (m === "python") setDot("v-yolo", "Ready", "ok");
  else if (m === "demo") setDot("v-yolo", "Demo data", "demo");
  else setDot("v-yolo", "Not connected", "off");
  const lit = m === "idle" && !S.cam ? 0 : m === "preview" ? 1 : 2;
  [...$("pipe").children].forEach((li,i) => li.classList.toggle("on", i < lit + (S.lastCmd ? 3 : 0)));
}

/* ---------- audio: uploaded MP3 files only ---------- */
const player = new Audio();
player.onended = () => { $("vState").textContent = "READY"; $("vState").className = "tagpill ready"; $("wave").classList.remove("on"); };
for (let i = 0; i < 28; i++) { const b = document.createElement("i"); b.style.height = (6 + Math.abs(Math.sin(i * .7)) * 26) + "px"; $("wave").append(b); }
function playCommand(cmd){
  const f = AUDIO_MAP[cmd], now = Date.now();
  if (!f || (S.played[cmd] && now - S.played[cmd] < 3000)) return;       // cooldown: same command max once / 3 s
  S.played[cmd] = now;
  $("vText").textContent = "“" + CMD[cmd].say + "”";
  player.src = AUDIO_DIR + f;
  player.play().then(() => {
    $("vState").textContent = "▶ PLAYING"; $("vState").className = "tagpill playing"; $("wave").classList.add("on");
    log("Voice — " + CMD[cmd].say.replace(".", ""), "voice");
  }).catch(() => { $("vText").textContent = "Click Start System to enable audio"; });
}

/* ---------- haptic simulation (visual only) ---------- */
let hapTimer;
function simulateHaptic(cmd){
  const side = CMD[cmd].hap; if (!side) return;
  $("hap").className = "hap " + side; $("hapState").textContent = "VIBRATION ACTIVE"; $("hapState").className = "hapbtn on";
  log("Haptic — Simulation active", "hap");
  clearTimeout(hapTimer);
  hapTimer = setTimeout(() => { $("hap").className = "hap"; $("hapState").textContent = "VIBRATION READY"; $("hapState").className = "hapbtn"; }, 2200);
}

/* ---------- navigation tile ---------- */
function setCommand(raw, sub){
  const cmd = AUDIO_ALIAS[raw] || raw, c = CMD[cmd]; if (!c) return;
  $("tile").className = "tile " + c.c;
  $("tileIcon").innerHTML = c.ic; $("tileIcon").style.transform = `rotate(${c.rot || 0}deg)`;
  $("tileText").textContent = c.t; $("tileSub").textContent = sub || c.sub;
  if (cmd === S.lastCmd) return;                         // act only when the command changes
  S.lastCmd = cmd; $("tile").classList.add("pop");
  log("Navigation — " + c.say.replace(".", ""), "nav");
  playCommand(cmd); simulateHaptic(cmd); setMode(S.mode);
}

/* ---------- detections ---------- */
function norm(d){
  const label = (d.object || d.label || "object").toLowerCase(); let pos = (d.position || "").toLowerCase();
  if (!pos && d.box) { const cx = (d.box[0] + d.box[2]) / 2; pos = cx < 1/3 ? "left" : cx > 2/3 ? "right" : "center"; }
  return {label, conf: +d.confidence || 0, pos: pos || "center", box: d.box};
}
const colorOf = l => S.colors[l] || (S.colors[l] = COLORS[Object.keys(S.colors).length % COLORS.length]);
function renderDetections(list){
  $("objBody").innerHTML = list.length ? "" : '<tr><td colspan="4" class="mut">No objects detected.</td></tr>';
  $("boxes").innerHTML = "";
  ["left","center","right"].forEach(p => $("z-" + p).innerHTML = "");
  list.forEach((d, i) => {
    const col = colorOf(d.label), pct = Math.round(d.conf * 100) + "%";
    $("objBody").insertAdjacentHTML("beforeend", `<tr><td>${i+1}</td><td>${cap(d.label)}</td><td>${pct}</td><td><span class="ppos ${d.pos}">${cap(d.pos)}</span></td></tr>`);
    $("z-" + d.pos).insertAdjacentHTML("beforeend", `<div class="zchip" style="--c:${col}">${cap(d.label)}<small>${d.conf.toFixed(2)}</small></div>`);
    if (d.box) { const [x1,y1,x2,y2] = d.box;
      $("boxes").insertAdjacentHTML("beforeend", `<div class="bb" style="--c:${col};left:${x1*100}%;top:${y1*100}%;width:${(x2-x1)*100}%;height:${(y2-y1)*100}%"><span>${cap(d.label)} ${pct}</span></div>`); }
  });
}

/* ===== INTEGRATION POINT: one entry for BOTH the Python bridge and Demo Mode ===== */
function apply(p){
  const dets = (p.detections || []).map(norm); renderDetections(dets);
  const sig = dets.map(d => d.label + d.pos).join();
  if (p.log_message && p.log_message !== S.lastMsg) { S.lastMsg = p.log_message; log(p.log_message, "det"); S.lastSig = sig; }
  else if (sig !== S.lastSig) { S.lastSig = sig; dets.slice(0, 3).forEach(d => log(`${cap(d.label)} detected — ${cap(d.pos)}`, "det")); }
  if (p.command) setCommand(p.command, p.sub);
}

/* ---------- Python bridge (real YOLOv8 data arrives here) ---------- */
async function poll(){
  try {
    const s = await (await fetch("/api/state", {cache:"no-store"})).json();
    const fresh = s.age !== null && s.age < 2;
    if (fresh && s.demo !== true) {
      if (S.mode === "demo") stopDemo();
      if (!S.pyAt) log("Python bridge connected — AI vision active", "sys");
      S.pyAt = Date.now();
      if (S.mode !== "python") setMode("python");
      if (s.has_frame && !S.stream) { S.stream = true; $("stream").src = "/stream"; $("stream").style.display = "block"; $("video").style.display = "none"; $("camMsg").hidden = true; setDot("v-cam", "Active (Python)", "ok"); }
      if (s.seq !== S.seq) { S.seq = s.seq; apply(s); }
    } else if (S.pyAt && !fresh) { S.pyAt = 0; setMode(S.cam ? "preview" : "idle"); log("Python bridge disconnected", "sys"); }
  } catch (e) { /* opened without server.py: dashboard still works in Demo Mode */ }
}
setInterval(poll, 250);

/* ---------- camera + start/stop ---------- */
async function startSystem(){
  S.started = true; $("btnStart").disabled = true;
  setDot("v-voice", "Ready", "ok"); log("System ready", "sys");
  if (S.stream || S.mode === "python") {
    setDot("v-cam", "Active (Python)", "ok");
    $("camMsg").hidden = true;
    setCommand("system_ready");
    return;
  }
  try {
    S.cam = await navigator.mediaDevices.getUserMedia({video:{width:1280, height:720}});
    $("video").srcObject = S.cam; $("camMsg").hidden = true; setDot("v-cam", "Active", "ok"); log("Camera activated", "sys");
    if (S.mode === "idle") setMode("preview"); else setMode(S.mode);
  } catch (e) {
    if (!S.stream) {
      setDot("v-cam", "Unavailable", "err"); $("camMsg").innerHTML = "<span>Camera permission denied or camera in use.<br>Demo Mode still works.</span>";
    }
    log("Camera unavailable: " + (e.name || "error"), "sys");
  }
  setCommand("system_ready");
}
function stopSystem(){
  stopDemo(); if (S.cam) S.cam.getTracks().forEach(t => t.stop());
  S.cam = null; S.started = false; S.lastCmd = null; S.lastSig = ""; S.played = {};
  $("video").srcObject = null; $("camMsg").hidden = false; $("camMsg").innerHTML = "<span>Press <b>Start System</b> to open the laptop camera</span>";
  player.pause(); player.onended(); $("btnStart").disabled = false;
  setDot("v-cam", "Off", "off"); setDot("v-voice", "Standby", "off");
  $("tile").className = "tile idle"; $("tileText").textContent = "STANDBY"; $("tileSub").textContent = "Waiting for a command";
  $("tileIcon").innerHTML = '<path d="M12 3a9 9 0 100 18 9 9 0 000-18z" opacity=".25"/>'; $("tileIcon").style.transform = "";
  $("vText").textContent = "—"; renderDetections([]); setMode("idle"); log("System stopped", "sys");
}
$("btnStart").onclick = startSystem; $("btnStop").onclick = stopSystem; $("btnClear").onclick = () => $("log").innerHTML = "";

/* ================= DEMO MODE (simulated data, NOT YOLOv8) =================
 * Keep separate from the real layer above; delete this block when no longer needed. */
const box = (x, w, h=.55) => [x, .9 - h, x + w, .9];
const DEMO = [
  {command:"system_ready",     detections:[], log_message:"System ready", sub:"Demo: system check complete"},
  {command:"object_detected",  detections:[{object:"person", confidence:.92, position:"left", box:box(.08,.2,.6)}], log_message:"Object detected", sub:"Demo: object found on the left"},
  {command:"move_right",       detections:[{object:"person", confidence:.92, position:"left", box:box(.08,.2,.6)}], log_message:"Person detected — Left", sub:"Demo: obstacle detected on left"},
  {command:"slow_down",        detections:[{object:"chair", confidence:.81, position:"center", box:box(.4,.2,.4)},{object:"person", confidence:.9, position:"left", box:box(.08,.2,.6)}], log_message:"Chair detected — Center", sub:"Demo: object ahead"},
  {command:"stop",             detections:[{object:"chair", confidence:.86, position:"center", box:box(.36,.28,.6)}], log_message:"Chair very close — Center", sub:"Demo: obstacle very close"},
  {command:"move_left",        detections:[{object:"car", confidence:.88, position:"right", box:box(.66,.3,.45)},{object:"chair", confidence:.8, position:"center", box:box(.4,.2,.4)}], log_message:"Car detected — Right", sub:"Demo: obstacle detected on right"},
  {command:"wait_for_a_while", detections:[{object:"person", confidence:.89, position:"center", box:box(.4,.2,.55)}], log_message:"Person crossing — Center", sub:"Demo: waiting for the path to clear"},
  {command:"obstacle_detected",detections:[{object:"chair", confidence:.84, position:"center", box:box(.38,.25,.5)}], log_message:"Obstacle in path", sub:"Demo: obstacle in the path"},
  {command:"move_backward",    detections:[{object:"table", confidence:.76, position:"center", box:box(.2,.6,.45)}], log_message:"Table blocks path", sub:"Demo: path ahead blocked"},
  {command:"move_straight",    detections:[], log_message:"Path clear", sub:"Demo: nothing in the way"},
  {command:"start_walking",    detections:[], log_message:"Start walking", sub:"Demo: path clear"}
];
let demoI = 0;
function startDemo(){
  if (S.mode === "python") return log("Demo disabled: Python bridge is sending real data", "sys");
  S.lastCmd = null; S.played = {}; setMode("demo"); log("Demo Mode ON — simulated data, not YOLOv8", "sys");
  const step = () => { const d = DEMO[demoI++ % DEMO.length]; S.lastMsg = null; apply(d); };
  step(); S.demoTimer = setInterval(step, 4500);
}
function stopDemo(){ if (S.mode !== "demo") return; clearInterval(S.demoTimer); renderDetections([]); setMode(S.cam ? "preview" : "idle"); log("Demo Mode OFF", "sys"); }
$("btnDemo").onclick = () => S.mode === "demo" ? stopDemo() : startDemo();

setMode("idle"); log("Dashboard loaded — press Start System or Demo Mode", "sys");
