# Cluster status/auto-scaling

import click
import requests
from ..utils.output import print_table, print_json

API_BASE_URL = "http://localhost:8000"

@click.group(name="cluster")
def cluster_group():
    """Manage cluster resources and health"""
    pass

@cluster_group.command(name="health")
@click.option("--format", "-f", type=click.Choice(["table", "json"]), default="table")
def cluster_health(format: str):
    """Show cluster resource health metrics"""
    try:
        # Get host resources
        host_response = requests.get(f"{API_BASE_URL}/host/resources")
        if host_response.status_code != 200:
            click.echo(click.style("❌ Failed to get host metrics", fg="red"))
            return

        # Get all nodes
        nodes_response = requests.get(f"{API_BASE_URL}/nodes")
        if nodes_response.status_code != 200:
            click.echo(click.style("❌ Failed to get nodes", fg="red"))
            return

        host_metrics = host_response.json()
        nodes = nodes_response.json()

        if format == "json":
            print_json({
                "host": host_metrics,
                "nodes": nodes
            })
        else:
            # Print host metrics
            click.echo(click.style("\nHost System Resources:", fg="green", bold=True))
            host_headers = ["CPU Cores", "Memory Total", "Memory Available", "CPU Limit", "Memory Limit"]
            host_row = [
                str(host_metrics["cpu_count"]),
                f"{host_metrics['memory_total'] / (1024*1024*1024):.1f}GB",
                f"{host_metrics['memory_available'] / (1024*1024*1024):.1f}GB",
                f"{host_metrics['cpu_limit_percent']}%",
                f"{host_metrics['memory_limit_percent']}%"
            ]
            print_table(host_headers, [host_row])

            # Print node metrics
            click.echo(click.style("\nNode Resources:", fg="green", bold=True))
            node_headers = ["Node ID", "Status", "CPU Usage", "Memory Usage"]
            node_rows = []

            for node in nodes:
                if node["status"] == "online":
                    memory_usage = (1 - (node["resources"]["memory_available"] / node["resources"]["memory_total"])) * 100
                    node_rows.append([
                        node["id"][:8] + "...",
                        node["status"],
                        f"{(node['resources']['cpu_count'])}",
                        f"{memory_usage:.1f}%"
                    ])

            print_table(node_headers, node_rows)

    except Exception as e:
        click.echo(click.style(f"❌ Error: {str(e)}", fg="red"))

@cluster_group.command(name="limits")
@click.option("--cpu", "-c", type=float, help="CPU usage limit in percentage")
@click.option("--memory", "-m", type=float, help="Memory usage limit in percentage")
def update_limits(cpu: float, memory: float):
    """Update cluster resource usage limits"""
    if not cpu and not memory:
        click.echo("Please specify at least one limit to update (--cpu or --memory)")
        return

    try:
        current_response = requests.get(f"{API_BASE_URL}/host/resources")
        if current_response.status_code != 200:
            click.echo(click.style("❌ Failed to get current limits", fg="red"))
            return

        current_limits = current_response.json()
        
        new_limits = {
            "cpu_limit_percent": cpu if cpu is not None else current_limits["cpu_limit_percent"],
            "memory_limit_percent": memory if memory is not None else current_limits["memory_limit_percent"]
        }

        response = requests.put(
            f"{API_BASE_URL}/host/resources/limits",
            json=new_limits
        )

        if response.status_code == 200:
            click.echo(click.style("✅ Resource limits updated successfully!", fg="green"))
            click.echo(f"New CPU limit: {new_limits['cpu_limit_percent']}%")
            click.echo(f"New Memory limit: {new_limits['memory_limit_percent']}%")
        else:
            click.echo(click.style(f"❌ Failed to update limits: {response.text}", fg="red"))

    except Exception as e:
        click.echo(click.style(f"❌ Error: {str(e)}", fg="red"))

