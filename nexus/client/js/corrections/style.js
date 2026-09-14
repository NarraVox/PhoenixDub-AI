export default `
    <style>
        :host { display: block; margin: 16px 0; font-family: 'Outfit', 'Segoe UI', sans-serif; color: #fff; }
        * { box-sizing: border-box; }
        button, input, select, textarea { font: inherit; }
        button { padding: 11px 16px; background: #64e8ed; border: 1px solid #64e8ed; border-radius: 8px; color: #07252c; font-weight: 800; cursor: pointer; }
        button:disabled { opacity: .5; cursor: default; }
        button:focus-visible, input:focus-visible, textarea:focus-visible, select:focus-visible { outline: 3px solid #ffc96d; outline-offset: 2px; }
        .launch { width: 100%; text-align: left; background: #0c333e; color: #aafaff; }
        .launch small { display: block; margin-top: 6px; font-weight: 400; font-size: 12px; line-height: 1.5; }
        dialog { position: fixed; inset: 0; margin: auto; width: min(1120px, calc(100vw - 32px)); height: min(850px, calc(100dvh - 32px)); padding: 24px; border: 1px solid #55cad8; border-radius: 18px; background: #101724; color: #fff; overflow: auto; }
        dialog::backdrop { background: #02050ce6; }
        h2 { font-size: 23px; margin: 0; }
        p { color: #b5c8db; line-height: 1.5; font-size: 14px; }
        .bar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin: 14px 0; }
        .head { justify-content: space-between; }
        .quiet { background: #1e2b3e; color: #d7e6f5; border-color: #47617e; }
        input, textarea, select { color: #fff; background: #090f19; border: 1px solid #4b6681; border-radius: 7px; padding: 10px; min-width: 0; }
        select { flex: 1; min-width: 200px; max-width: 100%; }
        input { flex: 1; }
        textarea { width: 100%; resize: vertical; min-height: 75px; line-height: 1.5; }
        .row { border: 1px solid #31465e; border-radius: 10px; padding: 16px; margin-top: 12px; background: #151f2e; }
        .name { font-size: 13px; color: #8cdee7; overflow-wrap: anywhere; }
        .original { font-size: 14px; color: #b9c7d7; white-space: pre-wrap; margin: 12px 0; }
        .save { color: #a9b9cd; font-size: 12px; }
        .error { color: #ffaf9c; }
        audio { max-width: 100%; width: 260px; height: 35px; }
        .status { white-space: pre-wrap; padding: 12px; background: #082e36; border-radius: 8px; font-size: 14px; overflow-wrap: anywhere; }
        .footer { position: sticky; bottom: -24px; background: #101724; border-top: 1px solid #31465e; padding: 12px 0; margin-top: 16px; }
        .count { font-size: 13px; color: #bdd6df; }
        details { margin: 12px 0; padding: 12px; border: 1px solid #31465e; border-radius: 8px; }
        summary { cursor: pointer; color: #8cdee7; font-weight: 700; }
        .pick-label { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
        input[type=checkbox] { flex: none; width: 18px; height: 18px; accent-color: #64e8ed; }
        .batch-review { max-height: 260px; overflow: auto; }
        .task-progress { margin: 16px 0; padding: 14px; background: #082e36; border-radius: 10px; }
        .progress-bar { width: 100%; height: 18px; margin: 10px 0; accent-color: #64e8ed; }
        .progress-log { max-height: 160px; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; font: 12px/1.6 Consolas, monospace; color: #d7e6f5; }
        .timing { margin: 8px 0 12px; color: #bde8df; }
        .timing-bar { width: 100%; height: 12px; accent-color: #64e8ed; }
        .over-budget, .over-budget .count { color: #ffb2a8; }
        .over-budget .timing-bar { accent-color: #ff7266; }
        .generated-timing { margin: 8px 0; }
    </style>`;
