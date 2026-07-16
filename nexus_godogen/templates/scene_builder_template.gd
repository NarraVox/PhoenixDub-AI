extends SceneTree

# Função recursiva auxiliar para definir o proprietário (Owner) de todos os filhos criados
# Isso é obrigatório no Godot para que os nós secundários sejam salvos no arquivo .tscn
func set_owner_on_nodes(node: Node, scene_owner: Node) -> void:
	for child in node.get_children():
		child.owner = scene_owner
		# Se o nó filho não tem caminho de cena de origem (ou seja, foi criado dinamicamente), recorremos
		if child.scene_file_path.is_empty():
			set_owner_on_nodes(child, scene_owner)

func _init() -> void:
	print("⚙️ [SceneBuilder] Iniciando montagem de cena programática (SceneTree)...")
	
	# Criar nó raiz da cena (ex: Node3D para 3D, Node2D para 2D, Control para UI)
	var root = Node3D.new()
	root.name = "Main"
	
	# ==========================================
	# CONSTRUÇÃO DE ESTRUTURAS (IA adicionará aqui)
	# ==========================================
	
	# Exemplo: Luz Direcional (Sol)
	var sun = DirectionalLight3D.new()
	sun.name = "Sun"
	sun.rotation_degrees = Vector3(-45, -30, 0)
	sun.shadow_enabled = true
	root.add_child(sun)
	
	# Exemplo: Ambiente
	var world_env = WorldEnvironment.new()
	world_env.name = "WorldEnvironment"
	var env = Environment.new()
	env.background_mode = Environment.BG_CLEAR_COLOR
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	world_env.environment = env
	root.add_child(world_env)
	
	# Exemplo: Chão CSG (Colisão Automática)
	var floor_box = CSGBox3D.new()
	floor_box.name = "Floor"
	floor_box.size = Vector3(40, 1, 40)
	floor_box.use_collision = true
	root.add_child(floor_box)
	
	# ==========================================
	# ASSOCIAÇÃO DE SCRIPTS E SALVAMENTO
	# ==========================================
	
	# Define owner para todos os nós criados recursivamente
	set_owner_on_nodes(root, root)
	
	var packed = PackedScene.new()
	var pack_err = packed.pack(root)
	if pack_err == OK:
		var save_err = ResourceSaver.save(packed, "res://main.tscn")
		if save_err == OK:
			print("✅ [SceneBuilder] Cena salva com sucesso em: res://main.tscn")
		else:
			print("❌ [SceneBuilder] Erro ao salvar arquivo .tscn: ", save_err)
	else:
		print("❌ [SceneBuilder] Erro ao empacotar cena: ", pack_err)
		
	# ENCERRA O PROCESSO DO GODOT
	quit()
