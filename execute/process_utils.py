import os
import platform
import psutil
import random


def get_os_type() -> str:
    return platform.system()

def get_cpu_freq(percpu=False):
    return psutil.cpu_freq(percpu=percpu)

def get_cpu_percent(interval: int=0.2, percpu: bool=True):
    return psutil.cpu_percent(interval=interval, percpu=percpu)

def get_idle_cpu(available_cpus=None, ratio=5.0):
    cpus = get_cpu_percent()
    available_cpus = set(available_cpus) if available_cpus else None

    usable_cpus = [
        i for i, usage in enumerate(cpus)
        if usage <= ratio and (available_cpus is None or i in available_cpus)
    ]

    if not usable_cpus:
        return -1
    return random.choice(usable_cpus)

def get_cpu_num(logical=True):
    return psutil.cpu_count(logical=logical)

def get_affinity_cpu_num():
    process = psutil.Process()
    return len(process.cpu_affinity())

def get_affinity_cpu():
    process = psutil.Process()
    return process.cpu_affinity()

def get_swap_memory():
    return psutil.swap_memory()

def get_disk_usage(drive_path):
    return psutil.disk_usage(drive_path)

def get_disk_partitions():
    return psutil.disk_partitions()

def get_pids():
    return psutil.pids()

def get_process_info(pid: int=-1) -> dict:
    try:
        if pid == -1:
            procs = {}
            for p in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
                procs[p.info['pid']] = p.info
            return procs
        else:
            p = psutil.Process(pid)
            return {
                "pid": p.pid,
                "name": p.name(),
                "exe": p.exe() if p.exe() else None,
                "cmdline": p.cmdline(),
                "username": p.username(),
                "status": p.status(),
                "cpu_percent": p.cpu_percent(interval=0.1),
                "memory_percent": p.memory_percent(),
                "create_time": p.create_time(),
                "num_threads": p.num_threads(),
            }
            return info
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return {}

def get_pid_exits(pid:int):
    return psutil.pid_exists(pid)

def suspend_process(pid: int) -> bool:
    try:
        p = psutil.Process(pid)
        p.suspend()
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False

def resume_process(pid: int) -> bool:
    try:
        p = psutil.Process(pid)
        p.resume()
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False

def kill_process(pid: int):
    try:
        p = psutil.Process(pid)
        p.terminate()
        p.wait(timeout=3)
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
        return False

def kill_process_with_children(pid: int) -> None:
    def _on_terminate(proc):
        print(f'process {proc} terminated with exit code {proc.returncode}')

    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        if not children:
            return

        for p in children:
            try:
                p.terminate()
            except psutil.NoSuchProcess:
                continue

        gone, alive = psutil.wait_procs(children, timeout=5, callback=_on_terminate)
        for p in alive:
            try:
                p.kill()
            except psutil.NoSuchProcess:
                continue
    except psutil.NoSuchProcess:
        pass

def assign_cpu(pid: int = None, cpu_num: int = 0) -> bool:
    if pid is None:
        pid = os.getpid()

    if cpu_num not in range(psutil.cpu_count()):
        raise ValueError(f"Invalid cpu_num: {cpu_num}")

    system = platform.system()
    try:
        if system == 'Windows':
            psutil.Process(pid).cpu_affinity([cpu_num])
        elif system == 'Linux':
            os.sched_setaffinity(pid, {cpu_num})
        else:
            return False
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError, OSError):
        return False



