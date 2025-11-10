const API = '';

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

function setStatus(txt, ok=true){
  $('#status').innerText = txt;
  $('#status').style.color = ok ? '#56d364' : '#ff6b6b';
}

async function loadInsights(){
  const region = $('#region').value.trim();
  const limit  = $('#limit').value.trim();
  const auto_fix = $('#auto_fix').checked ? 'true':'false';
  const p = new URLSearchParams({limit, auto_fix});
  if(region) p.append('region', region);

  setStatus('Loading…');
  const res = await fetch(`/insights/top_risk?${p.toString()}`);
  if(!res.ok){ setStatus('Error loading insights', false); return; }
  const rows = await res.json();
  renderRows(rows);
  setStatus(`Loaded ${rows.length} rows`);
}

function renderRows(rows){
  const tb = $('#results tbody');
  tb.innerHTML = '';
  rows.forEach((r, i) => {
    const pass = r.compliance?.pass;
    const v = (r.compliance?.violations || []).join(' · ');
    const m = (r.compliance?.missing_disclaimers || []).join(' · ');

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><input type="checkbox" class="rowcheck"/></td>
      <td>${r.customer_id}</td>
      <td>${r.region}</td>
      <td><b>${r.final_score}</b></td>
      <td>${r.CPI}</td>
      <td>${r.Severity}</td>
      <td>${r.CRS}</td>
      <td>${r.action}</td>
      <td>
        <span class="badge ${pass ? 'pass':'fail'}">${pass ? 'pass':'fail'}</span>
        ${!pass && v ? `<div class="muted">viol: ${v}</div>`:''}
        ${!pass && m ? `<div class="muted">miss: ${m}</div>`:''}
      </td>
      <td class="msg" contenteditable="true">${escapeHtml(r.proposed_text)}</td>
    `;
    // stash original object on the row
    tr._data = r;
    tb.appendChild(tr);
  });

  // header checkbox
  $('#checkAll').checked = false;
  $('#checkAll').onchange = (e)=> $$('#results tbody .rowcheck').forEach(c => c.checked = e.target.checked);
}

function selectedRows(){
  const trs = $$('#results tbody tr');
  return trs.filter(tr => tr.querySelector('.rowcheck').checked);
}

function escapeHtml(s){
  return (s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

async function approveSelected(){
  const trs = selectedRows();
  if(!trs.length){ setStatus('No rows selected', false); return; }

  // collect payload (apply edited message)
  const payload = trs.map(tr => {
    const data = {...tr._data};
    data.proposed_text = tr.querySelector('.msg').innerText.trim();
    return data;
  });

  setStatus('Logging approvals…');
  const res = await fetch('/insights/log', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(payload)
  });
  if(!res.ok){ setStatus('Failed to log approvals', false); return; }
  const j = await res.json();
  setStatus(`Logged ${j.logged} items to action_log.csv`);
}

$('#loadBtn').onclick = loadInsights;
$('#approveSelectedBtn').onclick = approveSelected;
document.addEventListener('DOMContentLoaded', loadInsights);
