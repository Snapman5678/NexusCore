import click
import requests
from typing import Optional
from ..utils.output import print_table, print_json

API_BASE_URL = "http://localhost:8000"

@click.group(name="nodes")
def nodes_group():
    """Manage cluster nodes"""
    pass

@nodes_group.command(name="add")
@click.option("--cpu", "-c", type=int, default=1, help="Number of CPU cores for the node")
@click.option("--memory", "-m", type=int, help="Memory in MB for the node")
def add_node(cpu: int, memory: Optional[int]):
    """Add a new node to the cluster with specified resources"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/nodes",
            json={"cpu_count": cpu, "memory_mb": memory}
        )
        
        if response.status_code == 201:
            node_data = response.json()
            click.echo(click.style("✅ Node added successfully!", fg="green"))
            click.echo(f"Node ID: {node_data['id']}")
            click.echo(f"Hostname: {node_data['hostname']}")
            click.echo(f"Status: {node_data['status']}")
            click.echo(f"CPU Cores: {node_data['resources']['cpu_count']}")
            if memory:
                click.echo(f"Memory: {memory}MB")
        else:
            click.echo(click.style(f"❌ Failed to add node: {response.text}", fg="red"))
    except Exception as e:
        click.echo(click.style(f"❌ Error: {str(e)}", fg="red"))

@nodes_group.command(name="list")
@click.option("--format", "-f", type=click.Choice(["table", "json"]), default="table", 
              help="Output format (table or json)")
def list_nodes(format: str):
    """List all nodes in the cluster"""
    try:
        response = requests.get(f"{API_BASE_URL}/nodes")
        if response.status_code == 200:
            nodes = response.json()
            
            if format == "json":
                print_json(nodes)
            else:
                headers = ["ID", "Hostname", "Status", "CPU Cores", "Memory Available", "Last Heartbeat"]
                rows = []
                
                for node in nodes:
                    memory_mb = node["resources"]["memory_available"] / (1024 * 1024)
                    last_heartbeat = node.get("last_heartbeat", "Never")
                    if last_heartbeat != "Never":
                        last_heartbeat = last_heartbeat.replace("T", " ").split(".")[0]
                        
                    rows.append([
                        node["id"][:8] + "...",
                        node["hostname"],
                        node["status"],
                        node["resources"]["cpu_count"],
                        f"{memory_mb:.1f}MB",
                        last_heartbeat
                    ])
                
                print_table(headers, rows)
        else:
            click.echo(click.style(f"❌ Failed to retrieve nodes: {response.text}", fg="red"))
    except Exception as e:
        click.echo(click.style(f"❌ Error: {str(e)}", fg="red"))

@nodes_group.command(name="inspect")
@click.argument("node_id")
def inspect_node(node_id: str):
    """Show detailed information about a specific node"""
    try:
        response = requests.get(f"{API_BASE_URL}/nodes/{node_id}")
        if response.status_code == 200:
            node = response.json()
            print_json(node)
        else:
            click.echo(click.style(f"❌ Node not found: {response.text}", fg="red"))
    except Exception as e:
        click.echo(click.style(f"❌ Error: {str(e)}", fg="red"))

