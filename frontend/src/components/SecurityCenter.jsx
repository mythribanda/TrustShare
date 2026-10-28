import React,{useEffect,useState}from'react';
import{ShieldCheck,X,RefreshCw,Link2,Copy,Activity,Users,HardDrive,LockKeyhole,BarChart3,Share2,Download,Trash2,FileText,Upload,ShieldAlert,ExternalLink,KeyRound,MonitorSmartphone}from'lucide-react';

const API=import.meta.env.VITE_API_URL||'http://localhost:8000';
const bytesText=value=>{const n=Number(value||0);if(n<1024)return n+' B';if(n<1048576)return(n/1024).toFixed(1)+' KB';if(n<1073741824)return(n/1048576).toFixed(1)+' MB';return(n/1073741824).toFixed(2)+' GB'};
const titleText=value=>String(value).replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());

export default function SecurityCenter({token,user,onClose}){
const[tab,setTab]=useState('user');
const[data,setData]=useState(null);
const[error,setError]=useState('');
const[busy,setBusy]=useState(false);
const[days,setDays]=useState('30');
const[hours,setHours]=useState('24');
const[shareFileId,setShareFileId]=useState('');
const[shareHours,setShareHours]=useState('24');
const[shareLimit,setShareLimit]=useState('');
const[sharePassword,setSharePassword]=useState('');
const[sharePermission,setSharePermission]=useState('download');
const[shareUrl,setShareUrl]=useState('');
const[directFileId,setDirectFileId]=useState('');
const[directEmail,setDirectEmail]=useState('');
const[directPermission,setDirectPermission]=useState('view_download');
const[vaultStatus,setVaultStatus]=useState(null);
const[vaultPassword,setVaultPassword]=useState('');
const[vaultSetupPassword,setVaultSetupPassword]=useState('');
const[vaultNewPassword,setVaultNewPassword]=useState('');
const[vaultFiles,setVaultFiles]=useState([]);
const[vaultUpload,setVaultUpload]=useState(null);
const[sharingReport,setSharingReport]=useState(null);
const[mfaStatus,setMfaStatus]=useState(null);
const[mfaSetup,setMfaSetup]=useState(null);
const[mfaCode,setMfaCode]=useState('');
const[backupCodes,setBackupCodes]=useState([]);
const[disablePassword,setDisablePassword]=useState('');
const[disableCode,setDisableCode]=useState('');
const[sessions,setSessions]=useState([]);
const[revokedAll,setRevokedAll]=useState(false);

async function apiFetch(path,options={}){
const headers={Authorization:'Bearer '+token,...(options.headers||{})};
const response=await fetch(API+path,{...options,headers});
const type=response.headers.get('content-type')||'';
const body=type.includes('application/json')?await response.json():await response.text();
if(!response.ok)throw new Error(body?.detail||body?.message||'Request failed ('+response.status+')');
return body;
}
async function load(){
setBusy(true);setError('');
try{
if(tab==='user')setData(await apiFetch('/api/dashboard/user'));
else if(tab==='analytics')setData(await apiFetch('/api/analytics/files?days='+days));
else if(tab==='security')setData(await apiFetch('/api/dashboard/security?hours='+hours));
else if(tab==='admin')setData(await apiFetch('/api/dashboard/admin'));
else if(tab==='links')setData(await apiFetch('/api/shares/links'));
else if(tab==='shared')setData(await apiFetch('/api/shares/direct'));
else if(tab==='account'){const [mfa,activeSessions]=await Promise.all([apiFetch('/api/auth/mfa/status'),apiFetch('/api/auth/sessions')]);setMfaStatus(mfa);setSessions(activeSessions);setData({stats:{mfa_enabled:mfa.enabled,active_sessions:activeSessions.length,backup_codes_remaining:mfa.backup_codes_remaining}});setRevokedAll(false)}
else if(tab==='vault'){const status=await apiFetch('/api/vault/status');setVaultStatus(status);setData(status);if(status.configured&&vaultPassword){setVaultFiles(await apiFetch('/api/vault/files',{headers:{'X-Vault-Password':vaultPassword}}));}}
}catch(e){setError(e.message)}finally{setBusy(false)}
}
useEffect(()=>{load()},[tab,days,hours]);

async function createLink(e){
e.preventDefault();setError('');setShareUrl('');
try{
const body={expires_in_hours:Number(shareHours),permission:sharePermission};
if(shareLimit!=='')body.max_downloads=Number(shareLimit);
if(sharePassword)body.password=sharePassword;
const result=await apiFetch('/api/files/'+encodeURIComponent(shareFileId)+'/shares',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
setShareUrl(result.url);setSharePassword('');setTab('links');setData(await apiFetch('/api/shares/links'));
}catch(e){setError(e.message)}
}
async function createDirectShare(e){
e.preventDefault();setError('');
try{
await apiFetch('/api/files/'+encodeURIComponent(directFileId)+'/direct-shares',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:directEmail,permission:directPermission})});
setDirectEmail('');setTab('shared');setData(await apiFetch('/api/shares/direct'));
}catch(e){setError(e.message)}
}
async function revokeLink(id){
try{await apiFetch('/api/shares/'+id+'/revoke',{method:'POST'});await load()}catch(e){setError(e.message)}
}
async function revokeGrant(id){
try{await apiFetch('/api/shares/direct/'+id,{method:'DELETE'});await load()}catch(e){setError(e.message)}
}
async function setupVault(e){
e.preventDefault();setError('');
try{await apiFetch('/api/vault/setup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:vaultSetupPassword})});setVaultSetupPassword('');await load()}catch(e){setError(e.message)}
}
async function unlockVault(e){
e.preventDefault();setError('');
try{setVaultFiles(await apiFetch('/api/vault/files',{headers:{'X-Vault-Password':vaultPassword}}));setVaultStatus(await apiFetch('/api/vault/status'))}catch(e){setError(e.message)}
}
async function uploadVaultFile(e){
e.preventDefault();if(!vaultUpload)return;setError('');
try{const body=new FormData();body.append('file',vaultUpload);await apiFetch('/api/vault/files/upload',{method:'POST',headers:{'X-Vault-Password':vaultPassword},body});setVaultUpload(null);setVaultFiles(await apiFetch('/api/vault/files',{headers:{'X-Vault-Password':vaultPassword}}));setVaultStatus(await apiFetch('/api/vault/status'))}catch(e){setError(e.message)}
}
async function vaultDownload(item){
try{const response=await fetch(API+'/api/vault/files/'+item.id+'/download',{headers:{Authorization:'Bearer '+token,'X-Vault-Password':vaultPassword}});if(!response.ok){const body=await response.json();throw Error(body.detail||'Download failed')}const blob=await response.blob();const href=URL.createObjectURL(blob);const a=document.createElement('a');a.href=href;a.download=item.name;document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(href)}catch(e){setError(e.message)}
}
async function vaultPreview(item){
try{const response=await fetch(API+'/api/vault/files/'+item.id+'/preview',{headers:{Authorization:'Bearer '+token,'X-Vault-Password':vaultPassword}});if(!response.ok){const body=await response.json();throw Error(body.detail||'Preview is not available for this file type')}const blob=await response.blob();const href=URL.createObjectURL(blob);window.open(href,'_blank','noopener,noreferrer');setTimeout(()=>URL.revokeObjectURL(href),60000)}catch(e){setError(e.message)}
}
async function vaultRename(item){
const name=window.prompt('New file name',item.name);
if(!name||name.trim()===item.name)return;
setError('');
try{await apiFetch('/api/vault/files/'+item.id,{method:'PATCH',headers:{'Content-Type':'application/json','X-Vault-Password':vaultPassword},body:JSON.stringify({name:name.trim()})});setVaultFiles(await apiFetch('/api/vault/files',{headers:{'X-Vault-Password':vaultPassword}}));setVaultStatus(await apiFetch('/api/vault/status'))}catch(e){setError(e.message)}
}
async function deleteVaultFile(id){
if(!window.confirm('Permanently delete this encrypted vault file?'))return;
try{await apiFetch('/api/vault/files/'+id,{method:'DELETE',headers:{'X-Vault-Password':vaultPassword}});setVaultFiles(await apiFetch('/api/vault/files',{headers:{'X-Vault-Password':vaultPassword}}));setVaultStatus(await apiFetch('/api/vault/status'))}catch(e){setError(e.message)}
}
async function changeVaultPassword(e){
e.preventDefault();setError('');
try{await apiFetch('/api/vault/change-password',{method:'POST',headers:{'Content-Type':'application/json','X-Vault-Password':vaultPassword},body:JSON.stringify({new_password:vaultNewPassword})});setVaultPassword(vaultNewPassword);setVaultNewPassword('');setVaultFiles(await apiFetch('/api/vault/files',{headers:{'X-Vault-Password':vaultNewPassword}}));setVaultStatus(await apiFetch('/api/vault/status'))}catch(e){setError(e.message)}
}
async function resetVault(){
const accountPassword=window.prompt('This permanently deletes every file in your Secure Vault. Enter your account password to confirm:');
if(!accountPassword)return;
if(!window.confirm('FINAL WARNING: your encrypted vault files will be permanently deleted. Continue?'))return;
setError('');
try{await apiFetch('/api/vault/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:accountPassword})});setVaultPassword('');setVaultSetupPassword('');setVaultNewPassword('');setVaultFiles([]);setVaultStatus({configured:false,file_count:0});setData({configured:false,file_count:0});setNotice?.('')}
catch(e){setError(e.message)}
}
async function beginMfaSetup(){
setError('');setBackupCodes([]);
try{setMfaSetup(await apiFetch('/api/auth/mfa/setup',{method:'POST'}))}catch(e){setError(e.message)}
}
async function confirmMfa(e){
e.preventDefault();setError('');
try{const result=await apiFetch('/api/auth/mfa/confirm',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:mfaCode})});setBackupCodes(result.backup_codes||[]);setMfaSetup(null);setMfaCode('');await load()}catch(e){setError(e.message)}
}
async function disableMfa(e){
e.preventDefault();setError('');
try{await apiFetch('/api/auth/mfa/disable',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:disablePassword,code:disableCode})});setDisablePassword('');setDisableCode('');setBackupCodes([]);setMfaSetup(null);await load()}catch(e){setError(e.message)}
}
async function revokeSession(id){
setError('');
try{await apiFetch('/api/auth/sessions/'+id+'/revoke',{method:'POST'});await load()}catch(e){setError(e.message)}
}
async function revokeAllSessions(){
setError('');
try{await apiFetch('/api/auth/sessions/revoke-all',{method:'POST'});setSessions([]);setRevokedAll(true)}catch(e){setError(e.message)}
}
async function exportAudit(){
try{const response=await fetch(API+'/api/admin/audit.csv',{headers:{Authorization:'Bearer '+token}});if(!response.ok){const body=await response.json();throw Error(body.detail||'Export failed')}const blob=await response.blob();const href=URL.createObjectURL(blob);const a=document.createElement('a');a.href=href;a.download='trustshare-audit.csv';document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(href)}catch(e){setError(e.message)}
}
async function loadSharingReport(){
try{setSharingReport(await apiFetch('/api/admin/reports/sharing'))}catch(e){setError(e.message)}
}
const statCards=Object.entries(data?.stats||{});
const nav=[['user','My dashboard',Activity],['analytics','File analytics',BarChart3],['security','Security events',ShieldAlert],['links','Link sharing',Link2],['shared','Direct sharing',Share2],['vault','Secure vault',LockKeyhole],['account','Account security',MonitorSmartphone],...(user?.role==='admin'?[['admin','Admin overview',Users]]:[])];
const primaryButton='inline-flex items-center justify-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50';
const secondaryButton='inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50';
const inputClass='mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100';
return <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/60 p-3 sm:p-5"><section className="mx-auto my-4 max-w-6xl rounded-2xl bg-slate-50 p-4 shadow-2xl sm:p-6">
<header className="flex items-start justify-between gap-3"><div className="flex items-start gap-3"><div className="rounded-xl bg-indigo-100 p-3 text-indigo-700"><ShieldCheck size={25}/></div><div><h2 className="text-xl font-bold text-slate-900">TrustShare Security Center</h2><p className="mt-1 text-sm text-slate-500">Security, file sharing, analytics and private vault</p><p className="mt-1 text-xs text-slate-400">Signed in as {user?.email||user?.name||'user'}</p></div></div><button onClick={onClose} className="rounded-lg p-2 text-slate-500 hover:bg-slate-200" aria-label="Close"><X/></button></header>
<nav className="my-5 flex gap-2 overflow-x-auto pb-1">{nav.map(([key,label,Icon])=><button key={key} onClick={()=>{setTab(key);setData(null);setError('')}} className={'inline-flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium '+(tab===key?'bg-slate-900 text-white':'border border-slate-200 bg-white text-slate-600 hover:bg-slate-100')}><Icon size={16}/>{label}</button>)}</nav>
{error&&<div className="mb-4 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800"><ShieldAlert size={17} className="mt-0.5 shrink-0"/><span>{error}</span></div>}
<div className="mb-4 flex flex-wrap items-center justify-between gap-3"><p className="text-sm font-semibold text-slate-700">{titleText(tab)}</p><div className="flex gap-2">{tab==='analytics'&&<select value={days} onChange={e=>setDays(e.target.value)} className="rounded-lg border bg-white px-3 py-2 text-sm"><option value="7">7 days</option><option value="30">30 days</option><option value="90">90 days</option></select>}{tab==='security'&&<select value={hours} onChange={e=>setHours(e.target.value)} className="rounded-lg border bg-white px-3 py-2 text-sm"><option value="24">24 hours</option><option value="168">7 days</option><option value="720">30 days</option></select>}<button onClick={load} className={secondaryButton}><RefreshCw size={15}/>Refresh</button></div></div>
{busy&&<div className="rounded-xl border bg-white p-6 text-sm text-slate-500">Loading TrustShare data…</div>}
{!busy&&['user','admin','security'].includes(tab)&&data&&<div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{statCards.map(([key,value])=><div key={key} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500"><HardDrive size={14}/>{titleText(key)}</div><div className="mt-2 break-words text-2xl font-bold text-slate-900">{key.includes('bytes')?bytesText(value):String(value)}</div></div>)}</div>}
{!busy&&tab==='analytics'&&data&&<div className="space-y-5"><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{statCards.map(([key,value])=><div key={key} className="rounded-xl border bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">{titleText(key)}</div><div className="mt-2 text-xl font-bold">{key==='storage_bytes'?bytesText(value):value}</div></div>)}</div><div className="grid gap-4 lg:grid-cols-2"><div className="rounded-xl border bg-white p-4"><h3 className="mb-3 font-semibold">Storage by file type</h3><div className="space-y-3">{(data.storage_by_type||[]).map(x=><div key={x.type}><div className="mb-1 flex justify-between gap-3 text-sm"><span>{x.type}</span><span className="text-slate-500">{x.files} files · {bytesText(x.bytes)}</span></div><div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-indigo-500" style={{width:Math.max(3,100*x.bytes/Math.max(1,...(data.storage_by_type||[]).map(t=>t.bytes)))+'%'}}/></div></div>)}</div></div><div className="rounded-xl border bg-white p-4"><h3 className="mb-3 font-semibold">Daily activity</h3><div className="max-h-72 overflow-auto"><table className="w-full text-left text-sm"><thead className="sticky top-0 bg-slate-50 text-xs text-slate-500"><tr><th className="p-2">Date</th><th className="p-2">Uploads</th><th className="p-2">Downloads</th><th className="p-2">Shares</th></tr></thead><tbody>{(data.activity||[]).map(x=><tr key={x.date} className="border-t"><td className="p-2">{x.date}</td><td className="p-2">{x.uploads}</td><td className="p-2">{x.downloads}</td><td className="p-2">{x.shares}</td></tr>)}</tbody></table></div>{data.activity_logging==='unavailable'&&<p className="mt-3 text-xs text-amber-700">Activity history is unavailable until MongoDB logging is connected.</p>}</div></div></div>}
{!busy&&tab==='security'&&data&&<div className="mt-4 overflow-hidden rounded-xl border bg-white"><div className="border-b p-4"><h3 className="font-semibold">Recent security events</h3><p className="mt-1 text-xs text-slate-500">The events shown depend on MongoDB activity logging.</p></div>{(data.events||[]).length===0?<p className="p-5 text-sm text-slate-500">No tracked events in this period, or event logging is unavailable.</p>:<div className="max-h-80 overflow-auto"><table className="w-full text-left text-sm"><thead className="sticky top-0 bg-slate-50 text-xs text-slate-500"><tr><th className="p-3">Event</th><th className="p-3">Time</th><th className="p-3">Details</th></tr></thead><tbody>{data.events.map((event,i)=><tr key={i} className="border-t"><td className="p-3 font-medium">{titleText(event.event||'event')}</td><td className="whitespace-nowrap p-3 text-slate-500">{String(event.timestamp||'').replace('T',' ').slice(0,19)}</td><td className="max-w-sm break-words p-3 text-xs text-slate-500">{JSON.stringify(event.details||{})}</td></tr>)}</tbody></table></div>}</div>}
{!busy&&tab==='links'&&<div className="space-y-4"><form onSubmit={createLink} className="grid gap-3 rounded-xl border bg-white p-4 sm:grid-cols-2 lg:grid-cols-5"><label className="text-sm">File ID<input required type="number" min="1" value={shareFileId} onChange={e=>setShareFileId(e.target.value)} className={inputClass}/></label><label className="text-sm">Expires in<select value={shareHours} onChange={e=>setShareHours(e.target.value)} className={inputClass}><option value="1">1 hour</option><option value="6">6 hours</option><option value="24">24 hours</option><option value="168">7 days</option><option value="720">30 days</option></select></label><label className="text-sm">Download limit<input type="number" min="1" max="10000" value={shareLimit} onChange={e=>setShareLimit(e.target.value)} placeholder="Unlimited" className={inputClass}/></label><label className="text-sm">Optional password (8+ chars)<input type="password" minLength="8" maxLength="128" autoComplete="new-password" value={sharePassword} onChange={e=>setSharePassword(e.target.value)} placeholder="Leave blank for no password" className={inputClass}/></label><label className="text-sm">Link permission<select value={sharePermission} onChange={e=>setSharePermission(e.target.value)} className={inputClass}><option value="download">Download</option><option value="view">Inline view</option></select></label><div className="flex items-end"><button className={primaryButton}><Link2 size={16}/>Create link</button></div></form>{shareUrl&&<div className="break-all rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900"><p className="mb-2 font-semibold">New link — copy it now</p>{shareUrl}<button onClick={()=>navigator.clipboard.writeText(shareUrl)} className={secondaryButton+' mt-3'}><Copy size={15}/>Copy link</button></div>}<div className="overflow-hidden rounded-xl border bg-white"><div className="border-b p-4 font-semibold">Your share links</div>{Array.isArray(data)&&data.length===0?<p className="p-4 text-sm text-slate-500">No share links yet.</p>:<div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="bg-slate-50 text-xs text-slate-500"><tr><th className="p-3">File</th><th className="p-3">Expiry</th><th className="p-3">Usage</th><th className="p-3">Status</th><th className="p-3">Action</th></tr></thead><tbody>{(Array.isArray(data)?data:[]).map(x=><tr key={x.id} className="border-t"><td className="p-3">{x.file_name||('File '+x.file_id)}</td><td className="p-3">{String(x.expires_at||'').replace('T',' ').slice(0,16)}</td><td className="p-3">{x.download_count}/{x.max_downloads??'∞'}</td><td className="p-3">{x.revoked?'Revoked':x.expired?'Expired':'Active'}</td><td className="p-3">{!x.revoked&&!x.expired&&<button onClick={()=>revokeLink(x.id)} className="text-sm font-semibold text-red-700">Revoke</button>}</td></tr>)}</tbody></table></div>}</div></div>}
{!busy&&tab==='shared'&&<div className="space-y-4"><form onSubmit={createDirectShare} className="grid gap-3 rounded-xl border bg-white p-4 sm:grid-cols-2 lg:grid-cols-4"><label className="text-sm">File ID<input required type="number" min="1" value={directFileId} onChange={e=>setDirectFileId(e.target.value)} className={inputClass}/></label><label className="text-sm">Recipient account email<input required type="email" value={directEmail} onChange={e=>setDirectEmail(e.target.value)} className={inputClass} placeholder="person@example.com"/></label><label className="text-sm">Permission<select value={directPermission} onChange={e=>setDirectPermission(e.target.value)} className={inputClass}><option value="view_download">View and download</option><option value="view">View-only (in-app preview route)</option></select></label><div className="flex items-end"><button className={primaryButton}><Share2 size={16}/>Share with user</button></div></form><div className="grid gap-4 lg:grid-cols-2">{[['Shared with me',data?.shared_with_me||[],false],['Shared by me',data?.shared_by_me||[],true]].map(([label,rows,canRevoke])=><div key={label} className="overflow-hidden rounded-xl border bg-white"><h3 className="border-b p-4 font-semibold">{label}</h3>{rows.length===0?<p className="p-4 text-sm text-slate-500">No direct shares.</p>:rows.map(x=><div key={x.grant_id} className="flex items-center justify-between gap-3 border-b p-3 last:border-0"><div className="min-w-0"><p className="truncate text-sm font-medium">{x.file_name||('File '+x.file_id)}</p><p className="mt-1 break-all text-xs text-slate-500">{canRevoke?'To: '+x.recipient_email:'From: '+x.owner_email} · {x.permission}</p></div>{canRevoke&&<button onClick={()=>revokeGrant(x.grant_id)} className="shrink-0 text-xs font-semibold text-red-700">Revoke</button>}</div>)}</div>)}</div></div>}
{!busy&&tab==='vault'&&<div className="space-y-4"><div className="rounded-xl border bg-white p-4"><div className="mb-2 flex items-center gap-2"><LockKeyhole className="text-indigo-700"/><h3 className="font-semibold">Private Secure Vault</h3></div><p className="mb-4 text-sm text-slate-500">Files and names are encrypted with a key derived from a separate vault password. You must enter this password again for protected actions. If you forget it, the files cannot be recovered; reset deletes them permanently.</p>{!vaultStatus?.configured?<form onSubmit={setupVault} className="flex flex-wrap items-end gap-3"><label className="min-w-64 flex-1 text-sm">Create a new vault password (12+ characters)<input required minLength="12" type="password" autoComplete="new-password" value={vaultSetupPassword} onChange={e=>setVaultSetupPassword(e.target.value)} className={inputClass}/></label><button className={primaryButton}>Create vault</button></form>:<form onSubmit={unlockVault} className="flex flex-wrap items-end gap-3"><label className="min-w-64 flex-1 text-sm">Vault password<input required type="password" autoComplete="current-password" value={vaultPassword} onChange={e=>setVaultPassword(e.target.value)} className={inputClass}/></label><button className={primaryButton}><LockKeyhole size={16}/>Unlock vault</button><button type="button" className={secondaryButton} onClick={()=>{setVaultPassword('');setVaultFiles([]);setVaultUpload(null)}}>Lock vault</button><span className="text-xs text-slate-500">{vaultStatus.file_count} protected files</span></form>}</div>{vaultStatus?.configured&&vaultPassword&&<><form onSubmit={uploadVaultFile} className="flex flex-wrap items-end gap-3 rounded-xl border bg-white p-4"><label className="min-w-64 flex-1 text-sm">Add a file to the vault<input type="file" onChange={e=>setVaultUpload(e.target.files?.[0]||null)} className={inputClass}/></label><button disabled={!vaultUpload} className={primaryButton}><Upload size={16}/>Encrypt and store</button></form><form onSubmit={changeVaultPassword} className="flex flex-wrap items-end gap-3 rounded-xl border bg-white p-4"><label className="min-w-64 flex-1 text-sm">Change vault password<input minLength="12" required type="password" autoComplete="new-password" value={vaultNewPassword} onChange={e=>setVaultNewPassword(e.target.value)} className={inputClass}/></label><button className={secondaryButton}>Re-key vault</button></form><div className="overflow-hidden rounded-xl border bg-white"><h3 className="border-b p-4 font-semibold">Vault files</h3>{vaultFiles.length===0?<p className="p-4 text-sm text-slate-500">No vault files yet. Upload a file above to get started.</p>:vaultFiles.map(item=><div key={item.id} className="flex items-center justify-between gap-3 border-b p-3 last:border-0"><div className="flex min-w-0 items-center gap-3"><FileText size={19} className="shrink-0 text-indigo-700"/><div className="min-w-0"><p className="truncate text-sm font-medium">{item.name}</p><p className="text-xs text-slate-500">{bytesText(item.size)} · {String(item.created_at).slice(0,10)}</p></div></div><div className="flex shrink-0 gap-2"><button type="button" onClick={()=>vaultPreview(item)} className={secondaryButton} aria-label="Preview vault file"><ExternalLink size={15}/></button><button type="button" onClick={()=>vaultDownload(item)} className={secondaryButton} aria-label="Download vault file"><Download size={15}/></button><button type="button" onClick={()=>vaultRename(item)} className={secondaryButton} aria-label="Rename vault file">Rename</button><button type="button" onClick={()=>deleteVaultFile(item.id)} className="rounded-lg border border-red-200 px-3 py-2 text-red-700" aria-label="Delete vault file"><Trash2 size={15}/></button></div></div>)}</div><div className="rounded-xl border border-red-200 bg-red-50 p-4"><h3 className="font-semibold text-red-900">Reset Secure Vault</h3><p className="mt-1 text-sm text-red-800">Use only if you need to discard the vault. All protected files are permanently deleted; they cannot be restored.</p><button type="button" onClick={resetVault} className="mt-3 rounded-lg border border-red-300 bg-white px-3 py-2 text-sm font-semibold text-red-800 hover:bg-red-100">Reset vault and delete all files</button></div></>}</div>}
{!busy&&tab==='admin'&&user?.role==='admin'&&data&&<div className="mt-5 space-y-4"><div className="rounded-xl border bg-white p-4"><h3 className="mb-3 font-semibold">Administrator reports</h3><div className="flex flex-wrap gap-2"><button onClick={exportAudit} className={primaryButton}><Download size={16}/>Export audit CSV</button><button onClick={loadSharingReport} className={secondaryButton}><Share2 size={16}/>Load sharing report</button></div></div>{sharingReport&&<div className="overflow-x-auto rounded-xl border bg-white"><div className="border-b p-4 font-semibold">Sharing report · {sharingReport.total} links · {sharingReport.active} active</div><table className="w-full text-left text-sm"><thead className="bg-slate-50 text-xs text-slate-500"><tr><th className="p-3">File</th><th className="p-3">Owner</th><th className="p-3">Expiry</th><th className="p-3">Downloads</th><th className="p-3">Status</th></tr></thead><tbody>{sharingReport.shares.map(x=><tr key={x.share_id} className="border-t"><td className="p-3">{x.file_name}</td><td className="p-3">{x.owner_email}</td><td className="p-3">{String(x.expires_at).slice(0,16).replace('T',' ')}</td><td className="p-3">{x.downloads}/{x.max_downloads??'∞'}</td><td className="p-3">{x.revoked?'Revoked':x.expired?'Expired':'Active'}</td></tr>)}</tbody></table></div>}{(data.recent_events||[]).length>0&&<div className="overflow-hidden rounded-xl border bg-white"><h3 className="border-b p-4 font-semibold">Recent activity</h3>{data.recent_events.map((e,i)=><div key={i} className="border-b p-3 text-sm last:border-0"><span className="font-medium">{titleText(e.event)}</span><span className="ml-2 text-xs text-slate-500">{e.timestamp||''}</span></div>)}</div>}</div>}
{!busy&&tab==='account'&&<div className="space-y-4">
<div className="rounded-xl border bg-white p-4"><div className="mb-2 flex items-center gap-2"><KeyRound className="text-indigo-700"/><h3 className="font-semibold">Authenticator MFA</h3></div><p className="mb-4 text-sm text-slate-500">Protect sign-ins with a time-based authenticator code. Backup codes are single-use; store them somewhere safe.</p><p className="mb-3 text-sm">Status: <strong>{mfaStatus?.enabled?'Enabled':mfaStatus?.configured?'Setup started':'Not configured'}</strong></p>{!mfaStatus?.enabled&&!mfaSetup&&<button className={primaryButton} onClick={beginMfaSetup}>Set up authenticator</button>}{mfaSetup&&<div className="space-y-3 rounded-lg bg-slate-50 p-3"><p className="text-sm font-medium">Add this secret to your authenticator app</p><code className="block break-all rounded bg-white p-3 text-sm">{mfaSetup.secret}</code><button className={secondaryButton} onClick={()=>navigator.clipboard.writeText(mfaSetup.secret)}><Copy size={15}/>Copy secret</button><p className="break-all text-xs text-slate-500">Setup URI: {mfaSetup.otpauth_url}</p><form onSubmit={confirmMfa} className="flex flex-wrap items-end gap-3"><label className="min-w-44 flex-1 text-sm">Authenticator code<input required minLength="6" maxLength="8" value={mfaCode} onChange={e=>setMfaCode(e.target.value)} className={inputClass} autoComplete="one-time-code"/></label><button className={primaryButton}>Confirm and enable MFA</button></form></div>}{backupCodes.length>0&&<div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3"><h4 className="font-semibold text-amber-900">Save these backup codes now</h4><p className="mt-1 text-xs text-amber-800">They are shown only once. Each code can be used once.</p><div className="my-3 grid grid-cols-2 gap-2 sm:grid-cols-5">{backupCodes.map(code=><code key={code} className="rounded bg-white p-2 text-center">{code}</code>)}</div><button className={secondaryButton} onClick={()=>navigator.clipboard.writeText(backupCodes.join('\n'))}><Copy size={15}/>Copy backup codes</button></div>}{mfaStatus?.enabled&&<form onSubmit={disableMfa} className="mt-3 grid gap-3 rounded-lg border border-red-100 p-3 sm:grid-cols-3"><label className="text-sm">Account password<input required type="password" value={disablePassword} onChange={e=>setDisablePassword(e.target.value)} className={inputClass}/></label><label className="text-sm">Authenticator or backup code<input required value={disableCode} onChange={e=>setDisableCode(e.target.value)} className={inputClass}/></label><div className="flex items-end"><button className="rounded-lg border border-red-200 px-4 py-2 text-sm font-semibold text-red-700">Disable MFA</button></div></form>}</div>
<div className="rounded-xl border bg-white p-4"><div className="mb-3 flex flex-wrap items-center justify-between gap-2"><div><h3 className="flex items-center gap-2 font-semibold"><MonitorSmartphone size={18}/>Active sessions and devices</h3><p className="mt-1 text-xs text-slate-500">Revoke a device session if you no longer recognize it.</p></div><button className="rounded-lg border border-red-200 px-3 py-2 text-sm font-semibold text-red-700" onClick={revokeAllSessions}>Revoke all sessions</button></div>{revokedAll&&<p className="mb-3 rounded bg-amber-50 p-3 text-sm text-amber-800">All sessions were revoked, including this one. Sign in again to continue.</p>}{sessions.length===0?<p className="text-sm text-slate-500">No active tracked sessions.</p>:sessions.map(session=><div key={session.id} className="flex flex-wrap items-center justify-between gap-3 border-t py-3"><div className="min-w-0"><p className="text-sm font-medium">{session.current?'This session':'Signed-in device'} {session.current&&<span className="ml-1 text-xs text-emerald-700">Current</span>}</p><p className="mt-1 break-all text-xs text-slate-500">{session.user_agent} · IP {session.ip_address}</p><p className="mt-1 text-xs text-slate-400">Last active: {String(session.last_active_at).replace('T',' ').slice(0,19)}</p></div><button onClick={()=>revokeSession(session.id)} className="shrink-0 text-sm font-semibold text-red-700">Revoke</button></div>)}</div>
</div>}
<div className="mt-6 flex justify-end"><button onClick={onClose} className={secondaryButton}>Close security center</button></div>
</section></div>;
}
