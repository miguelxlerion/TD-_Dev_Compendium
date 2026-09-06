/* TD Dev Compendium — shell unificado con auto-integración vía content/manifest.json */
(function(){
  "use strict";
  const $ = (s, r=document)=>r.querySelector(s);
  const $$ = (s, r=document)=>Array.from(r.querySelectorAll(s));
  const LS_FAV="td_favs_v1", LS_REC="td_recent_v1";

  const state = { manifest:null, route:{view:"home"}, query:"", favs:new Set(), recents:[] };
  try{ state.favs = new Set(JSON.parse(localStorage.getItem(LS_FAV)||"[]")); }catch(e){}
  try{ state.recents = JSON.parse(localStorage.getItem(LS_REC)||"[]"); }catch(e){}

  const COLOR = { violet:"#8b5cf6", amber:"#e8c15a", cyan:"#22d3ee", emerald:"#34d399", rose:"#fb7185" };

  function toast(msg){
    const t=document.createElement("div"); t.textContent=msg;
    $("#toasts").appendChild(t); setTimeout(()=>t.remove(),3200);
  }
  function saveFavs(){ localStorage.setItem(LS_FAV, JSON.stringify([...state.favs])); }
  function pushRecent(id){
    state.recents=[id,...state.recents.filter(x=>x!==id)].slice(0,8);
    localStorage.setItem(LS_REC, JSON.stringify(state.recents));
  }

  async function loadManifest(){
    // En file:// el navegador bloquea fetch por CORS: se usa directo
    // el manifest embebido, sin intentar la petición (evita el error).
    if(location.protocol!=="file:"){
      const urls=["content/manifest.json","./content/manifest.json"];
      for(const u of urls){
        try{ const r=await fetch(u,{cache:"no-store"}); if(r.ok) return await r.json(); }catch(e){}
      }
    }
    const emb=$("#manifest-embedded");
    if(emb){ try{ return JSON.parse(emb.textContent); }catch(e){} }
    throw new Error("No se pudo cargar content/manifest.json");
  }

  function pageById(id){ return (state.manifest.pages||[]).find(p=>p.id===id); }
  function catById(id){ return (state.manifest.categories||[]).find(c=>c.id===id); }
  function countByCat(cat){ return state.manifest.pages.filter(p=>p.category===cat).length; }

  function icon(name, size=16){
    // lucide via <i data-lucide>; refresh after render
    return `<i data-lucide="${name}" style="width:${size}px;height:${size}px"></i>`;
  }
  function refreshIcons(){ if(window.lucide) lucide.createIcons(); }

  function matches(p,q){
    if(!q) return true;
    q=q.toLowerCase();
    return (p.title+" "+(p.short||"")+" "+(p.description||"")+" "+(p.tags||[]).join(" ")).toLowerCase().includes(q);
  }

  function cardHTML(p){
    const cat=catById(p.category);
    const fav=state.favs.has(p.id)?"fav-on":"";
    return `<article class="card" data-id="${p.id}">
      <div class="card-top">
        <span class="cat-dot" style="background:${COLOR[cat?.color]||"#8b5cf6"}"></span>
        <span>${cat?cat.name:""}</span>
        <span class="pill type-${p.type}" style="margin-left:auto">${p.type==="pdf"?"PDF":"HTML"}</span>
      </div>
      <h3>${escapeHTML(p.short||p.title)}</h3>
      <p>${escapeHTML((p.description||"").slice(0,180))}</p>
      <div class="card-tags">${(p.tags||[]).slice(0,5).map(t=>`<span>#${escapeHTML(t)}</span>`).join("")}</div>
      <div class="card-actions">
        <button class="mini go" data-act="open">Abrir →</button>
        <button class="mini ${fav}" data-act="fav" title="Favorito">★</button>
        <button class="mini" data-act="newtab" title="Abrir original en pestaña nueva">↗</button>
      </div>
    </article>`;
  }
  function escapeHTML(s){ return String(s||"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }

  function renderSidebar(){
    const cats=state.manifest.categories||[];
    $("#sideCats").innerHTML=cats.map(c=>`
      <button class="nav-item" data-route="#/categoria/${c.id}">
        <span class="cat-dot" style="background:${COLOR[c.color]||"#8b5cf6"}"></span>
        <span>${escapeHTML(c.name)}</span><span class="count">${countByCat(c.id)}</span>
      </button>`).join("");
    $("#statPages").textContent=state.manifest.pages.filter(p=>p.type==="html").length;
    $("#statPdfs").textContent=state.manifest.pages.filter(p=>p.type==="pdf").length;
    $("#statCats").textContent=cats.length;
    refreshIcons();
  }

  function renderHome(){
    const q=state.query;
    const pages=state.manifest.pages.filter(p=>matches(p,q));
    const featured=state.manifest.pages.filter(p=>p.featured&&matches(p,q));
    const html=pages.filter(p=>p.type==="html"), pdfs=pages.filter(p=>p.type==="pdf");
    const favs=state.manifest.pages.filter(p=>state.favs.has(p.id));
    const recs=state.recents.map(pageById).filter(Boolean);

    $("#view").innerHTML=`
      <div class="hero">
        <div class="crumbs">TD DEV COMPENDIUM · Documentación de Total Darkness</div>
        <h1 class="font-display">Centro de conocimiento del proyecto</h1>
        <p>Todas las guías HTML y documentos PDF en un solo lugar, organizados por contexto.
        Para agregar una página nueva: copia el <code class="inline">.html</code> a
        <code class="inline">content/</code> (o el PDF a <code class="inline">docs/</code>) y ejecuta
        <code class="inline">python tools/build-manifest.py</code>. Al recargar, aparece sola.</p>
        <div class="stats">
          <div class="stat"><b>${state.manifest.pages.filter(p=>p.type==="html").length}</b><span>Guías HTML</span></div>
          <div class="stat"><b>${state.manifest.pages.filter(p=>p.type==="pdf").length}</b><span>Documentos PDF</span></div>
          <div class="stat"><b>${state.manifest.categories.length}</b><span>Categorías</span></div>
          <div class="stat"><b>${state.favs.size}</b><span>Favoritos</span></div>
        </div>
      </div>
      ${q?`<div class="section-title"><h2>Resultados para “${escapeHTML(q)}” (${pages.length})</h2></div>
      <div class="grid">${pages.map(cardHTML).join("")||`<div class="empty">Sin resultados. Prueba con “pipeline”, “unity”, “qte”…</div>`}</div>`:`
      ${featured.length?`<div class="section-title">${icon("sparkles")} <h2>Destacados</h2></div>
      <div class="grid">${featured.map(cardHTML).join("")}</div>`:""}
      <div class="section-title">${icon("layout-grid")} <h2>Categorías</h2></div>
      <div class="grid">${state.manifest.categories.map(c=>`
        <article class="card" data-cat="${c.id}">
          <div class="card-top"><span class="cat-dot" style="background:${COLOR[c.color]}"></span><span>${countByCat(c.id)} recursos</span></div>
          <h3>${escapeHTML(c.name)}</h3><p>${escapeHTML(c.description)}</p>
          <div class="card-actions"><button class="mini go" data-act="cat">Explorar →</button></div>
        </article>`).join("")}</div>
      ${favs.length?`<div class="section-title">★ <h2>Favoritos (${favs.length})</h2></div><div class="grid">${favs.map(cardHTML).join("")}</div>`:""}
      ${recs.length?`<div class="section-title"><h2>Vistos recientemente</h2></div><div class="grid">${recs.map(cardHTML).join("")}</div>`:""}
      <div class="section-title">${icon("file-text")} <h2>Todas las guías HTML (${html.length})</h2></div>
      <div class="grid">${html.map(cardHTML).join("")}</div>
      <div class="section-title">${icon("library")} <h2>Biblioteca PDF (${pdfs.length})</h2></div>
      <div class="grid">${pdfs.map(cardHTML).join("")}</div>`}
      <div class="section-title"><h2>¿Cómo agrego una página nueva?</h2></div>
      <div class="help-grid">
        <div class="meta-box"><h4>1 · COPIA EL ARCHIVO</h4><p>Pega tu <code class="inline">nueva-guia.html</code> en <code class="inline">content/</code>. Los PDF van en <code class="inline">docs/</code>. Usa nombres sin espacios ni tildes.</p></div>
        <div class="meta-box"><h4>2 · REGENERA EL ÍNDICE</h4><p>Ejecuta <code class="inline">python tools/build-manifest.py</code> o <code class="inline">npm run manifest</code>. El script detecta título, descripción y categoría automáticamente.</p></div>
        <div class="meta-box"><h4>3 · RECARGA</h4><p>La página aparece sola en su categoría, en el buscador y en el menú. Sin tocar código.</p></div>
      </div>`;
    refreshIcons();
  }

  function renderCategory(id){
    const c=catById(id);
    if(!c){ location.hash="#/inicio"; return; }
    const items=state.manifest.pages.filter(p=>p.category===id&&matches(p,state.query));
    $("#view").innerHTML=`
      <div class="crumbs"><a href="#/inicio" style="color:inherit">Inicio</a> / ${escapeHTML(c.name)}</div>
      <div class="section-title"><span class="cat-dot" style="background:${COLOR[c.color]}"></span><h2>${escapeHTML(c.name)} (${items.length})</h2></div>
      <p style="color:var(--muted);font-size:.9rem">${escapeHTML(c.description)}</p>
      <div class="grid">${items.map(cardHTML).join("")||`<div class="empty">Sin recursos en esta categoría.</div>`}</div>`;
  }

  function renderFavs(){
    const items=state.manifest.pages.filter(p=>state.favs.has(p.id)&&matches(p,state.query));
    $("#view").innerHTML=`<div class="crumbs">Inicio / Favoritos</div>
      <div class="section-title">★ <h2>Favoritos (${items.length})</h2></div>
      <div class="grid">${items.map(cardHTML).join("")||`<div class="empty">Aún no tienes favoritos. Pulsa ★ en cualquier tarjeta.</div>`}</div>`;
  }

  function renderPage(id){
    const p=pageById(id);
    if(!p){ $("#view").innerHTML=`<div class="empty">Página no encontrada. <a href="#/inicio">Volver</a></div>`; return; }
    pushRecent(id);
    const cat=catById(p.category);
    const fav=state.favs.has(p.id)?"fav-on":"";
    $("#view").innerHTML=`
      <div class="viewer-head">
        <div><div class="crumbs"><a href="#/inicio" style="color:inherit">Inicio</a> / <a href="#/categoria/${p.category}" style="color:inherit">${escapeHTML(cat?.name||"")}</a> / ${escapeHTML(p.short||p.title)}</div>
        <h2 style="margin:.3rem 0;font-size:1.15rem">${escapeHTML(p.title)}</h2></div>
        <div class="viewer-toolbar">
          <button class="btn" id="btnFav" title="Favorito">${fav?"★":"☆"} Favorito</button>
          <button class="btn" id="btnReload">⟳ Recargar</button>
          <button class="btn" id="btnFull">⛶ Pantalla completa</button>
          <a class="btn btn-primary" href="${p.file}" target="_blank" rel="noopener">Abrir original ↗</a>
        </div>
      </div>
      <div class="frame-wrap" id="frameWrap">
        <iframe class="viewer" id="viewer" src="${p.file}" title="${escapeHTML(p.title)}"></iframe>
      </div>
      <div class="meta">
        <div class="meta-box"><h4>ACERCA DE ESTE RECURSO</h4><p>${escapeHTML(p.description||"")}</p>
          <p>Etiquetas: ${(p.tags||[]).map(t=>`<code class="inline">#${escapeHTML(t)}</code>`).join(" ")}</p></div>
        <div class="meta-box"><h4>FICHA</h4>
          <p>Tipo: <b>${p.type.toUpperCase()}</b><br>Categoría: <b>${escapeHTML(cat?.name||"")}</b><br>Archivo: <code class="inline">${escapeHTML(p.file)}</code>${p.badge?`<br>Marca: <b>${escapeHTML(p.badge)}</b>`:""}</p></div>
      </div>`;
    $("#btnReload").onclick=()=>{ $("#viewer").src=$("#viewer").src; toast("Vista recargada"); };
    $("#btnFull").onclick=()=>{ $("#frameWrap").classList.toggle("full"); };
    $("#btnFav").onclick=(e)=>{
      if(state.favs.has(p.id)){state.favs.delete(p.id);}else{state.favs.add(p.id);toast("Añadido a favoritos");}
      saveFavs(); renderPage(id); renderSidebarActive();
    };
  }

  function renderHelp(){
    $("#view").innerHTML=`
      <div class="crumbs">Inicio / Ayuda</div>
      <div class="section-title"><h2>Auto-integración de páginas nuevas</h2></div>
      <div class="help-grid">
        <div class="meta-box"><h4>OPCIÓN A · CON EL BOTÓN (RECOMENDADA)</h4>
          <ol><li>Copia el <code class="inline">.html</code> a <code class="inline">content/</code>.</li>
          <li>Pulsa <b>⟳ Re-escanear</b> (arriba) o <b>＋ Añadir página → Regenerar índice ahora</b>.</li>
          <li>La página aparece sola, sin recargar ni tocar código.</li></ol>
          <p>Requiere abrir la plataforma con <code class="inline">Iniciar-Plataforma.bat</code>, <code class="inline">npm run up</code> o <code class="inline">python tools/launcher.py</code> (el botón usa el endpoint <code class="inline">POST /api/regenerar</code>).</p></div>
        <div class="meta-box"><h4>OPCIÓN B · POR TERMINAL</h4>
          <ol><li>Copia el archivo a <code class="inline">content/</code> (<code class="inline">docs/</code> para PDF).</li>
          <li>Ejecuta <code class="inline">python tools/build-manifest.py --update-index</code>.</li>
          <li>Recarga la plataforma.</li></ol>
          <p>El script lee el <code class="inline">&lt;title&gt;</code>, el primer párrafo y palabras clave para asignar categoría, descripción y etiquetas. Respeta ediciones manuales previas del manifest.</p></div>
        <div class="meta-box"><h4>OPCIÓN B · IMPORTAR Y PREVISUALIZAR</h4>
          <p>Usa el botón <b>＋ Añadir página</b> para previsualizar un HTML local al instante (vista temporal de sesión). Para fijarlo, guárdalo después en <code class="inline">content/</code> y regenera.</p></div>
        <div class="meta-box"><h4>SERVIDOR LOCAL</h4>
          <p>Doble clic funciona gracias al manifest embebido, pero lo ideal es servir la carpeta:</p>
          <p><code class="inline">python -m http.server 8080</code><br><code class="inline">npx serve .</code> o <code class="inline">npm run dev</code></p>
          <p>Luego abre <code class="inline">http://localhost:8080</code>.</p></div>
        <div class="meta-box"><h4>ATAJOS</h4>
          <p><kbd>/</kbd> buscar · <kbd>Esc</kbd> cerrar diálogos · Navegación por <code class="inline">#hash</code> (compatible con historial).</p></div>
      </div>`;
  }

  function renderSidebarActive(){
    $$("#sidebar [data-route]").forEach(b=>{
      const r=b.getAttribute("data-route");
      b.classList.toggle("active", location.hash===r || (location.hash.startsWith("#/pagina/")&&false));
    });
    $("#statFav").textContent=state.favs.size;
  }

  // Regenera content/manifest.json vía el mini-servidor local (tools/server.py).
  // Si la plataforma se abrió con doble clic o con un servidor estático simple,
  // el endpoint no existe y se muestra la alternativa manual.
  async function regenerarIndice(statusEl){
    const set=(t)=>{ if(statusEl) statusEl.textContent=t; };
    set("Regenerando índice…");
    toast("⟳ Re-escaneando content/ y docs/…");
    try{
      const r=await fetch("api/regenerar",{method:"POST"});
      if(!r.ok) throw new Error("HTTP "+r.status);
      const j=await r.json();
      if(!j.ok) throw new Error(j.error||"falló el generador");
      state.manifest=await loadManifest(); // recarga sin refrescar la página
      state.query=""; $("#search").value="";
      renderSidebar(); router(); refreshIcons();
      const msg=`Índice regenerado: ${j.html} HTML + ${j.pdf} PDF`;
      set("✔ "+msg); toast("✔ "+msg);
      return true;
    }catch(err){
      set("Sin puente local: abre con 'npm run up' o ejecuta python tools/build-manifest.py");
      toast("El botón necesita el servidor local (npm run up). Ver Ayuda.");
      return false;
    }
  }

  function router(){
    const h=location.hash||"#/inicio";
    if(h.startsWith("#/pagina/")) renderPage(decodeURIComponent(h.slice(9)));
    else if(h.startsWith("#/categoria/")) renderCategory(decodeURIComponent(h.slice(12)));
    else if(h==="#/favoritos") renderFavs();
    else if(h==="#/ayuda") renderHelp();
    else renderHome();
    renderSidebarActive();
    $("#sidebar").classList.remove("open");
    window.scrollTo({top:0});
  }

  function bindGlobal(){
    document.addEventListener("click",(e)=>{
      const nav=e.target.closest("[data-route]");
      if(nav){ location.hash=nav.getAttribute("data-route"); return; }
      const card=e.target.closest(".card");
      if(card){
        const act=e.target.closest("[data-act]");
        const id=card.getAttribute("data-id")||card.getAttribute("data-cat");
        if(card.hasAttribute("data-cat")){
          if(!act||act.getAttribute("data-act")==="cat") location.hash="#/categoria/"+id;
          return;
        }
        const p=pageById(id); if(!p) return;
        const a=act?act.getAttribute("data-act"):null;
        if(a==="fav"){ state.favs.has(id)?state.favs.delete(id):state.favs.add(id); saveFavs(); toast(state.favs.has(id)?"★ Añadido a favoritos":"☆ Quitado de favoritos"); router(); renderSidebarActive(); }
        else if(a==="newtab"){ window.open(p.file,"_blank","noopener"); }
        else location.hash="#/pagina/"+id;
      }
    });
    $("#search").addEventListener("input",(e)=>{ state.query=e.target.value.trim(); const h=location.hash;
      if(h.startsWith("#/pagina/")) location.hash="#/inicio"; else router(); });
    document.addEventListener("keydown",(e)=>{
      if(e.key==="/"&&document.activeElement!==$("#search")){e.preventDefault();$("#search").focus();}
      if(e.key==="Escape"){$("#modalAdd").classList.remove("open");$("#sidebar").classList.remove("open");}
    });
    $("#menuBtn").onclick=()=>$("#sidebar").classList.toggle("open");
    $("#btnAdd").onclick=()=>{ $("#rescanStatus").textContent=""; $("#modalAdd").classList.add("open"); };
    $("#btnRescan").onclick=()=>regenerarIndice();
    $("#btnAutoRescan").onclick=()=>regenerarIndice($("#rescanStatus"));
    $("#modalAdd").addEventListener("click",(e)=>{ if(e.target.id==="modalAdd"||e.target.closest("[data-close]")) $("#modalAdd").classList.remove("open"); });
    $("#fileInput").addEventListener("change",(e)=>{
      const f=e.target.files[0]; if(!f) return;
      const url=URL.createObjectURL(f);
      $("#view").innerHTML=`<div class="crumbs">Vista previa temporal · ${escapeHTML(f.name)}</div>
        <div class="frame-wrap"><iframe class="viewer" src="${url}"></iframe></div>
        <div class="meta"><div class="meta-box"><h4>¿CÓMO LA FIJO EN LA PLATAFORMA?</h4>
        <p>Esta vista es temporal. Para integrarla: guarda <code class="inline">${escapeHTML(f.name)}</code> en <code class="inline">content/</code> y ejecuta <code class="inline">python tools/build-manifest.py</code>.</p></div></div>`;
      $("#modalAdd").classList.remove("open"); toast("Vista previa cargada (temporal)");
    });
    window.addEventListener("hashchange",router);
  }

  async function init(){
    bindGlobal();
    if(location.protocol==="file:"){
      // Sin servidor no hay endpoint /api/regenerar (el navegador bloquea
      // fetch a file:// por CORS). Se avisa y se sigue en modo lectura.
      const w=document.createElement("div");
      w.className="filewarn";
      w.innerHTML=`⚠ La abriste como <b>archivo local</b>: todo funciona excepto el botón <b>⟳ Re-escanear</b>. Usa <b>Iniciar-Plataforma.bat</b> o <code class="inline">npm run up</code> para activar todas las funciones. <a href="#/ayuda">Ver ayuda</a>`;
      const c=$(".content"); if(c) c.prepend(w);
    }
    try{
      state.manifest=await loadManifest();
    }catch(err){
      $("#view").innerHTML=`<div class="empty">No se encontró <code class="inline">content/manifest.json</code>.<br>Sirve la carpeta con <code class="inline">python -m http.server</code> o revisa la consola.</div>`;
      return;
    }
    // páginas temporales aportadas por el generador (merge con ?page=)
    renderSidebar();
    if(!location.hash) location.hash="#/inicio";
    router();
    refreshIcons();
  }
  document.addEventListener("DOMContentLoaded",init);
})();
