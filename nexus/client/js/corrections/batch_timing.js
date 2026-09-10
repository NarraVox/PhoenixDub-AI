import {textMetrics, seconds} from './timing.js';

export function setupBatchTiming(el, selected) {
    const field = el('.batch-text'), box = el('.batch-timing');
    function update() {
        const items = [...selected.values()];
        const known = items.filter(item => item.original_duration > 0);
        const count = textMetrics(field.value,null).count;
        const title = box.querySelector('.batch-timing-count');
        const detail = box.querySelector('.batch-timing-detail');
        const bar = box.querySelector('progress');
        bar.hidden = !known.length;
        box.classList.remove('over-budget');
        if (!known.length) {
            title.textContent = `${count} caracteres`;
            detail.textContent = items.length ? 'As durações originais não estão disponíveis.' : 'Selecione falas para ver o recomendado por duração.';
            return;
        }
        const durations = known.map(i => i.original_duration);
        const min = Math.min(...durations), max = Math.max(...durations);
        const shortest = textMetrics(field.value,min), longest = textMetrics(field.value,max);
        const over = known.filter(i => textMetrics(field.value,i.original_duration).over).length;
        box.classList.toggle('over-budget',over > 0);
        title.textContent = `${count} caracteres • recomendado: ${shortest.recommended}` +
            (shortest.recommended !== longest.recommended ? ` a ${longest.recommended}` : '') + ' por fala';
        detail.textContent = `Originais: ${seconds(min)}` + (min !== max ? ` a ${seconds(max)}` : '') +
            ` s • 18 caracteres/s • ${over} de ${known.length} acima do recomendado.` +
            (known.length < items.length ? ` ${items.length-known.length} sem duração.` : '') +
            ' A barra usa a fala mais curta. Salvar continua permitido; aceleração máxima de 1,20×.';
        bar.max = Math.max(1,shortest.recommended); bar.value = Math.min(count,bar.max);
    }
    field.addEventListener('input',update);
    return update;
}
