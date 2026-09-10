// Carrega os módulos do painel a partir da localização deste script.
(() => {
    const host = document.getElementById('global-correction-panel');
    if (!host) return;
    const source = document.currentScript.src;
    import(new URL('./corrections/controller.js', source)).then(({mount}) => mount(host)).catch(error => {
        host.textContent = 'Não foi possível abrir a correção. Reabra o programa. ' + error.message;
    });
})();
