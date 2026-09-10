export const CPS = 18;
export const seconds = value => Number(value).toLocaleString('pt-BR', {maximumFractionDigits:3});
export function textMetrics(text, duration) {
    const count = Array.from(text.normalize('NFC')).length;
    const valid = Number.isFinite(duration) && duration > 0;
    const recommended = valid ? Math.floor(duration * CPS + 1e-8) : null;
    return {count, recommended, over:valid && count > recommended, cps:valid ? count / duration : null};
}

export function attachTiming(textarea, duration) {
    const box = document.createElement('div'); box.className = 'timing';
    const original = document.createElement('div'); original.className = 'count';
    original.textContent = duration > 0 ? `Áudio original: ${seconds(duration)} s • referência: 18 caracteres/s` : 'Duração original não disponível';
    const count = document.createElement('div'); count.className = 'timing-count';
    count.setAttribute('aria-live','polite');
    const bar = document.createElement('progress'); bar.className = 'timing-bar';
    bar.setAttribute('aria-label','Caracteres usados em relação ao recomendado');
    const note = document.createElement('div'); note.className = 'count';
    box.append(original, count, bar, note);
    function update() {
        const m = textMetrics(textarea.value, duration);
        box.classList.toggle('over-budget',m.over);
        count.textContent = m.recommended == null ? `${m.count} caracteres` :
            `${m.count} / ${m.recommended} caracteres recomendados • ${seconds(m.cps)} caracteres/s`;
        bar.hidden = m.recommended == null;
        bar.max = Math.max(1,m.recommended || 1); bar.value = Math.min(m.count,bar.max);
        note.textContent = m.over ? 'Acima do recomendado. Você pode salvar; a fala pode ficar mais longa mesmo com aceleração de até 1,20×.' : 'Contagem inclui espaços e pontuação. É uma orientação, não um bloqueio.';
    }
    textarea.addEventListener('input',update); update();
    return box;
}

export function showGenerated(row, generated, speed, original) {
    const label = row.querySelector('.generated-timing');
    if (!label) return;
    label.hidden = !(generated > 0);
    if (label.hidden) return;
    const over = original > 0 && generated > original + .02;
    label.classList.toggle('over-budget',over);
    label.textContent = `Áudio gerado: ${seconds(generated)} s` + (speed ? ` • velocidade ${seconds(speed)}×` : '') +
        (over ? ` • ${seconds(generated-original)} s acima do original; fala preservada` : '');
}
