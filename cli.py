"""Main CLI entry point for FrappeBR."""

import sys
import traceback
from pathlib import Path
from typing import Optional

from .ui.console import ConsoleUI
from .core.ssh_manager import SSHManager, SSHConnectionError
from .core.site_manager import SiteManager, SiteDiscoveryError
from .core.backup_manager import BackupManager, BackupError
from .core.transfer_manager import TransferManager, TransferError
from .core.restore_manager import RestoreManager, RestoreError
from .models.config import RestoreConfig, BackupInfo, BackupSet


class FrappeBRApp:
    """Main FrappeBR application."""
    
    def __init__(self):
        self.ui = ConsoleUI()
        self.ssh_manager = SSHManager()
        self.site_manager = SiteManager(self.ssh_manager)
        self.backup_manager = BackupManager(self.ssh_manager)
        self.transfer_manager = TransferManager(self.ssh_manager)
        self.restore_manager = RestoreManager()
        
        self.current_hostname: Optional[str] = None
        self.current_bench_path: Optional[str] = None
        self.current_site: Optional[str] = None
    
    def run(self):
        """Run the main application loop."""
        try:
            self.ui.clear_screen()
            self.ui.print_header()
            
            while True:
                try:
                    choice = self.ui.show_main_menu()
                    
                    if choice == "1":
                        self.handle_remote_connection()
                    elif choice == "2":
                        self.handle_local_backups()
                    elif choice == "3":
                        self.handle_restore()
                    elif choice == "4":
                        self.handle_settings()
                    elif choice == "5":
                        self.handle_history()
                    elif choice == "6":
                        self.ui.print_info("Goodbye!")
                        break
                    
                except KeyboardInterrupt:
                    self.ui.print_info("\nOperation cancelled by user")
                    continue
                except Exception as e:
                    self.ui.print_error(f"Unexpected error: {e}")
                    if "--debug" in sys.argv:
                        traceback.print_exc()
                    continue
        
        finally:
            self.cleanup()
    
    def handle_remote_connection(self):
        """Handle remote host connection and operations."""
        try:
            # Get SSH hosts
            hosts = self.ssh_manager.list_hosts()
            selected_host = self.ui.select_ssh_host(hosts)
            
            if not selected_host:
                return
            
            # Test connection
            self.ui.print_info(f"Connecting to {selected_host.hostname}...")
            success = self.ssh_manager.test_connection(selected_host.hostname, selected_host)
            self.ui.show_connection_status(selected_host.hostname, success)
            
            if not success:
                return
            
            self.current_hostname = selected_host.hostname
            
            # Find frappe benches
            self.ui.print_info("Searching for frappe-bench directories...")
            bench_paths = self.site_manager.find_frappe_benches(self.current_hostname)
            
            selected_bench = self.ui.select_frappe_bench(bench_paths)
            if not selected_bench:
                return
            
            self.current_bench_path = selected_bench
            
            # List sites
            self.ui.print_info("Loading sites...")
            sites = self.site_manager.list_sites(self.current_hostname, self.current_bench_path)
            
            selected_site = self.ui.display_sites(sites)
            if not selected_site:
                return
            
            self.current_site = selected_site.name
            
            # Show backup menu for selected site
            self.handle_remote_backup_operations(selected_site)
        
        except SSHConnectionError as e:
            self.ui.print_error(f"SSH connection failed: {e}")
        except SiteDiscoveryError as e:
            self.ui.print_error(f"Site discovery failed: {e}")
        except Exception as e:
            self.ui.print_error(f"Remote connection error: {e}")
    
    def handle_remote_backup_operations(self, site_info):
        """Handle backup operations for selected site."""
        while True:
            choice = self.ui.show_backup_menu()
            
            if choice == "1":
                self.list_remote_backups(site_info)
            elif choice == "2":
                self.create_remote_backup(site_info)
            elif choice == "3":
                self.download_backup(site_info)
            elif choice == "4":
                break
    
    def list_remote_backups(self, site_info):
        """List backups for remote site."""
        try:
            self.ui.print_info("Loading backups...")
            backup_sets = self.backup_manager.list_backup_sets(
                self.current_hostname, 
                self.current_bench_path, 
                site_info.name
            )
            
            if backup_sets:
                self.ui.display_backup_sets(backup_sets)
            else:
                self.ui.print_warning("No backups found for this site")
            
            self.ui.wait_for_keypress()
        
        except BackupError as e:
            self.ui.print_error(f"Failed to list backups: {e}")
    
    def create_remote_backup(self, site_info):
        """Create new backup for remote site."""
        try:
            backup_type = self.ui.get_backup_type()
            
            self.ui.print_info(f"Creating {backup_type} backup for {site_info.name}...")
            
            backup_info = self.backup_manager.create_backup(
                self.current_hostname,
                self.current_bench_path,
                site_info.name,
                backup_type
            )
            
            if backup_info:
                self.ui.print_success(f"Backup created: {backup_info.filename}")
                
                # Ask if user wants to download it
                if self.ui.confirm_action("Download backup now?"):
                    self.download_specific_backup(backup_info)
            else:
                self.ui.print_success("Backup created successfully! Check the backup list to see it.")
        
        except BackupError as e:
            self.ui.print_error(f"Backup creation failed: {e}")
    
    def download_backup(self, site_info):
        """Download existing backup."""
        try:
            backup_sets = self.backup_manager.list_backup_sets(
                self.current_hostname, 
                self.current_bench_path, 
                site_info.name
            )
            
            if not backup_sets:
                self.ui.print_warning("No backups available for download")
                return
            
            selected_backup_set = self.ui.display_backup_sets(backup_sets)
            if selected_backup_set:
                self.download_backup_set(selected_backup_set)
        
        except BackupError as e:
            self.ui.print_error(f"Failed to download backup: {e}")
    
    def download_specific_backup(self, backup_info: BackupInfo):
        """Download a specific backup with progress tracking."""
        try:
            def progress_callback(progress):
                # This would be called by the transfer manager
                # For now, we'll use a simple progress display
                pass
            
            # Check if this is part of a complete backup set
            backup_set = self.backup_manager.get_backup_set_files(
                self.current_hostname, backup_info
            )
            
            if len(backup_set) > 1:
                self.ui.print_info(f"Downloading complete backup set ({len(backup_set)} files)...")
                
                downloaded_files = []
                for backup_file in backup_set:
                    self.ui.print_info(f"Downloading {backup_file.filename}...")
                    
                    local_path = self.transfer_manager.download_backup(
                        self.current_hostname,
                        backup_file,
                        progress_callback=progress_callback
                    )
                    downloaded_files.append(local_path)
                
                self.ui.print_success(f"Downloaded {len(downloaded_files)} backup files:")
                for file_path in downloaded_files:
                    self.ui.print_info(f"  - {file_path}")
                
            else:
                # Single backup file
                self.ui.print_info(f"Downloading {backup_info.filename}...")
                
                local_path = self.transfer_manager.download_backup(
                    self.current_hostname,
                    backup_info,
                    progress_callback=progress_callback
                )
                
                self.ui.print_success(f"Downloaded to: {local_path}")
        
        except TransferError as e:
            self.ui.print_error(f"Download failed: {e}")
    
    def download_backup_set(self, backup_set: BackupSet):
        """Download all files in a backup set."""
        try:
            def progress_callback(progress):
                # This would be called by the transfer manager
                pass
            
            if len(backup_set.files) == 1:
                # Single file backup
                backup_file = backup_set.files[0]
                self.ui.print_info(f"Downloading {backup_file.filename}...")
                
                local_path = self.transfer_manager.download_backup(
                    self.current_hostname,
                    backup_file,
                    progress_callback=progress_callback
                )
                self.ui.print_success(f"Downloaded to: {local_path}")
            
            else:
                # Multi-file backup set
                self.ui.print_info(f"Downloading {backup_set.backup_type} backup set ({len(backup_set.files)} files)...")
                
                downloaded_files = []
                for backup_file in backup_set.files:
                    self.ui.print_info(f"Downloading {backup_file.filename}...")
                    
                    local_path = self.transfer_manager.download_backup(
                        self.current_hostname,
                        backup_file,
                        progress_callback=progress_callback
                    )
                    downloaded_files.append(local_path)
                
                self.ui.print_success(f"Downloaded {len(downloaded_files)} backup files:")
                for file_path in downloaded_files:
                    self.ui.print_info(f"  - {file_path}")
        
        except TransferError as e:
            self.ui.print_error(f"Download failed: {e}")
    
    def handle_local_backups(self):
        """Handle local backup management."""
        try:
            local_backup_sets = self.transfer_manager.get_local_backup_sets()
            
            if not local_backup_sets:
                self.ui.print_warning("No local backups found")
                return
            
            # Convert to list and sort by creation date (newest first)
            backup_sets_list = sorted(
                local_backup_sets.values(), 
                key=lambda x: x.created_at, 
                reverse=True
            )
            
            # Display backup sets
            self.ui.display_backup_sets(backup_sets_list)
            self.ui.wait_for_keypress()
        
        except Exception as e:
            self.ui.print_error(f"Failed to list local backups: {e}")
    
    def handle_restore(self):
        """Handle site restoration."""
        try:
            # Show local backup sets
            local_backup_sets = self.transfer_manager.get_local_backup_sets()
            
            if not local_backup_sets:
                self.ui.print_warning("No local backups available for restore")
                return
            
            # Convert to list and sort by creation date (newest first)
            backup_sets_list = sorted(
                local_backup_sets.values(), 
                key=lambda x: x.created_at, 
                reverse=True
            )
            
            # Let user select backup set
            if len(backup_sets_list) == 1:
                selected_backup_set = backup_sets_list[0]
                self.ui.print_info(f"Using backup set: {selected_backup_set.timestamp}")
            else:
                selected_backup_set = self.ui.display_backup_sets(backup_sets_list)
                if not selected_backup_set:
                    return
            
            # Get restore configuration
            restore_config_dict = self.ui.get_restore_config(selected_backup_set)
            
            restore_config = RestoreConfig(
                backup_set=selected_backup_set,
                **restore_config_dict
            )
            
            # Validate configuration
            valid, message = self.restore_manager.validate_restore_config(restore_config)
            if not valid:
                self.ui.print_error(f"Invalid configuration: {message}")
                return
            
            # Confirm restore
            if not self.ui.confirm_action(f"Restore backup set {selected_backup_set.timestamp} to {restore_config.target_site_name}?"):
                return
            
            # Perform restore using the backup set
            self.ui.print_info("Starting restore operation...")
            success = self.restore_manager.restore_site(restore_config)
            
            if success:
                self.ui.print_success("Restore completed successfully!")
                
                # Run post-restore tasks
                if self.ui.confirm_action("Run post-restore tasks (migrate, rebuild)?", default=True):
                    self.restore_manager.post_restore_tasks(
                        restore_config, 
                        Path(restore_config.target_bench_path)
                    )
            else:
                self.ui.print_error("Restore operation failed")
        
        except RestoreError as e:
            self.ui.print_error(f"Restore failed: {e}")
        except Exception as e:
            self.ui.print_error(f"Unexpected error during restore: {e}")
    
    def handle_settings(self):
        """Handle application settings."""
        self.ui.print_info("Settings configuration not yet implemented")
        self.ui.wait_for_keypress()
    
    def handle_history(self):
        """Handle operation history."""
        self.ui.print_info("Operation history not yet implemented")
        self.ui.wait_for_keypress()
    
    def cleanup(self):
        """Clean up resources."""
        self.ssh_manager.disconnect_all()


def main():
    """Main entry point."""
    app = FrappeBRApp()
    app.run()


if __name__ == "__main__":
    main()