import style from './style.js';
export default style + `
    <button class="launch" type="button">🎯 CORREÇÃO GLOBAL DE DUBLAGEM
        <small>Corrija falas de projetos prontos. Alterações salvas automaticamente.</small>
    </button>
    <dialog aria-labelledby="correction-title">
        <div class="bar head"><h2 id="correction-title">Correção de dublagem</h2><button class="quiet close" type="button">Fechar</button></div>
        <p class="intro"></p>
        <div class="bar"><select aria-label="Filtrar projeto (opcional)"></select><button class="quiet refresh" type="button">Atualizar projetos</button></div>
        <div class="bar"><input class="query" aria-label="Buscar falas" placeholder="Digite a fala — buscamos em todos os uploads, mesmo com pequenos erros"><button class="search" type="button">Buscar</button></div>
        <div class="count summary"></div>
        <details class="batch-details">
            <summary>Corrigir várias falas de uma vez</summary>
            <p>Selecione as falas com o mesmo significado e escreva a tradução uma vez. Cada personagem será gerado com sua própria referência de voz.</p>
            <div class="bar"><button class="quiet pick-page" type="button">Selecionar página</button><button class="quiet pick-all" type="button">Selecionar todos os resultados</button><button class="quiet pick-clear" type="button">Limpar seleção</button></div>
            <div class="count batch-count"></div>
            <details><summary>Conferir originais e projetos selecionados</summary><div class="batch-review"></div></details>
            <label>Correção em português para as selecionadas<textarea class="batch-text" maxlength="3000" aria-label="Correção em português para as selecionadas"></textarea></label>
            <div class="batch-timing timing">
                <div class="batch-timing-count" aria-live="polite"></div>
                <progress class="timing-bar" aria-label="Caracteres em relação à fala selecionada mais curta" hidden></progress>
                <div class="batch-timing-detail count"></div>
            </div>
            <button class="batch-save" type="button" disabled>Salvar e dublar selecionadas</button>
            <div class="save batch-status" role="status"></div>
        </details>
        <div class="rows"></div>
        <div class="bar"><button class="quiet previous" type="button">Anterior</button><button class="quiet next" type="button">Próxima página</button></div>
        <section class="task-progress" hidden aria-label="Progresso geral das correções">
            <div class="progress-summary" role="status" aria-live="polite"></div>
            <progress class="progress-bar" max="100" aria-label="Percentual de falas concluídas"></progress>
            <div class="count progress-stage"></div>
            <details open><summary>Registro de processamento</summary><pre class="progress-log" tabindex="0" aria-label="Registro de processamento"></pre></details>
        </section>
        <div class="footer"><div class="status" role="status" aria-live="polite">Busque uma fala em todos os projetos de uploads.</div>
            <div class="bar"><button class="start" type="button">▶ COMEÇAR</button><button class="quiet export" type="button">Exportar correções salvas</button><button class="quiet folder" type="button" hidden>Abrir pasta de saída</button></div>
            <div class="count queue"></div>
        </div>
    </dialog>`;
