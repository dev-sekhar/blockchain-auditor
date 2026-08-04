export const $=selector=>document.querySelector(selector);
export const escapeHtml=value=>String(value??"").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
export const colors={critical:"#b42318",high:"#e5484d",medium:"#e09f3e",low:"#3478c8",informational:"#8792a2"};
export const statCard=(label,value)=>`<div class="card"><span>${escapeHtml(label)}</span><b>${escapeHtml(value)}</b></div>`;
export const badge=(value,color="")=>`<span class="badge"${color?` style="color:${color}"`:""}>${escapeHtml(value)}</span>`;
export function notify(message){const element=$("#notification");element.textContent=message;element.classList.add("show");setTimeout(()=>element.classList.remove("show"),4000)}
