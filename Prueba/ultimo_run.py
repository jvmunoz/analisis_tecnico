import json
from pathlib import Path


def _fmt_value(v):
    return "-" if v is None else str(v)


def main():
    base_dir = Path(__file__).resolve().parent
    runs_dir = base_dir / "runs"
    latest_file = runs_dir / "latest_run.json"

    if not latest_file.exists():
        print(f"No existe {latest_file}")
        print("Ejecuta primero EstrategiaCombinadaRSI.py para generar un run.")
        return

    try:
        latest = json.loads(latest_file.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"No se pudo leer {latest_file}: {e}")
        return

    print("ULTIMO RUN")
    print(f"- updated_at: {_fmt_value(latest.get('updated_at'))}")
    print(f"- fecha_ultima: {_fmt_value(latest.get('fecha_ultima'))}")
    print(f"- run_started_at: {_fmt_value(latest.get('run_started_at'))}")
    print(f"- run_finished_at: {_fmt_value(latest.get('run_finished_at'))}")
    print(f"- duration_seconds: {_fmt_value(latest.get('duration_seconds'))}")
    print(f"- tickers_objetivo: {_fmt_value(latest.get('tickers_objetivo'))}")
    print(f"- tickers_procesados: {_fmt_value(latest.get('tickers_procesados'))}")
    print(f"- tickers_con_resultado: {_fmt_value(latest.get('tickers_con_resultado'))}")
    print(f"- errores: {_fmt_value(latest.get('errores'))}")

    output_dir = latest.get("output_dir")
    if not output_dir:
        print("\nNo hay output_dir en latest_run.json")
        return

    run_path = Path(output_dir)
    print(f"- output_dir: {run_path}")

    if not run_path.exists():
        print(f"\nNo existe la ruta de salida: {run_path}")
        return

    files = [p for p in run_path.iterdir() if p.is_file()]
    files.sort(key=lambda p: p.name.lower())

    print(f"\nARTEFACTOS ({len(files)})")
    for p in files:
        print(f"- {p.name}")


if __name__ == "__main__":
    main()
