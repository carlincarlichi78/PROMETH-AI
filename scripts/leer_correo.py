"""CLI para ingesta de email via IMAP — SFCE Task 42.

Uso basico:
    python scripts/leer_correo.py \\
        --servidor imap.gmail.com \\
        --usuario x@gmail.com \\
        --contrasena "mi_contrasena" \\
        --ruta-base clientes/

Con archivo de configuracion YAML:
    python scripts/leer_correo.py --config config_email.yaml

Formato del archivo YAML de configuracion:
    servidor: imap.gmail.com
    puerto: 993
    usuario: contabilidad@empresa.com
    contrasena: "mi_contrasena"
    carpeta: INBOX
    ssl: true
    marcar_leidos: true
    ruta_base: clientes/
    clientes:
      proveedor@empresa.com: empresa-sl
      facturas@iberdrola.es: pastorino-costa-del-sol
"""
import argparse
import sys
from pathlib import Path

import yaml

# Asegurar que el directorio raiz del proyecto esta en el path
_RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_RAIZ))

from sfce.core.ingesta_email import ConfigEmail, procesar_correo


def _cargar_config_yaml(ruta: str) -> tuple[ConfigEmail, dict, str]:
    """Lee el archivo YAML y retorna (ConfigEmail, mapa_clientes, ruta_base)."""
    datos = yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))

    cfg = ConfigEmail(
        servidor=datos["servidor"],
        puerto=int(datos.get("puerto", 993)),
        usuario=datos["usuario"],
        contrasena=datos["contrasena"],
        carpeta=datos.get("carpeta", "INBOX"),
        ssl=bool(datos.get("ssl", True)),
        marcar_leidos=bool(datos.get("marcar_leidos", True)),
    )
    mapa = datos.get("clientes", {})
    ruta_base = datos.get("ruta_base", "clientes/")
    return cfg, mapa, ruta_base


def _imprimir_resultado(resultado: dict) -> None:
    print(f"\nResumen de ingesta de email:")
    print(f"  Emails procesados : {resultado['procesados']}")
    print(f"  Clasificados      : {resultado['clasificados']}")
    print(f"  Sin clasificar    : {resultado['sin_clasificar']}")
    print(f"  Errores           : {resultado['errores']}")

    if resultado["detalle"]:
        print("\nDetalle:")
        for entrada in resultado["detalle"]:
            uid = entrada["uid"]
            slug = entrada.get("slug") or "_sin_clasificar"
            n_adj = len(entrada.get("adjuntos", []))
            error = entrada.get("error")
            if error:
                print(f"  UID {uid}: ERROR — {error}")
            else:
                print(f"  UID {uid}: {n_adj} adjunto(s) → {slug}")


def main():
    parser = argparse.ArgumentParser(
        description="Leer correos IMAP y guardar PDFs adjuntos en inbox de clientes SFCE"
    )

    # Opcion 1: archivo de configuracion
    parser.add_argument("--config", help="Ruta al archivo YAML de configuracion")

    # Opcion 2: parametros directos
    parser.add_argument("--servidor", help="Servidor IMAP (ej: imap.gmail.com)")
    parser.add_argument("--puerto", type=int, default=993, help="Puerto IMAP (defecto: 993)")
    parser.add_argument("--usuario", help="Usuario IMAP (email)")
    parser.add_argument("--contrasena", help="Contrasena IMAP")
    parser.add_argument("--carpeta", default="INBOX", help="Carpeta IMAP (defecto: INBOX)")
    parser.add_argument("--sin-ssl", action="store_true", help="Desactivar SSL")
    parser.add_argument("--no-marcar-leidos", action="store_true", help="No marcar emails como leidos")
    parser.add_argument("--ruta-base", default="clientes/", help="Directorio base de clientes")

    args = parser.parse_args()

    if args.config:
        cfg, mapa_clientes, ruta_base = _cargar_config_yaml(args.config)
    else:
        if not all([args.servidor, args.usuario, args.contrasena]):
            parser.error("Se requieren --servidor, --usuario y --contrasena (o bien --config)")

        cfg = ConfigEmail(
            servidor=args.servidor,
            puerto=args.puerto,
            usuario=args.usuario,
            contrasena=args.contrasena,
            carpeta=args.carpeta,
            ssl=not args.sin_ssl,
            marcar_leidos=not args.no_marcar_leidos,
        )
        mapa_clientes = {}
        ruta_base = args.ruta_base

    print(f"Conectando a {cfg.servidor}:{cfg.puerto} como {cfg.usuario}...")
    try:
        resultado = procesar_correo(cfg, mapa_clientes, ruta_base)
        _imprimir_resultado(resultado)
        sys.exit(0 if resultado["errores"] == 0 else 1)
    except ConnectionError as e:
        print(f"Error de conexion: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
