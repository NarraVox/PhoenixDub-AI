import os
import sys
import shutil
from pipeline_engine import PipelineEngine

sys.stdout.reconfigure(encoding='utf-8')

def test_pipeline():
    print("[Test] Iniciando teste do Pipeline do Nexus-Godogen...")
    engine = PipelineEngine()
    
    # 1. Verificar executavel do Godot
    godot_path = engine.get_godot_path()
    print(f"Caminho do Godot: {godot_path}")
    if not os.path.exists(godot_path):
        print("Erro: Executavel do Godot nao encontrado no caminho indicado.")
        return False
        
    # 2. Configurar pastas e projeto
    game_name = "Teste_Pipeline_Game"
    print(f"Criando projeto de teste: {game_name}")
    proj_dir = engine.setup_project_structure(game_name)
    
    # 3. Escrever manualmente um script de build para testar a compilacao (SceneTree)
    builder_content = """extends SceneTree

func _init():
\tprint("⚙️ [SceneBuilder] Construindo cena de teste...")
\tvar root = Node3D.new()
\troot.name = "Main"
\t
\tvar box = CSGBox3D.new()
\tbox.name = "Floor"
\tbox.size = Vector3(30, 1, 30)
\tbox.use_collision = true
\troot.add_child(box)
\tbox.owner = root
\t
\tvar packed = PackedScene.new()
\tvar pack_err = packed.pack(root)
\tif pack_err == OK:
\t\tvar save_err = ResourceSaver.save(packed, "res://main.tscn")
\t\tif save_err == OK:
\t\t\tprint("✅ [SceneBuilder] Cena salva com sucesso!")
\t\telse:
\t\t\tprint("❌ [SceneBuilder] Erro ao salvar: ", save_err)
\telse:
\t\tprint("❌ [SceneBuilder] Erro ao empacotar: ", pack_err)
\t
\t# Encerra
\tquit()
"""
    
    with open(proj_dir / "builders" / "build_main.gd", "w", encoding="utf-8") as f:
        f.write(builder_content)
        
    # 4. Executar Scene Builder headlessly
    print("Executando Scene Builder...")
    build_success = engine.run_scene_builder(proj_dir)
    if not build_success:
        print("Compilacao falhou.")
        return False
    print("Compilacao concluida com sucesso.")
    
    # 5. Executar captura visual
    print("Executando Screenshot / Validacao Visual...")
    visual_success = engine.verify_game_visually(proj_dir)
    if not visual_success:
        print("Validacao visual falhou (screenshot nao foi criada).")
        return False
    print("Validacao visual concluida com sucesso (screenshot criada!).")
    
    print("\n[SUCESSO] O pipeline completo (Compilacao + Captura) esta funcionando perfeitamente no seu Windows!")
    return True

if __name__ == "__main__":
    success = test_pipeline()
    sys.exit(0 if success else 1)
