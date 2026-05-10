import psutil
import os
import signal

def kill_bot_processes():
    # Hozirgi ishlayotgan ushbu skriptning ID sini olamiz (o'zini o'zi o'chirib yubormaslik uchun)
    current_pid = os.getpid()
    found = False

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Jarayon nomi 'python' bo'lsa va komanda satrida 'main.py' bo'lsa
            cmdline = proc.info.get('cmdline')
            if cmdline and any('main.py' in arg for arg in cmdline):
                pid = proc.info['pid']
                if pid != current_pid:
                    print(f"To'xtatilmoqda: PID {pid} ({' '.join(cmdline)})")
                    os.kill(pid, signal.SIGTERM) # Jarayonni to'xtatish
                    found = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    if not found:
        print("Hech qanday ishlayotgan bot jarayonlari topilmadi.")
    else:
        print("✅ Barcha botlar to'xtatildi.")

if __name__ == "__main__":
    kill_bot_processes()