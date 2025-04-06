import click
import requests
from ..utils.output import print_table, print_json

API_BASE_URL = "http://localhost:8000"

@click.group(name="pods")
def pods_group():
    """Manage pods and their resources"""
    pass

@pods_group.command(name="create")
@click.option("--name", "-n", required=True, help="Name of the pod")
@click.option("--cpu", "-c", type=int, required=True, help="Number of CPU cores")
@click.option("--memory", "-m", type=int, required=True, help="Memory in MB")
def create_pod(name: str, cpu: int, memory: int):
    """Create a new pod with specified resource requirements"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/pods",
            json={
                "name": name,
                "resources": {
                    "cpu_cores": cpu,
                    "memory_mb": memory
                }
            }
        )
        
        if response.status_code == 201:
            pod = response.json()
            click.echo(click.style("✅ Pod created successfully!", fg="green"))
            click.echo(f"Pod ID: {pod['id']}")
            click.echo(f"Name: {pod['name']}")
            click.echo(f"Status: {pod['status']}")
            click.echo(f"CPU Cores: {pod['resources']['cpu_cores']}")
            click.echo(f"Memory: {pod['resources']['memory_mb']}MB")
            if pod['node_id']:
                click.echo(f"Assigned to node: {pod['node_id']}")
        else:
            click.echo(click.style(f"❌ Failed to create pod: {response.text}", fg="red"))
    except Exception as e:
        click.echo(click.style(f"❌ Error: {str(e)}", fg="red"))

@pods_group.command(name="list")
@click.option("--format", "-f", type=click.Choice(["table", "json"]), default="table", 
              help="Output format (table or json)")
def list_pods(format: str):
    """List all pods and their resource allocations"""
    try:
        response = requests.get(f"{API_BASE_URL}/pods")
        if response.status_code == 200:
            pods = response.json()
            
            if format == "json":
                print_json(pods)
            else:
                headers = ["ID", "Name", "Status", "CPU Cores", "Memory", "Node ID"]
                rows = []
                
                for pod in pods:
                    rows.append([
                        pod["id"][:8] + "...",
                        pod["name"],
                        pod["status"],
                        str(pod["resources"]["cpu_cores"]),
                        f"{pod['resources']['memory_mb']}MB",
                        pod.get("node_id", "Not assigned")[:8] + "..." if pod.get("node_id") else "Not assigned"
                    ])
                
                print_table(headers, rows)
        else:
            click.echo(click.style(f"❌ Failed to retrieve pods: {response.text}", fg="red"))
    except Exception as e:
        click.echo(click.style(f"❌ Error: {str(e)}", fg="red"))

@pods_group.command(name="delete")
@click.argument("pod_id")
def delete_pod(pod_id: str):
    """Delete a pod and free its resources"""
    try:
        response = requests.delete(f"{API_BASE_URL}/pods/{pod_id}")
        if response.status_code == 204:
            click.echo(click.style("✅ Pod deleted successfully!", fg="green"))
        else:
            click.echo(click.style(f"❌ Failed to delete pod: {response.text}", fg="red"))
    except Exception as e:
        click.echo(click.style(f"❌ Error: {str(e)}", fg="red"))

@pods_group.command(name="inspect")
@click.argument("pod_id")
def inspect_pod(pod_id: str):
    """Show detailed information about a pod"""
    try:
        response = requests.get(f"{API_BASE_URL}/pods/{pod_id}")
        if response.status_code == 200:
            pod = response.json()
            print_json(pod)
        else:
            click.echo(click.style(f"❌ Pod not found: {response.text}", fg="red"))
    except Exception as e:
        click.echo(click.style(f"❌ Error: {str(e)}", fg="red"))

