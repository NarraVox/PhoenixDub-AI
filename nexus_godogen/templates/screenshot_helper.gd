extends Node

func _ready() -> void:
	print("📸 [ScreenshotHelper] Iniciado. Aguardando inicialização do jogo...")
	# Espera 1.5 segundos para o motor carregar texturas, iluminação e física
	await get_tree().create_timer(1.5).timeout
	take_screenshot()

func take_screenshot() -> void:
	print("📸 [ScreenshotHelper] Capturando tela do viewport...")
	var viewport = get_viewport()
	if viewport:
		# Forçar a renderização do frame para garantir que a imagem não venha em branco
		await get_tree().process_frame
		await get_tree().process_frame
		
		var img = viewport.get_texture().get_image()
		if img:
			# No Godot, texturas de Viewport podem vir invertidas verticalmente por padrão.
			# Corrigimos isso flipando a imagem no eixo Y.
			img.flip_y()
			
			var save_path = "res://screenshot.png"
			var err = img.save_png(save_path)
			if err == OK:
				print("✅ [ScreenshotHelper] Imagem salva com sucesso em: ", ProjectSettings.globalize_path(save_path))
				print("[SCREENSHOT_SAVED]")
			else:
				print("❌ [ScreenshotHelper] Falha ao salvar imagem de teste: ", err)
		else:
			print("❌ [ScreenshotHelper] Erro: Textura do Viewport está nula.")
	
	# Encerra o jogo
	print("🚪 [ScreenshotHelper] Fechando o jogo após validação visual.")
	get_tree().quit()
