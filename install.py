"""
Установка Krisha Parser Bot — копирует сборку в LocalAppData и создаёт ярлык на рабочий стол.

Запуск ПОСЛЕ build_portable.py:
    python install.py
"""
import os
import sys
import shutil


def get_install_dir() -> str:
    """Путь установки: %LOCALAPPDATA%\\Programs\\KrishaParser"""
    local = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
    return os.path.join(local, "Programs", "KrishaParser")


def get_desktop() -> str:
    """Путь к рабочему столу."""
    return os.path.join(os.path.expanduser("~"), "Desktop")


def create_shortcut(target_exe: str, shortcut_path: str, icon_path: str = None):
    """Создаёт ярлык Windows (.lnk) через PowerShell."""
    # PowerShell скрипт для создания ярлыка
    ps_script = f'''
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut("{shortcut_path}")
$sc.TargetPath = "{target_exe}"
$sc.WorkingDirectory = "{os.path.dirname(target_exe)}"
$sc.Description = "Krisha Parser Bot"
'''
    if icon_path and os.path.exists(icon_path):
        ps_script += f'$sc.IconLocation = "{icon_path}"\n'
    ps_script += '$sc.Save()\n'

    import subprocess
    result = subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
        capture_output=True, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    return result.returncode == 0


def install():
    # Находим dist
    root = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(root, "dist", "KrishaParser")

    if not os.path.exists(dist_dir):
        print("❌ Папка dist/KrishaParser не найдена!")
        print("   Сначала запустите: python build_portable.py")
        return False

    exe_in_dist = os.path.join(dist_dir, "KrishaParser.exe")
    if not os.path.exists(exe_in_dist):
        print("❌ KrishaParser.exe не найден в dist/KrishaParser/")
        return False

    install_dir = get_install_dir()

    print("=" * 60)
    print("📦 Установка Krisha Parser Bot")
    print(f"   Источник: {dist_dir}")
    print(f"   Назначение: {install_dir}")
    print("=" * 60)

    # Удаляем старую установку если есть (кроме данных пользователя)
    if os.path.exists(install_dir):
        print("🗑️ Удаляю предыдущую установку...")
        # Сохраняем пользовательские данные
        user_files = ["config.json", "phones.db"]
        user_dirs = ["sessions", os.path.join("wa-server", "wa_auth_data")]
        backup = {}

        for f in user_files:
            src = os.path.join(install_dir, f)
            if os.path.exists(src):
                backup[f] = open(src, "rb").read()

        backup_dirs = {}
        for d in user_dirs:
            src = os.path.join(install_dir, d)
            if os.path.exists(src):
                tmp = os.path.join(install_dir, f"_backup_{os.path.basename(d)}")
                try:
                    if os.path.exists(tmp):
                        shutil.rmtree(tmp)
                    shutil.move(src, tmp)
                    backup_dirs[d] = tmp
                except Exception:
                    pass

        # Удаляем всё
        try:
            shutil.rmtree(install_dir)
        except Exception as e:
            print(f"⚠️ Не удалось полностью удалить: {e}")

    # Копируем dist → install_dir
    print("📁 Копирую файлы...")
    shutil.copytree(dist_dir, install_dir)
    print(f"   ✅ Скопировано в {install_dir}")

    # Восстанавливаем пользовательские данные
    if 'backup' in dir() and backup:
        for f, data in backup.items():
            dst = os.path.join(install_dir, f)
            with open(dst, "wb") as fh:
                fh.write(data)
            print(f"   ♻️ Восстановлен: {f}")

    if 'backup_dirs' in dir() and backup_dirs:
        for d, tmp in backup_dirs.items():
            dst = os.path.join(install_dir, d)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            try:
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.move(tmp, dst)
                print(f"   ♻️ Восстановлена папка: {d}")
            except Exception:
                pass

    # Создаём ярлык на рабочий стол
    exe_path = os.path.join(install_dir, "KrishaParser.exe")
    icon_path = os.path.join(install_dir, "logo.ico")
    desktop = get_desktop()
    shortcut_path = os.path.join(desktop, "Krisha Parser Bot.lnk")

    print("🖥️ Создаю ярлык на рабочий стол...")
    if create_shortcut(exe_path, shortcut_path, icon_path):
        print(f"   ✅ Ярлык: {shortcut_path}")
    else:
        print(f"   ⚠️ Не удалось создать ярлык автоматически")
        print(f"   Создайте вручную: {exe_path}")

    print()
    print("=" * 60)
    print("✅ Установка завершена!")
    print(f"📁 Программа: {install_dir}")
    print(f"🖥️ Ярлык: {shortcut_path}")
    print("=" * 60)
    return True


if __name__ == "__main__":
    if not install():
        sys.exit(1)
