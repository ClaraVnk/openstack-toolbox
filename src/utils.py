#!/usr/bin/env python3

from datetime import datetime
from typing import Optional, Tuple

from rich import print

from .exceptions import ParsingError


def format_size(size_bytes: int) -> str:
    """
    Formate une taille en bytes dans l'unité la plus appropriée.

    Args:
        size_bytes: Taille en bytes à formater

    Returns:
        Taille formatée avec l'unité appropriée (To, Go, Mo, Ko, octets)

    Examples:
        >>> format_size(1500)
        '1.50 Ko'
        >>> format_size(1500000000)
        '1.50 Go'
    """
    units = [("To", 1000000000000), ("Go", 1000000000), ("Mo", 1000000), ("Ko", 1000)]

    for unit, threshold in units:
        if size_bytes >= threshold:
            size = size_bytes / threshold
            return f"{size:.2f} {unit}"
    return f"{size_bytes} octets"


def parse_flavor_name(
    name: str,
) -> Tuple[Optional[str], Optional[int], Optional[int], Optional[int]]:
    """
    Parse un nom de flavor OpenStack et extrait les informations de ressources.

    Le format attendu est 'aX-ramY-diskZ' où:
    - X est le nombre de vCPUs
    - Y est la quantité de RAM en Go
    - Z est la taille du disque en Go

    Args:
        name: Nom du flavor à parser (ex: 'a2-ram4-disk50')

    Returns:
        Tuple contenant:
            - Description lisible des ressources (ou None)
            - Nombre de vCPUs (ou None)
            - Quantité de RAM en Go (ou None)
            - Taille du disque en Go (ou None)

    Examples:
        >>> parse_flavor_name('a2-ram4-disk50')
        ('2 vCPU / 4 Go RAM / 50 Go disque', 2, 4, 50)
        >>> parse_flavor_name('invalid')
        (None, None, None, None)
    """
    try:
        parts = name.split("-")
        cpu_part = next(
            (p for p in parts if p.startswith("a") and p[1:].isdigit()), None
        )
        ram_part = next(
            (p for p in parts if p.startswith("ram") and p[3:].isdigit()),
            None,
        )
        disk_part = next(
            (p for p in parts if p.startswith("disk") and p[4:].isdigit()),
            None,
        )

        cpu = int(cpu_part[1:]) if cpu_part else None
        ram = int(ram_part[3:]) if ram_part else None
        disk = int(disk_part[4:]) if disk_part else None

        if all(v is not None for v in [cpu, ram, disk]):
            desc = f"{cpu} vCPU / {ram} Go RAM / {disk} Go disque"
            return desc, cpu, ram, disk
    except (ValueError, IndexError, AttributeError):
        # Return None values if parsing fails
        pass
    return None, None, None, None


def isoformat(dt: datetime) -> str:
    """
    Convertit un objet datetime en chaîne ISO 8601 avec timezone.

    Args:
        dt (datetime): Objet datetime à convertir

    Returns:
        str: Date formatée en ISO 8601 avec timezone

    Examples:
        >>> from datetime import datetime, timezone
        >>> dt = datetime(2024, 3, 15, 14, 30, tzinfo=timezone.utc)
        >>> isoformat(dt)
        '2024-03-15T14:30:00+00:00'
    """
    return dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def print_header(header: str) -> None:
    """
    Affiche un en-tête formaté avec Rich.

    Args:
        header: Le texte de l'en-tête à afficher

    Examples:
        >>> print_header("LISTE DES INSTANCES")
        ==========================================
        [yellow bold]         LISTE DES INSTANCES         [/yellow bold]
        ==========================================
    """
    print("\n" + "=" * 50)
    print(f"[yellow bold]{header.center(50)}[/yellow bold]")
    print("=" * 50 + "\n")
