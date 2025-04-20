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

@nodes_group.command(name="stop")
@click.argument("node_id")
def stop_node(node_id: str):
    """Stop a node's container"""
    try:
        response = requests.post(f"{API_BASE_URL}/nodes/{node_id}/stop")
        if response.status_code == 200:
            click.echo(click.style(f"✅ Node {node_id} stopped successfully", fg="green"))
        else:
            click.echo(click.style(f"❌ Failed to stop node: {response.text}", fg="red"))
    except Exception as e:
        click.echo(click.style(f"❌ Error: {str(e)}", fg="red"))

@nodes_group.command(name="restart")
@click.argument("node_id")
def restart_node(node_id: str):
    """Restart a node's container"""
    try:
        response = requests.post(f"{API_BASE_URL}/nodes/{node_id}/restart")
        if response.status_code == 200:
            click.echo(click.style(f"✅ Node {node_id} restarted successfully", fg="green"))
        else:
            click.echo(click.style(f"❌ Failed to restart node: {response.text}", fg="red"))
    except Exception as e:
        click.echo(click.style(f"❌ Error: {str(e)}", fg="red"))

@nodes_group.command(name="delete")
@click.argument("node_id")
@click.option("--force", "-f", is_flag=True, help="Force delete without confirmation")
def delete_node(node_id: str, force: bool):
    """Delete a node and its container"""
    if not force:
        if not click.confirm(f"Are you sure you want to delete node {node_id}?"):
            click.echo("Operation cancelled.")
            return

    try:
        response = requests.delete(f"{API_BASE_URL}/nodes/{node_id}")
        if response.status_code == 200:
            click.echo(click.style(f"✅ Node {node_id} deleted successfully", fg="green"))
        else:
            click.echo(click.style(f"❌ Failed to delete node: {response.text}", fg="red"))
    except Exception as e:
        click.echo(click.style(f"❌ Error: {str(e)}", fg="red"))

@nodes_group.command(name="resources")
@click.argument("node_id")
def get_node_resources(node_id: str):
    """Show resource utilization of a specific node"""
    try:
        response = requests.get(f"{API_BASE_URL}/nodes/{node_id}/resources")
        if response.status_code == 200:
            resources = response.json()
            click.echo(click.style(f"Node {node_id} Resource Utilization:", fg="blue"))
            click.echo(f"CPU: {resources['cpu_available']}/{resources['total_cpu']} cores available")
            click.echo(f"CPU Utilization: {resources['cpu_utilization_percent']:.1f}%")
            memory_mb_available = resources['memory_available'] / (1024 * 1024)
            memory_mb_total = resources['total_memory'] / (1024 * 1024)
            click.echo(f"Memory: {memory_mb_available:.1f}MB/{memory_mb_total:.1f}MB available")
            click.echo(f"Memory Utilization: {resources['memory_utilization_percent']:.1f}%")
        else:
            click.echo(click.style(f"❌ Failed to get node resources: {response.text}", fg="red"))
    except Exception as e:
        click.echo(click.style(f"❌ Error: {str(e)}", fg="red"))

@nodes_group.command(name="pods")
@click.argument("node_id")
@click.option("--format", "-f", type=click.Choice(["table", "json"]), default="table", 
              help="Output format (table or json)")
def list_node_pods(node_id: str, format: str):
    """List all pods running on a specific node"""
    try:
        response = requests.get(f"{API_BASE_URL}/nodes/{node_id}/pods")
        if response.status_code == 200:
            pods = response.json()
            
            if not pods:
                click.echo(f"No pods running on node {node_id}")
                return
                
            if format == "json":
                print_json(pods)
            else:
                headers = ["ID", "Name", "Status", "CPU Cores", "Memory", "Created At"]
                rows = []
                
                for pod in pods:
                    created_at = pod.get("created_at", "Unknown")
                    if created_at != "Unknown":
                        created_at = created_at.replace("T", " ").split(".")[0]
                        
                    rows.append([
                        pod["id"][:8] + "...",
                        pod["name"],
                        pod["status"],
                        pod["resources"]["cpu_cores"],
                        f"{pod['resources']['memory_mb']}MB",
                        created_at
                    ])
                
                print_table(headers, rows)
        else:
            click.echo(click.style(f"❌ Failed to retrieve pods: {response.text}", fg="red"))
    except Exception as e:
        click.echo(click.style(f"❌ Error: {str(e)}", fg="red"))

@nodes_group.command(name="shutdown")
@click.argument("node_id")
def shutdown_node(node_id: str):
    """Handle graceful node shutdown"""
    try:
        response = requests.post(f"{API_BASE_URL}/nodes/{node_id}/shutdown")
        if response.status_code == 200:
            click.echo(click.style(f"✅ Node {node_id} shutdown handled successfully", fg="green"))
        else:
            click.echo(click.style(f"❌ Failed to handle shutdown: {response.text}", fg="red"))
    except Exception as e:
        click.echo(click.style(f"❌ Error: {str(e)}", fg="red"))

