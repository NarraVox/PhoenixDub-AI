/* Independent Style panel; no changes to the existing generation/player flow. */
(() => {
    const api = 'http://127.0.0.1:5005/api/styles';
    const el = id => document.getElementById(`styles-${id}`);
    const player = el('player');
    let currentId = null, selected = null, timer = null, stopAt = null;
    const stages = {preparing:'Preparando áudio', separation:'Separando os quatro stems', score:'Extraindo score opcional',
        beats:'Detectando beats e compassos', patterns:'Comparando padrões da bateria', fills:'Avaliando viradas e transições',
        saving:'Salvando Style', cache:'Validando cache', completed:'Concluído'};
    const progress = {preparing:5,separation:15,score:48,beats:55,patterns:72,fills:85,saving:95,cache:98,completed:100};
    async function json(url, options) {
        const response = await fetch(url, options);
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `Falha HTTP ${response.status}`);
        return data;
    }
    function message(text) { el('status').textContent = text; }
    function busy(value) { el('analyze').disabled=value; el('cancel').disabled=!value; }
    function clearResult() {
        player.pause(); stopAt=null; selected=null;
        el('summary').replaceChildren(); el('timeline').replaceChildren(); el('evidence').textContent='';
        el('download').hidden=true;
    }
    async function list() {
        const data = await json(api);
        el('saved').replaceChildren(new Option('Selecione…',''));
        for (const item of data.items) el('saved').add(new Option(`${item.name} — ${item.status}`,item.id));
        if (currentId) el('saved').value=currentId;
        el('model-info').textContent=data.sheetsage.available ? 'SheetSage2 encontrado. A análise opcional acrescenta tonalidade, acordes, melodia e estrutura; BPM/grade do Nexus continuam independentes.' : data.sheetsage.message;
        if (data.active_id && !timer) { currentId=data.active_id; busy(true); poll(); }
    }
    function preview() {
        if (!selected || !currentId) return;
        const padding=el('context').checked?2:0;
        const start=Math.max(0,selected.start_seconds-padding);
        stopAt=selected.end_seconds+padding;
        const url=`${api}/${currentId}/audio/${el('track').value}`;
        const play=() => {
            player.currentTime=start;
            player.play().catch(err => message(`Reprodução: ${err.message}`));
        };
        player.pause();
        if (player.src!==url || player.readyState<1) { player.onloadedmetadata=play; player.src=url; player.load(); }
        else { player.onloadedmetadata=null; play(); }
    }
    player.addEventListener('timeupdate',()=> {if(stopAt!==null && player.currentTime>=stopAt) player.pause();});
    player.addEventListener('error',()=> message('Não foi possível carregar a faixa. Confira se o projeto e os stems continuam disponíveis.'));
    function render(style) {
        clearResult();
        const s=style.source_analysis;
        const tempoText=s.tempo_ambiguous?`ambíguo (${s.tempo_estimate??'indefinido'} estimado; alternativas em analysis.json)`:s.bpm??'indefinido';
        const harmony=style.harmony;
        const keyText=harmony?.key?.symbol?` · tonalidade ${harmony.key.symbol}`:'';
        const chordText=harmony?.chord_progression?.length?` · ${harmony.chord_progression.slice(0,8).map(x=>x.chord).join(' – ')}`:'';
        el('summary').textContent=`${style.name} · BPM ${tempoText} · compasso ${s.meter??'indefinido'} · confiança da grade ${Math.round((s.grid_confidence||0)*100)}% · ${style.drums.patterns.length} padrões${keyText}${chordText}.`;
        for(const section of style.sections) {
            const button=document.createElement('button'); button.type='button'; button.dataset.status=section.status;
            button.textContent=`${section.label} | ${section.start_seconds.toFixed(1)}–${section.end_seconds.toFixed(1)}s | ${Math.round(section.confidence*100)}%`;
            button.title=section.reason;
            button.addEventListener('click',()=> { selected=section; el('evidence').textContent=section.reason; preview(); });
            el('timeline').append(button);
        }
        if(!style.sections.length) el('evidence').textContent='Sem grade estável: nenhum padrão foi classificado. Tente outra referência ou informe BPM e compasso.';
        el('download').href=`${api}/${currentId}/style.json`; el('download').hidden=false;
    }
    async function poll() {
        clearTimeout(timer); timer=null;
        try {
            const data=await json(`${api}/${currentId}`);
            message(data.error || `${stages[data.stage]||data.status}${data.cached?' — cache reutilizado':''}`);
            el('progress').value=(progress[data.stage]||0)+(data.stage==='separation'?(data.fraction||0)*30:0);
            if(['queued','running'].includes(data.status)) {busy(true);timer=setTimeout(poll,1500);}
            else {busy(false);if(data.style) render(data.style);}
        } catch(err) {busy(false);message(`Consulta interrompida: ${err.message}. Use Atualizar lista para reconectar.`);}
    }
    el('form').addEventListener('submit',async event=> {
        event.preventDefault();clearTimeout(timer);timer=null;clearResult();busy(true);message('Enviando referência…');
        try {const data=await json(`${api}/analyze`,{method:'POST',body:new FormData(event.target)});currentId=data.id;poll();}
        catch(err){busy(false);message(err.message);}
    });
    el('cancel').addEventListener('click',async()=> {try {await json(`${api}/${currentId}/cancel`,{method:'POST'});message('Cancelando…');}catch(err){message(err.message);}});
    el('saved').addEventListener('change',()=> {if(el('saved').value){clearTimeout(timer);timer=null;currentId=el('saved').value;clearResult();poll();}});
    el('track').addEventListener('change',preview); el('context').addEventListener('change',preview);
    el('refresh').addEventListener('click',()=>list().catch(err=>message(err.message)));
    document.getElementById('open-styles').addEventListener('click',()=>{el('dialog').showModal();list().catch(err=>message(err.message));});
    el('close').addEventListener('click',()=>{player.pause();el('dialog').close();});
})();
