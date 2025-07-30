import tkinter as tk
from tkinter import ttk
import psutil
import threading
import time
import keyboard
import sys
from datetime import datetime

class SystemMonitor:
    def __init__(self, root):
        self.root = root
        self.popup_window = None
        self.is_popup_visible = False
        self.monitoring = True
        
        # System info storage
        self.cpu_percent = 0
        self.cpu_temp = "N/A"
        self.gpu_temp = "N/A"
        self.gpu_usage = "N/A"
        self.memory_percent = 0
        
        # Setup hotkey monitoring in a separate thread
        self.setup_hotkey_monitoring()
        
        # Start system monitoring
        self.update_system_info()
        
        print("System Monitor started!")
        print("Press Ctrl+Shift+M to show/hide system info")
        print("Press Ctrl+C in this window or close it to exit")
        
    def setup_hotkey_monitoring(self):
        """Setup hotkey monitoring in a separate thread"""
        def hotkey_thread():
            try:
                keyboard.add_hotkey('ctrl+shift+m', self.toggle_popup)
                keyboard.wait()  # Keep the thread alive
            except Exception as e:
                print(f"Hotkey error: {e}")
        
        self.hotkey_thread = threading.Thread(target=hotkey_thread, daemon=True)
        self.hotkey_thread.start()
    
    def get_cpu_temperature(self):
        """Get CPU temperature - works on Windows with some hardware"""
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    for entry in entries:
                        if 'cpu' in name.lower() or 'core' in name.lower():
                            return f"{entry.current:.1f}°C"
            return "N/A"
        except:
            return "N/A"
    
    def get_gpu_info(self):
        """Get GPU information using WMI and nvidia-ml-py"""
        try:
            import subprocess
            import json
            
            # Try nvidia-smi first (most reliable for NVIDIA GPUs)
            try:
                result = subprocess.run([
                    'nvidia-smi', 
                    '--query-gpu=utilization.gpu,temperature.gpu', 
                    '--format=csv,noheader,nounits'
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if lines and lines[0]:
                        values = lines[0].split(', ')
                        if len(values) >= 2:
                            usage = f"{values[0].strip()}%"
                            temp = f"{values[1].strip()}°C"
                            return temp, usage
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
                pass
            
            # Fallback: Try WMI for basic GPU info
            try:
                import wmi
                c = wmi.WMI(namespace="root/OpenHardwareMonitor")
                
                gpu_temp = "N/A"
                gpu_usage = "N/A"
                
                for sensor in c.Sensor():
                    if 'gpu' in sensor.Name.lower():
                        if 'temperature' in sensor.SensorType.lower():
                            gpu_temp = f"{sensor.Value:.0f}°C"
                        elif 'load' in sensor.SensorType.lower():
                            gpu_usage = f"{sensor.Value:.0f}%"
                
                return gpu_temp, gpu_usage
            except:
                pass
            
            # Final fallback: Try getting GPU usage from performance counters
            try:
                result = subprocess.run([
                    'powershell', 
                    '-Command', 
                    '(Get-Counter "\\GPU Engine(*)\\Utilization Percentage").CounterSamples | Select-Object -First 1 | Select-Object -ExpandProperty CookedValue'
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0 and result.stdout.strip():
                    usage_value = float(result.stdout.strip())
                    return "N/A", f"{usage_value:.1f}%"
            except:
                pass
                
            return "N/A", "N/A"
            
        except Exception as e:
            print(f"GPU info error: {e}")
            return "N/A", "N/A"
    
    def update_system_info(self):
        """Update system information - called by tkinter's main loop"""
        try:
            # Get CPU info
            self.cpu_percent = psutil.cpu_percent(interval=None)
            self.cpu_temp = self.get_cpu_temperature()
            
            # Get Memory info
            memory = psutil.virtual_memory()
            self.memory_percent = memory.percent
            
            # Get GPU info (basic)
            self.gpu_temp, self.gpu_usage = self.get_gpu_info()
            
            # Update popup if visible
            if self.is_popup_visible and self.popup_window:
                self.update_popup_content()
                
        except Exception as e:
            print(f"Monitoring error: {e}")
        
        # Schedule next update (every 2 seconds)
        if self.monitoring:
            self.root.after(2000, self.update_system_info)
    
    def create_popup(self):
        """Create the popup window"""
        if self.popup_window:
            return
            
        self.popup_window = tk.Toplevel(self.root)
        self.popup_window.title("System Monitor")
        self.popup_window.configure(bg='#2b2b2b')
        
        # Make window stay on top
        self.popup_window.attributes('-topmost', True)
        
        # Remove window decorations for cleaner look
        self.popup_window.overrideredirect(True)
        
        # Position window at top-right corner with better sizing
        screen_width = self.popup_window.winfo_screenwidth()
        screen_height = self.popup_window.winfo_screenheight()
        
        # Make window bigger to fit all content
        window_width = 320
        window_height = 300
        
        # Position it properly away from edges
        x_pos = screen_width - window_width - 20
        y_pos = 50
        
        self.popup_window.geometry(f"{window_width}x{window_height}+{x_pos}+{y_pos}")
        
        # Create main frame with more padding
        main_frame = tk.Frame(self.popup_window, bg='#2b2b2b', padx=20, pady=15)
        main_frame.pack(fill='both', expand=True)
        
        # Title
        title_label = tk.Label(main_frame, text="System Monitor", 
                              font=('Arial', 14, 'bold'), 
                              fg='#ffffff', bg='#2b2b2b')
        title_label.pack(pady=(0, 15))
        
        # CPU Section
        cpu_frame = tk.Frame(main_frame, bg='#2b2b2b')
        cpu_frame.pack(fill='x', pady=8)
        
        tk.Label(cpu_frame, text="CPU:", font=('Arial', 10, 'bold'), 
                fg='#4CAF50', bg='#2b2b2b').pack(anchor='w')
        
        self.cpu_usage_label = tk.Label(cpu_frame, text="Usage: 0%", 
                                       font=('Arial', 9), 
                                       fg='#ffffff', bg='#2b2b2b')
        self.cpu_usage_label.pack(anchor='w', padx=(15, 0))
        
        self.cpu_temp_label = tk.Label(cpu_frame, text="Temp: N/A", 
                                      font=('Arial', 9), 
                                      fg='#ffffff', bg='#2b2b2b')
        self.cpu_temp_label.pack(anchor='w', padx=(15, 0))
        
        # Memory Section
        mem_frame = tk.Frame(main_frame, bg='#2b2b2b')
        mem_frame.pack(fill='x', pady=8)
        
        tk.Label(mem_frame, text="Memory:", font=('Arial', 10, 'bold'), 
                fg='#2196F3', bg='#2b2b2b').pack(anchor='w')
        
        self.memory_label = tk.Label(mem_frame, text="Usage: 0%", 
                                    font=('Arial', 9), 
                                    fg='#ffffff', bg='#2b2b2b')
        self.memory_label.pack(anchor='w', padx=(15, 0))
        
        # GPU Section
        gpu_frame = tk.Frame(main_frame, bg='#2b2b2b')
        gpu_frame.pack(fill='x', pady=8)
        
        tk.Label(gpu_frame, text="GPU:", font=('Arial', 10, 'bold'), 
                fg='#FF9800', bg='#2b2b2b').pack(anchor='w')
        
        self.gpu_usage_label = tk.Label(gpu_frame, text="Usage: N/A", 
                                       font=('Arial', 9), 
                                       fg='#ffffff', bg='#2b2b2b')
        self.gpu_usage_label.pack(anchor='w', padx=(15, 0))
        
        self.gpu_temp_label = tk.Label(gpu_frame, text="Temp: N/A", 
                                      font=('Arial', 9), 
                                      fg='#ffffff', bg='#2b2b2b')
        self.gpu_temp_label.pack(anchor='w', padx=(15, 0))
        
        # Timestamp
        self.timestamp_label = tk.Label(main_frame, text="", 
                                       font=('Arial', 8), 
                                       fg='#888888', bg='#2b2b2b')
        self.timestamp_label.pack(pady=(15, 5))
        
        # Close button
        close_btn = tk.Button(main_frame, text="Close (Ctrl+Shift+M)", 
                             command=self.hide_popup,
                             bg='#f44336', fg='white', 
                             font=('Arial', 8),
                             padx=10, pady=5)
        close_btn.pack(pady=(5, 0))
        
        # Update content immediately
        self.update_popup_content()
        
        # Handle window close
        self.popup_window.protocol("WM_DELETE_WINDOW", self.hide_popup)
    
    def update_popup_content(self):
        """Update the popup window content with current data"""
        if not self.popup_window or not self.is_popup_visible:
            return
            
        try:
            # Update CPU info
            self.cpu_usage_label.config(text=f"Usage: {self.cpu_percent:.1f}%")
            self.cpu_temp_label.config(text=f"Temp: {self.cpu_temp}")
            
            # Update Memory info
            self.memory_label.config(text=f"Usage: {self.memory_percent:.1f}%")
            
            # Update GPU info
            self.gpu_usage_label.config(text=f"Usage: {self.gpu_usage}")
            self.gpu_temp_label.config(text=f"Temp: {self.gpu_temp}")
            
            # Update timestamp
            current_time = datetime.now().strftime("%H:%M:%S")
            self.timestamp_label.config(text=f"Updated: {current_time}")
            
        except Exception as e:
            print(f"Error updating popup: {e}")
    
    def show_popup(self):
        """Show the popup window"""
        if not self.is_popup_visible:
            self.create_popup()
            self.is_popup_visible = True
    
    def hide_popup(self):
        """Hide the popup window"""
        if self.is_popup_visible and self.popup_window:
            self.popup_window.destroy()
            self.popup_window = None
            self.is_popup_visible = False
    
    def toggle_popup(self):
        """Toggle popup visibility - called from hotkey thread"""
        # Schedule the toggle to run in the main thread
        self.root.after(0, self._toggle_popup_main_thread)
    
    def _toggle_popup_main_thread(self):
        """Toggle popup visibility in main thread"""
        if self.is_popup_visible:
            self.hide_popup()
        else:
            self.show_popup()
    
    def shutdown(self):
        """Clean shutdown"""
        self.monitoring = False
        self.hide_popup()
        try:
            keyboard.unhook_all()
        except:
            pass
        self.root.quit()

def main():
    """Main function"""
    # Create root window (hidden)
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    root.title("System Monitor (Hidden)")
    
    # Create system monitor
    monitor = SystemMonitor(root)
    
    # Handle window close event
    def on_closing():
        monitor.shutdown()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    try:
        # Start the tkinter main loop
        root.mainloop()
    except KeyboardInterrupt:
        print("\nShutting down...")
        monitor.shutdown()

if __name__ == "__main__":
    main()