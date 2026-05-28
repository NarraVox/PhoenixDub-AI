def resegment_based_on_pauses(whisper_result, max_chars=200, max_duration=10.0, silence_threshold=1.0, diarization_data=None):
    """
    Resegmenta as palavras do Whisper baseando-se em pausas de silêncio (0.5s), 
    limites de tamanho, e respeitando rigorosamente a MUDANÇA DE ORADOR (Diarização).
    Portado do App_videos Master.
    """
    words = whisper_result.get('words', [])
    if not words: return []
    
    segments = []
    current_segment = {'words': [], 'start': 0, 'end': 0, 'text': ''}
    
    def get_speaker_at_time(t, diarization_data):
        if not diarization_data: return "unknown"
        for d in diarization_data:
            if (d['start'] - 0.1) <= t <= (d['end'] + 0.1):
                return d.get('speaker', 'unknown')
        return "unknown"

    for i, word in enumerate(words):
        if not current_segment['words']:
            current_segment['start'] = word['start']
            current_segment['words'].append(word)
            current_segment['end'] = word['end']
            continue
            
        last_word = current_segment['words'][-1]
        gap = word['start'] - last_word['end']
        current_dur = word['end'] - current_segment['start']
        
        should_break = False
        
        # 1. Pausa longa
        if gap > silence_threshold:
            should_break = True
            
        # 2. Pontuação Forte + Pequena Pausa
        last_word_text = last_word['word'].strip()
        if last_word_text and last_word_text[-1] in ['.', '?', '!'] and gap > 0.1:
            should_break = True
            
        # 3. Limite de caracteres
        current_text_len = sum([len(w['word']) for w in current_segment['words']])
        if current_text_len > max_chars:
            should_break = True
            
        # 4. Duração máxima
        if current_dur > max_duration:
            should_break = True
            
        # 5. Mudança Real de Orador
        if not should_break and diarization_data:
            spk_current = get_speaker_at_time(word['start'], diarization_data)
            spk_last = get_speaker_at_time(last_word['end'], diarization_data)
            if spk_current != spk_last and spk_current != "unknown" and spk_last != "unknown":
                should_break = True
                
        if should_break:
             full_text = "".join([w['word'] for w in current_segment['words']]).strip()
             if full_text:
                 segments.append({
                     'start': current_segment['start'],
                     'end': current_segment['end'],
                     'text': full_text,
                     'words': current_segment['words']
                 })
             current_segment = {'words': [word], 'start': word['start'], 'end': word['end'], 'text': ''}
        else:
             current_segment['words'].append(word)
             current_segment['end'] = word['end']
             
    # Adiciona o último
    full_text = "".join([w['word'] for w in current_segment['words']]).strip()
    if full_text:
        segments.append({
             'start': current_segment['start'],
             'end': current_segment['end'],
             'text': full_text,
             'words': current_segment['words']
        })
        
    return segments
