"""Console interface for FrappeBR."""

import time
from typing import List, Optional, Dict, Any, Callable
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.layout import Layout
from rich.live import Live

from ..models.config import SSHConfig, SiteInfo, BackupInfo, BackupSet
from ..core.transfer_manager import TransferProgress


class ConsoleUI:
    """Rich console interface for FrappeBR."""
    
    def __init__(self):
        self.console = Console()
        
    def print_header(self):
        """Print application header."""
        header = Panel.fit(
            "[bold blue]FrappeBR - Frappe Backup & Restore Tool[/bold blue]\n"
            "[dim]Secure backup and restore for Frappe sites[/dim]",
            style="blue"
        )
        self.console.print(header)
        self.console.print()
    
    def print_error(self, message: str):
        """Print error message."""
        self.console.print(f"[bold red]Error:[/bold red] {message}")
    
    def print_warning(self, message: str):
        """Print warning message."""
        self.console.print(f"[bold yellow]Warning:[/bold yellow] {message}")
    
    def print_success(self, message: str):
        """Print success message."""
        self.console.print(f"[bold green]Success:[/bold green] {message}")
    
    def print_info(self, message: str):
        """Print info message."""
        self.console.print(f"[bold cyan]Info:[/bold cyan] {message}")
    
    def show_main_menu(self) -> str:
        """Show main menu and return selected option."""
        self.console.print(Panel.fit(
            "[bold]Main Menu[/bold]\n\n"
            "1. Connect to Remote Host\n"
            "2. Manage Local Backups\n"
            "3. Restore from Backup\n"
            "4. Settings & Configuration\n"
            "5. View Operation History\n"
            "6. Exit",
            title="FrappeBR",
            style="cyan"
        ))
        
        choice = Prompt.ask(
            "Select an option",
            choices=["1", "2", "3", "4", "5", "6"],
            default="1"
        )
        return choice
    
    def select_ssh_host(self, hosts: List[SSHConfig]) -> Optional[SSHConfig]:
        """Display SSH hosts and let user select one."""
        if not hosts:
            self.print_warning("No SSH hosts found in config")
            hostname = Prompt.ask("Enter hostname manually")
            return None if not hostname else SSHConfig(host=hostname, hostname=hostname, user="root")
        
        table = Table(title="Available SSH Hosts")
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("Host", style="magenta")
        table.add_column("Hostname", style="green")
        table.add_column("User", style="yellow")
        table.add_column("Port", justify="right")
        
        for i, host in enumerate(hosts, 1):
            table.add_row(
                str(i),
                host.host,
                host.hostname,
                host.user,
                str(host.port)
            )
        
        self.console.print(table)
        
        try:
            choice = Prompt.ask(
                f"Select host (1-{len(hosts)}) or 'm' for manual entry",
                default="1"
            )
            
            if choice.lower() == 'm':
                hostname = Prompt.ask("Enter hostname")
                user = Prompt.ask("Enter username", default="root")
                return SSHConfig(host=hostname, hostname=hostname, user=user)
            
            idx = int(choice) - 1
            if 0 <= idx < len(hosts):
                return hosts[idx]
            
        except (ValueError, IndexError):
            pass
        
        self.print_error("Invalid selection")
        return None
    
    def show_connection_status(self, hostname: str, success: bool):
        """Show connection status."""
        if success:
            self.print_success(f"Connected to {hostname}")
        else:
            self.print_error(f"Failed to connect to {hostname}")
    
    def select_frappe_bench(self, bench_paths: List[str]) -> Optional[str]:
        """Let user select a frappe-bench directory."""
        if not bench_paths:
            self.print_warning("No frappe-bench directories found")
            return Prompt.ask("Enter bench path manually", default="")
        
        if len(bench_paths) == 1:
            self.print_info(f"Using bench: {bench_paths[0]}")
            return bench_paths[0]
        
        table = Table(title="Available Frappe Benches")
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("Path", style="green")
        
        for i, path in enumerate(bench_paths, 1):
            table.add_row(str(i), path)
        
        self.console.print(table)
        
        try:
            choice = Prompt.ask(f"Select bench (1-{len(bench_paths)})", default="1")
            idx = int(choice) - 1
            if 0 <= idx < len(bench_paths):
                return bench_paths[idx]
        except (ValueError, IndexError):
            pass
        
        self.print_error("Invalid selection")
        return None
    
    def display_sites(self, sites: List[SiteInfo]) -> Optional[SiteInfo]:
        """Display sites and let user select one."""
        if not sites:
            self.print_warning("No sites found")
            return None
        
        table = Table(title="Available Sites")
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("Site Name", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Apps", style="yellow")
        table.add_column("Size (MB)", justify="right")
        table.add_column("Last Modified")
        
        for i, site in enumerate(sites, 1):
            status = "Active" if site.is_active else "Inactive"
            apps_str = ", ".join(site.apps[:3])  # Show first 3 apps
            if len(site.apps) > 3:
                apps_str += f" (+{len(site.apps) - 3})"
            
            size_str = f"{site.size_mb:.1f}" if site.size_mb else "Unknown"
            modified_str = site.last_modified.strftime("%Y-%m-%d %H:%M") if site.last_modified else "Unknown"
            
            table.add_row(
                str(i),
                site.name,
                status,
                apps_str,
                size_str,
                modified_str
            )
        
        self.console.print(table)
        
        try:
            choice = Prompt.ask(f"Select site (1-{len(sites)})")
            idx = int(choice) - 1
            if 0 <= idx < len(sites):
                return sites[idx]
        except (ValueError, IndexError):
            pass
        
        self.print_error("Invalid selection")
        return None
    
    def show_backup_menu(self) -> str:
        """Show backup management menu."""
        self.console.print(Panel.fit(
            "[bold]Backup Management[/bold]\n\n"
            "1. List existing backups\n"
            "2. Create new backup\n"
            "3. Download backup\n"
            "4. Back to main menu",
            style="green"
        ))
        
        return Prompt.ask("Select option", choices=["1", "2", "3", "4"], default="1")
    
    def display_backups(self, backups: List[BackupInfo]) -> Optional[BackupInfo]:
        """Display individual backups and let user select one."""
        if not backups:
            self.print_warning("No backups found")
            return None
        
        table = Table(title="Available Backups")
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("Filename", style="magenta")
        table.add_column("Type", style="green")
        table.add_column("Size (MB)", justify="right")
        table.add_column("Created", style="yellow")
        
        for i, backup in enumerate(backups, 1):
            table.add_row(
                str(i),
                backup.filename,
                backup.backup_type.title(),
                f"{backup.size_mb:.1f}",
                backup.created_at.strftime("%Y-%m-%d %H:%M")
            )
        
        self.console.print(table)
        
        try:
            choice = Prompt.ask(f"Select backup (1-{len(backups)})")
            idx = int(choice) - 1
            if 0 <= idx < len(backups):
                return backups[idx]
        except (ValueError, IndexError):
            pass
        
        self.print_error("Invalid selection")
        return None
    
    def display_backup_sets(self, backup_sets: List[BackupSet]) -> Optional[BackupSet]:
        """Display backup sets and let user select one."""
        if not backup_sets:
            self.print_warning("No backups found")
            return None
        
        table = Table(title="Available Backups")
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("Backup Set", style="magenta")
        table.add_column("Type", style="green")
        table.add_column("Size (MB)", justify="right")
        table.add_column("Created", style="yellow")
        table.add_column("Files", justify="right", style="dim")
        
        for i, backup_set in enumerate(backup_sets, 1):
            # Show a representative name for the backup set
            display_name = f"{backup_set.timestamp}-{backup_set.site_name.replace('.', '_')}"
            
            table.add_row(
                str(i),
                display_name,
                backup_set.backup_type.title(),
                f"{backup_set.total_size_mb:.1f}",
                backup_set.created_at.strftime("%Y-%m-%d %H:%M"),
                str(len(backup_set.files))
            )
        
        self.console.print(table)
        
        try:
            choice = Prompt.ask(f"Select backup (1-{len(backup_sets)})")
            idx = int(choice) - 1
            if 0 <= idx < len(backup_sets):
                return backup_sets[idx]
        except (ValueError, IndexError):
            pass
        
        self.print_error("Invalid selection")
        return None
    
    def get_backup_type(self) -> str:
        """Get backup type from user."""
        self.console.print("\n[bold]Backup Types:[/bold]")
        self.console.print("1. Complete (database + files)")
        self.console.print("2. Database only")
        self.console.print("3. Files only")
        
        choice = Prompt.ask("Select backup type", choices=["1", "2", "3"], default="1")
        
        type_map = {"1": "complete", "2": "database", "3": "files"}
        return type_map[choice]
    
    def show_transfer_progress(self, transfer_progress: TransferProgress, title: str = "Transfer Progress"):
        """Show transfer progress with live updates."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self.console,
        ) as progress:
            
            task = progress.add_task(title, total=transfer_progress.total_size)
            
            while not progress.finished:
                progress.update(
                    task, 
                    completed=transfer_progress.transferred,
                    description=f"Speed: {transfer_progress.speed_mbps:.1f} MB/s"
                )
                
                if transfer_progress.cancelled.is_set():
                    break
                    
                time.sleep(0.1)
    
    def get_restore_config(self, backup_set) -> Dict[str, Any]:
        """Get restore configuration from user."""
        self.console.print(f"\n[bold]Configuring restore for backup set:[/bold] {backup_set.timestamp}-{backup_set.site_name}")
        
        target_bench = Prompt.ask("Target bench path", default="~/frappe-bench")
        
        # Ask if they want to create a new site or restore to existing
        create_new = Confirm.ask("Create new site?", default=True)
        
        if create_new:
            target_site = Prompt.ask("New site name", default=backup_set.site_name)
        else:
            # TODO: In future, we could list existing sites from the bench
            target_site = Prompt.ask("Existing site name to restore to", default=backup_set.site_name)
        
        # Database credentials for restoration
        mariadb_user = Prompt.ask("MariaDB root username", default="root")
        mariadb_pass = Prompt.ask("MariaDB root password", password=True, default="")
        
        return {
            "target_bench_path": target_bench,
            "target_site_name": target_site,
            "mariadb_root_username": mariadb_user,
            "mariadb_root_password": mariadb_pass,
            "create_new_site": create_new,
            "force_restore": True
        }
    
    def show_operation_status(self, operation: str, status: str, details: Optional[str] = None):
        """Show operation status."""
        color = "green" if status == "success" else "red" if status == "error" else "yellow"
        
        panel_content = f"[bold]{operation}[/bold]\nStatus: [{color}]{status.upper()}[/{color}]"
        if details:
            panel_content += f"\n{details}"
        
        self.console.print(Panel(panel_content, style=color))
    
    def confirm_action(self, message: str, default: bool = False) -> bool:
        """Get confirmation from user."""
        return Confirm.ask(message, default=default)
    
    def get_input(self, prompt: str, default: str = "") -> str:
        """Get text input from user."""
        return Prompt.ask(prompt, default=default) if default else Prompt.ask(prompt)
    
    def wait_for_keypress(self, message: str = "Press any key to continue..."):
        """Wait for user keypress."""
        self.console.print(f"\n[dim]{message}[/dim]")
        input()
    
    def clear_screen(self):
        """Clear the console screen."""
        self.console.clear()
    
    def display_table(self, title: str, headers: List[str], rows: List[List[str]], 
                     styles: Optional[List[str]] = None):
        """Display a generic table."""
        table = Table(title=title)
        
        for i, header in enumerate(headers):
            style = styles[i] if styles and i < len(styles) else None
            table.add_column(header, style=style)
        
        for row in rows:
            table.add_row(*row)
        
        self.console.print(table)
    
    def show_spinner(self, message: str, task_func: Callable) -> Any:
        """Show spinner while executing a task."""
        with self.console.status(message):
            return task_func()
    
    def create_progress_callback(self, description: str = "Processing") -> Callable:
        """Create a progress callback for operations."""
        progress = Progress(console=self.console)
        task = progress.add_task(description, total=100)
        progress.start()
        
        def callback(current: int, total: int):
            percentage = (current / total) * 100 if total > 0 else 0
            progress.update(task, completed=percentage)
        
        return callback