import {test} from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
const code = fs.readFileSync(new URL('../nexus/client/js/dj_studio.js', import.meta.url), 'utf8');
function fixture(uploadOK) {
    const fields = Object.fromEntries(Object.entries({
        'song-title':'Teste', 'generation-mode':'cover', 'song-style':'eletronica',
        'song-lyrics':'Minha letra', 'source-audio-select':'old_drums.wav',
        'cover-strength':'0.8', 'extend-duration':'30', 'gen-steps':'8',
        'gen-cfg':'1', 'gen-duration':'30', 'batch-count':'1'
    }).map(([id,value]) => [id,{value,style:{}}]));
    fields['local-audio-file'] = {files:[{name:'Djavu.mp3'}],value:'Djavu.mp3'};
    fields['source-audio-select'].options=[];
    fields['source-audio-select'].appendChild = option => fields['source-audio-select'].options.push(option);
    fields['source-reference-note'] = {};
    const calls=[];
    const context=vm.createContext({
        window:{}, console, alert:()=>{}, FormData:class {append() {}},
        document:{getElementById:id=>fields[id] || null, querySelector:()=>({}),createElement:()=>({})},
        fetch:async(url,options)=>{
            calls.push({url,options});
            return {ok:url.endsWith('/api/upload_audio_file') ? uploadOK : true,
                json:async()=>url.endsWith('/api/upload_audio_file') ? (uploadOK ? {filename:'Djavu.mp3'} : {error:'upload failed'}) : {success:true}};
        }
    });
    vm.runInContext(code,context);
    vm.runInContext('setLockdown = value => { isLocked = value; }; logBrain = () => {}; resetFxLights = () => {}; startMonitoringProgress = () => {};',context);
    return {context,calls,fields};
}
test('pending Djavu upload replaces old drums before generating',async()=>{
    const {context,calls,fields}=fixture(true);
    await vm.runInContext('generateMusic()',context);
    assert.equal(calls.length,2);
    assert.ok(calls[0].url.endsWith('/api/upload_audio_file'));
    const payload=JSON.parse(calls[1].options.body);
    assert.equal(payload.source_audio,'Djavu.mp3');
    assert.equal(payload.style,'');
    assert.equal(fields['local-audio-file'].value,'');
});
test('failed pending upload never generates with old reference',async()=>{
    const {context,calls}=fixture(false);
    await vm.runInContext('generateMusic()',context);
    assert.equal(calls.length,1);
});

test('Extended sends the panel duration as the new music length',async()=>{
    const {context,calls,fields}=fixture(true);
    fields['generation-mode'].value='extend';
    fields['gen-duration'].value='180';
    await vm.runInContext('generateMusic()',context);
    const payload=JSON.parse(calls[1].options.body);
    assert.equal(payload.duration,180);
    assert.equal(payload.extend_duration,180);
});
