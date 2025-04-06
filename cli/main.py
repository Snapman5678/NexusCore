import click
import sys
import os

# Add parent directory to path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cli.commands.nodes import nodes_group
# from cli.commands.pods import pods_group
# from cli.commands.cluster import cluster_group

@click.group()
def cli():
    """NexusCore - A Distributed Systems Cluster Simulation Framework"""
    pass

# Add command groups
cli.add_command(nodes_group)
# cli.add_command(pods_group)
# cli.add_command(cluster_group)

if __name__ == '__main__':
    cli()

