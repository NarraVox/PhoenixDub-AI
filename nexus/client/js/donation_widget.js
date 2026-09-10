// Componente compartilhado por todas as telas do Nexus.
(() => {
    if (document.getElementById('nexus-donation-widget')) return;
    const host = document.createElement('div');
    host.id = 'nexus-donation-widget';
    host.setAttribute('popover', 'manual');
    const root = host.attachShadow({ mode: 'open' });
    root.innerHTML = `
        <style>
            :host { position: fixed; inset: auto 22px 22px auto; margin: 0; padding: 0; border: 0; background: transparent; overflow: visible; z-index: 2000; font-family: 'Outfit', 'Segoe UI', sans-serif; }
            * { box-sizing: border-box; }
            .donate { display: flex; align-items: center; gap: 12px; min-height: 58px; padding: 12px 22px; border: 2px solid #ffe7a0; border-radius: 16px; background: linear-gradient(120deg, #ffd568, #ffac79); color: #29102c; cursor: pointer; box-shadow: 0 5px 24px #ff56865c; animation: glow 2s ease-in-out 3; text-align: left; font: inherit; }
            .donate:hover { background: #ffe09a; transform: translateY(-2px); box-shadow: 0 6px 30px #ff568690; }
            .heart { font-size: 27px; }
            strong { display: block; font-size: 17px; font-weight: 900; letter-spacing: 1px; }
            small { display: block; margin-top: 2px; font-size: 11px; font-weight: 800; letter-spacing: .6px; }
            button:focus-visible, a:focus-visible { outline: 3px solid #55e6ff; outline-offset: 4px; }
            @keyframes glow { 50% { box-shadow: 0 0 32px #ff5686b0; } }
            dialog { position: fixed; inset: 0; margin: auto; width: min(460px, calc(100vw - 32px)); max-height: calc(100dvh - 40px); overflow: auto; padding: 30px; border: 1px solid #ffb77b; border-radius: 22px; background: #191121; color: #fff; box-shadow: 0 20px 80px #0009; font-family: inherit; }
            dialog::backdrop { background: #06030cbd; backdrop-filter: blur(5px); }
            .close { display: block; margin-left: auto; border: 0; background: #ffffff12; color: white; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; font-size: 24px; }
            h2 { font-size: 26px; margin: 12px 0; line-height: 1.2; }
            p { color: #ded2e5; line-height: 1.6; font-size: 15px; margin: 12px 0 22px; }
            a { display: block; padding: 15px; margin-top: 12px; border-radius: 11px; text-align: center; font-size: 15px; font-weight: 800; text-decoration: none; }
            .primary { background: #ffd07a; color: #29102c; }
            a:hover { filter: brightness(1.15); }
            .note { display: block; margin-top: 18px; text-align: center; font-size: 12px; color: #b9a8c5; }
            @media (max-width: 600px) { :host { right: 12px; bottom: 12px; } .donate { padding: 10px 14px; min-height: 50px; gap: 8px; } strong { font-size: 15px; } small { font-size: 9px; } }
            @media (prefers-reduced-motion: reduce) { .donate { animation: none; } .donate:hover { transform: none; } }
        </style>
        <button class="donate" type="button" aria-haspopup="dialog" aria-label="Doar e apoiar o projeto NarraVox">
            <span class="heart" aria-hidden="true">💖</span><span><strong>DOAR</strong><small>APOIE O PROJETO</small></span>
        </button>
        <dialog aria-labelledby="donation-title" aria-describedby="donation-description">
            <button class="close" type="button" aria-label="Fechar">×</button>
            <h2 id="donation-title">💖 Ajude a manter o Nexus crescendo</h2>
            <p id="donation-description">Seu apoio ajuda a NarraVox Studios a continuar desenvolvendo ferramentas gratuitas de inteligência artificial, dublagem e vídeo. Contribua pelo Apoia.se:</p>
            <a class="primary" href="https://apoia.se/narravox_studios" target="_blank" rel="noopener noreferrer">Apoiar no Apoia.se ↗</a>
            <span class="note">A contribuição é voluntária. Obrigado pelo apoio!</span>
        </dialog>`;
    document.body.appendChild(host);
    // A camada superior evita que os efeitos 3D das páginas desloquem o botão.
    if (host.showPopover) host.showPopover();
    const dialog = root.querySelector('dialog');
    const trigger = root.querySelector('.donate');
    trigger.addEventListener('click', () => dialog.showModal());
    root.querySelector('.close').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', (event) => {
        const rect = dialog.getBoundingClientRect();
        if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) dialog.close();
    });
    dialog.addEventListener('close', () => trigger.focus());
})();
