const API_BASE="http://127.0.0.1:8000";
let currentStudent=JSON.parse(localStorage.getItem("campusprint_student")||"null"),currentOrder=null,currentAdmin=JSON.parse(localStorage.getItem("campusprint_admin")||"null");
const $=id=>document.getElementById(id);
function showPage(id){document.querySelectorAll(".page").forEach(p=>p.classList.remove("active"));$(id)?.classList.add("active");window.scrollTo({top:0,behavior:"smooth"});if(id==="order-tracking")loadStudentOrders();if(id==="admin-dashboard")loadAdminOrders();}
document.addEventListener("click",e=>{const b=e.target.closest("[data-page]");if(b)showPage(b.dataset.page);});
async function api(path,opt={}){const r=await fetch(API_BASE+path,opt);let d=null;try{d=await r.json()}catch{}if(!r.ok)throw Error(d?.detail||`Request failed (${r.status})`);return d;}
function err(e){
  return e instanceof TypeError
    ? "Cannot connect to backend. Make sure FastAPI is running with: uvicorn main:app --reload"
    : e.message;
}
function loading(b,on,t){if(!b)return;if(on){b.dataset.t=b.textContent;b.disabled=true;b.textContent=t}else{b.disabled=false;b.textContent=b.dataset.t||t}}
function esc(v){return String(v??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;");}
const IST_TIMEZONE="Asia/Kolkata";
function formatEta(iso){
  if(!iso)return "—";
  const d=new Date(iso);
  return Number.isNaN(d.getTime())?"—":d.toLocaleTimeString("en-IN",{hour:"2-digit",minute:"2-digit",hour12:true,timeZone:IST_TIMEZONE});
}
function liveRemaining(iso){
  if(!iso)return "—";
  const ms=new Date(iso).getTime()-Date.now();
  if(ms<=0)return "Ready soon";
  const total=Math.ceil(ms/60000),h=Math.floor(total/60),m=total%60;
  return h?`${h}h ${m}m remaining`:`${total} min remaining`;
}
function countdownMinutes(mins){
  if(mins===null||mins===undefined)return "—";
  if(mins<=0)return "Next";
  const m=Math.ceil(mins);
  if(m<60)return `${m} min`;
  const h=Math.floor(m/60),r=m%60;
  return r?`${h}h ${r}m`:`${h}h`;
}
function updateLiveTimers(){
  document.querySelectorAll("[data-eta]").forEach(el=>{el.textContent=liveRemaining(el.dataset.eta);});
  document.querySelectorAll("[data-eta-clock]").forEach(el=>{el.textContent=formatEta(el.dataset.etaClock);});
}
function calc(){const p=Math.max(1,+$("pages").value||1),c=Math.max(1,+$("copies").value||1),total=p*c,type=$("color").value,slot=document.querySelector('input[name="slot"]:checked')?.value||"Green Slot",cost=total*(type==="color"?10:2),fee=slot==="Urgent"?5:0;$("summary-pages").textContent=total;$("summary-print-cost").textContent=`₹${cost}`;$("summary-priority-fee").textContent=`₹${fee}`;$("summary-price").textContent=`₹${cost+fee}`;return{p,c,total,type,slot,cost,fee};}
$("student-login-form").addEventListener("submit",async e=>{e.preventDefault();const f=new FormData();f.append("registration_number",$("student-registration").value.trim());f.append("password",$("student-roll").value.trim());const b=e.submitter;loading(b,true,"Checking...");try{const r=await api("/api/student/login",{method:"POST",body:f});currentStudent={registrationNumber:r.registrationNumber,rollNumber:r.rollNumber};localStorage.setItem("campusprint_student",JSON.stringify(currentStudent));$("order-roll").value=r.rollNumber;showPage("student-dashboard")}catch(x){alert(err(x))}finally{loading(b,false,"Login")}});
$("admin-login-form").addEventListener("submit",async e=>{e.preventDefault();const f=new FormData();f.append("admin_id",$("admin-id").value.trim());f.append("password",$("admin-password").value.trim());const b=e.submitter;loading(b,true,"Checking...");try{const r=await api("/api/admin/login",{method:"POST",body:f});currentAdmin=r;localStorage.setItem("campusprint_admin",JSON.stringify(r));showPage("admin-dashboard");loadAdminOrders()}catch(x){alert(err(x))}finally{loading(b,false,"Login")}});
["pages","copies"].forEach(id=>$(id).addEventListener("input",calc));["color","sides"].forEach(id=>$(id).addEventListener("change",calc));document.addEventListener("change",e=>{if(e.target.matches('input[name="slot"]'))calc();if(e.target.id==="print-file")$("file-label").textContent=e.target.files[0]?.name||"Upload your document";});
$("order-form").addEventListener("submit",async e=>{e.preventDefault();if(!currentStudent){alert("Please log in first.");showPage("student-login");return}const file=$("print-file").files[0],printer=document.querySelector('input[name="printer"]:checked')?.value,slot=document.querySelector('input[name="slot"]:checked')?.value;if(!file||!printer||!slot){alert("Please complete all selections.");return}const x=calc(),f=new FormData();f.append("registration_number",currentStudent.registrationNumber);f.append("roll_number",currentStudent.rollNumber);f.append("printer",printer);f.append("print_type",x.type);f.append("sides",$("sides").value);f.append("pages",x.p);f.append("copies",x.c);f.append("priority_slot",slot);f.append("document",file);const b=e.submitter;loading(b,true,"Submitting...");try{currentOrder=await api("/api/orders",{method:"POST",body:f});$("payment-printer").textContent=currentOrder.printer;$("payment-type").textContent=currentOrder.printType==="color"?"Colour":"Black & White";$("payment-pages").textContent=currentOrder.totalPages;$("payment-slot").textContent=currentOrder.slot;$("payment-price").textContent=`₹${currentOrder.amount}`;showPage("payment-page")}catch(x){alert(err(x))}finally{loading(b,false,"Continue to Payment →")}});
$("pay-button").addEventListener("click",async e=>{if(!currentOrder)return;const b=e.currentTarget;loading(b,true,"Processing payment...");try{const f=new FormData();f.append("payment_method","CampusPrint Demo Payment");const r=await api(`/api/orders/${encodeURIComponent(currentOrder.id)}/payment/demo`,{method:"POST",body:f});currentOrder=r.order;$("success-order-number").textContent=`ORDER #${currentOrder.id}`;showPage("order-success")}catch(x){alert(err(x))}finally{loading(b,false,"Pay Now →")}});
async function loadStudentOrders(){const c=$("tracking-list");if(!currentStudent){c.innerHTML='<div class="empty-state"><h2>Student login required.</h2></div>';return}try{const q=`?registration_number=${encodeURIComponent(currentStudent.registrationNumber)}&roll_number=${encodeURIComponent(currentStudent.rollNumber)}`,a=await api("/api/orders"+q);c.innerHTML=a.length?a.map(renderTrack).join(""):'<div class="empty-state"><h2>No orders yet.</h2></div>'}catch(x){c.innerHTML=`<div class="empty-state"><h2>Backend unavailable.</h2><p>${esc(err(x))}</p></div>`}}
function renderTrack(o){
  const si={Pending:0,Ready:1,Completed:2}[o.status]??0;
  const steps=["Order placed","Ready","Completed"];
  const queueInfo=o.status==="Pending"?`<div class="queue-info">
    <div><span>Queue position</span><strong>#${o.queuePosition??"—"}</strong></div>
    <div><span>Time remaining</span><strong data-eta="${esc(o.etaUtc)}">${liveRemaining(o.etaUtc)}</strong></div>
    <div><span>ETA (IST)</span><strong data-eta-clock="${esc(o.etaUtc)}">${formatEta(o.etaUtc)}</strong></div>
    <div><span>Print time</span><strong>${countdownMinutes(o.estimatedPrintMinutes)}</strong></div>
  </div>`:"";
  return `<article class="tracking-card"><div class="tracking-header"><div><span class="order-id">#${esc(o.id)}</span><h2>${esc(o.filename)}</h2></div><span class="status-badge">${esc(o.status.toUpperCase())}</span></div>
  <div class="progress-tracker">${steps.map((s,i)=>`<div class="progress-step ${i<si?"done":i===si?"current":""}"><span>${i<si?"✓":i+1}</span><p>${s}</p></div>${i<2?'<div class="progress-line"></div>':""}`).join("")}</div>
  ${queueInfo}${o.status==="Pending"?`<div class="queue-fairness"><span>${o.starvationProtected?"Fairness boost active":"Smart queue"}</span><strong>${o.agingBonusPages>0?`Waiting bonus: -${o.agingBonusPages} page score`:"Shortest-job priority"}</strong></div>`:""}<div class="tracking-details"><div><span>Printer</span><strong>${esc(o.printer)}</strong></div><div><span>Pages</span><strong>${o.totalPages}</strong></div><div><span>Priority</span><strong>${esc(o.slot)}</strong></div><div><span>Amount</span><strong>₹${o.amount}</strong></div></div></article>`;
}
async function loadAdminOrders(){
  try{
    if(!currentAdmin){return}
    const a=await api("/api/orders");
    const visible=a.filter(o=>o.printer===currentAdmin.printer);
    $("stat-active").textContent=visible.filter(o=>o.status==="Pending").length;
    $("stat-printing").textContent=visible.filter(o=>o.status==="Ready").length;
    $("stat-completed").textContent=visible.filter(o=>o.status==="Completed").length;
    $("stat-revenue").textContent=`₹${visible.reduce((s,o)=>s+Number(o.amount||0),0)}`;
    $("admin-orders").innerHTML=visible.length?visible.map(o=>`<div class="table-row">
      <span>#${esc(o.id)}</span><span>${esc(o.rollNumber)}</span><span>${esc(o.printer)}</span>
      <span class="${o.slot==="Urgent"?"priority-urgent":"priority-green"}">${esc(o.slot)}</span>
      <span>${o.status==="Pending"?`#${o.queuePosition??"—"}`:"—"}</span>
      <span>${o.status==="Pending"?`<span data-eta="${esc(o.etaUtc)}">${liveRemaining(o.etaUtc)}</span>`:"—"}</span>
      <span>${o.status==="Pending"?`<span data-eta-clock="${esc(o.etaUtc)}">${formatEta(o.etaUtc)}</span>`:"—"}</span>
      <span>${o.status==="Pending"?(o.starvationProtected?"Fairness boost":"-"+o.agingBonusPages+" page score"):"—"}</span>
      <span><select class="status-select" data-order-id="${esc(o.id)}">
        <option ${o.status==="Pending"?"selected":""}>Pending</option>
        <option ${o.status==="Ready"?"selected":""}>Ready</option>
        <option ${o.status==="Completed"?"selected":""}>Completed</option>
      </select></span><span>₹${o.amount}</span></div>`).join(""):'<div class="empty-state"><h2>No orders for this printer.</h2></div>'
  }catch(x){$("admin-orders").innerHTML=`<div class="empty-state"><h2>Backend unavailable.</h2><p>${esc(err(x))}</p></div>`}
}
document.addEventListener("change",async e=>{
  if(!e.target.matches(".status-select"))return;
  const f=new FormData();f.append("status",e.target.value);
  try{await api(`/api/orders/${encodeURIComponent(e.target.dataset.orderId)}/status`,{method:"PATCH",body:f});await loadAdminOrders()}
  catch(x){alert(err(x));await loadAdminOrders()}
});
if(currentStudent){$("student-registration").value=currentStudent.registrationNumber||"";$("student-roll").value=currentStudent.rollNumber||"";$("order-roll").value=currentStudent.rollNumber||""}
calc();
setInterval(()=>{if($("order-tracking")?.classList.contains("active"))loadStudentOrders();if($("admin-dashboard")?.classList.contains("active"))loadAdminOrders()},30000);

setInterval(updateLiveTimers,1000);
