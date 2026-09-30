"""suno-muzik skill'ini ~/.claude/skills altına kurar; böylece Claude Code her klasörde kullanabilir."""
import shutil
from pathlib import Path

kaynak = Path(__file__).resolve().parent / "suno-muzik"
hedef = Path.home() / ".claude" / "skills" / "suno-muzik"

hedef.mkdir(parents=True, exist_ok=True)
for dosya in kaynak.iterdir():
    if dosya.is_file():
        shutil.copy2(dosya, hedef / dosya.name)

print(f"Kuruldu: {hedef}")
print("Claude Code'u yeniden başlatın ve örneğin şunu yazın:")
print('  "Suno\'da hüzünlü bir Türkçe akustik şarkı üret, proje: Deneme"')
