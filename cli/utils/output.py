# Pretty-printing tables

import json
import click
from typing import List, Any

def print_json(data: Any):
    """Print data as formatted JSON"""
    click.echo(json.dumps(data, indent=2))

def print_table(headers: List[str], rows: List[List[Any]]):
    """Print data as a formatted table"""
    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Print header
    header_row = "| " + " | ".join(f"{h:{w}}" for h, w in zip(headers, col_widths)) + " |"
    separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    
    click.echo(separator)
    click.echo(header_row)
    click.echo(separator)
    
    # Print rows
    for row in rows:
        formatted_row = "| " + " | ".join(f"{str(c):{w}}" for c, w in zip(row, col_widths)) + " |"
        click.echo(formatted_row)
    
    click.echo(separator)

