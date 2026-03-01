#!/usr/bin/env python3
"""Motor de Escenarios de Campo SFCE — CLI."""
import argparse
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main():
    parser = argparse.ArgumentParser(description="Motor de Escenarios de Campo SFCE")
    parser.add_argument("--modo", choices=["rapido", "completo", "continuo"], default="rapido")
    parser.add_argument("--escenario", help="ID de escenario especifico")
    parser.add_argument("--grupo", help="Grupo de escenarios (ej: facturas_cliente)")
    parser.add_argument("--pausa", type=int, default=300, help="Segundos entre ciclos (modo continuo)")
    parser.add_argument("--max-variantes", type=int, default=20)
    args = parser.parse_args()

    from scripts.motor_campo.orquestador import Orquestador

    orquestador = Orquestador(
        sfce_api_url=os.getenv("SFCE_API_URL", "http://localhost:8000"),
        fs_api_url=os.getenv("FS_API_URL", "https://contabilidad.lemonfresh-tuc.com/api/3"),
        fs_token=os.getenv("FS_API_TOKEN", ""),
        empresa_id=3,
        codejercicio="0003",
        max_variantes=args.max_variantes,
    )

    ruta = orquestador.run(
        modo=args.modo,
        escenario_id=args.escenario,
        grupo=args.grupo,
        pausa=args.pausa,
    )
    print(f"\nReporte generado: {ruta}")


if __name__ == "__main__":
    main()
