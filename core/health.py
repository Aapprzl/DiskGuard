import psutil
import threading
import subprocess
import json
import os

_wmi_available = None
_smartctl_path = r"C:\Program Files\smartmontools\bin\smartctl.exe"


def _check_wmi():
    global _wmi_available
    if _wmi_available is None:
        try:
            import wmi
            c = wmi.WMI()
            list(c.Win32_DiskDrive())
            _wmi_available = True
        except Exception:
            _wmi_available = False
    return _wmi_available


def _get_drive_to_physical_map():
    import time
    for attempt in range(3):
        try:
            import wmi
            drive_map = {}
            c = wmi.WMI()
            for physical in c.Win32_DiskDrive():
                pd_index = physical.Index
                for partition in physical.associators("Win32_DiskDriveToDiskPartition"):
                    for logical in partition.associators("Win32_LogicalDiskToPartition"):
                        drive_letter = logical.DeviceID
                        drive_map[drive_letter] = f"pd{pd_index}"
            if drive_map:
                return drive_map
            if attempt < 2:
                time.sleep(0.5)
        except:
            if attempt < 2:
                time.sleep(0.5)
    return {}


def _get_smartctl_data(drive_letter):
    try:
        if not os.path.exists(_smartctl_path):
            return None
        
        drive_map = _get_drive_to_physical_map()
        device = drive_map.get(drive_letter)
        
        if not device:
            return None
        
        result = subprocess.run(
            [_smartctl_path, "-j", "-a", device],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode != 0:
            return None
        
        data = json.loads(result.stdout)
        
        if "nvme_smart_health_information_log" in data:
            nvme = data["nvme_smart_health_information_log"]
            
            temp = nvme.get("temperature")
            if isinstance(temp, dict):
                temp = temp.get("current", temp.get("temperature"))
            
            return {
                "temperature": temp if temp else "N/A",
                "power_on_hours": nvme.get("power_on_hours", "N/A"),
                "media_errors": nvme.get("media_errors", 0),
                "available_spare": nvme.get("available_spare", 100),
                "percentage_used": nvme.get("percentage_used", 0),
                "power_cycles": nvme.get("power_cycles", 0),
                "unsafe_shutdowns": nvme.get("unsafe_shutdowns", 0),
                "source": "smartctl"
            }
        
        if "ata_smart_attributes" in data:
            ata = data["ata_smart_attributes"]
            table = ata.get("table", [])
            
            reallocated = None
            power_on_hours = None
            
            for attr in table:
                attr_id = attr.get("id")
                raw = attr.get("raw", {}).get("string", "0")
                try:
                    raw_val = int(raw.split()[0]) if raw else 0
                except:
                    raw_val = 0
                    
                if attr_id == 5:
                    reallocated = raw_val
                elif attr_id == 9:
                    power_on_hours = raw_val
            
            return {
                "temperature": "N/A",
                "power_on_hours": power_on_hours if power_on_hours else "N/A",
                "reallocated_sectors": reallocated if reallocated else 0,
                "source": "smartctl"
            }
        
        return None
        
    except Exception:
        return None


def _detect_disk_type(model_name, drive_letter):
    model_upper = model_name.upper()
    
    if "NVME" in model_upper:
        return "NVMe SSD"
    if "SSD" in model_upper:
        return "SSD"
    
    try:
        drive_map = _get_drive_to_physical_map()
        device = drive_map.get(drive_letter)
        
        if device and os.path.exists(_smartctl_path):
            result = subprocess.run(
                [_smartctl_path, "-j", "-a", device],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                
                if "nvme_smart_health_information_log" in data:
                    return "NVMe SSD"
                
                rotation_rate = data.get("rotation_rate", 1)
                if rotation_rate == 0:
                    return "SSD"
                
                if data.get("solid_state_device"):
                    return "SSD"
                
                if rotation_rate > 0:
                    return "HDD"
    except:
        pass
    
    return "Unknown"


def get_all_disks():
    disks = []
    try:
        if _check_wmi():
            import wmi
            c = wmi.WMI()
            for physical in c.Win32_DiskDrive():
                for partition in physical.associators("Win32_DiskDriveToDiskPartition"):
                    for logical in partition.associators("Win32_LogicalDiskToPartition"):
                        drive_letter = logical.DeviceID
                        disk_type = _detect_disk_type(physical.Model, drive_letter)
                        disks.append({
                            "drive_letter": drive_letter,
                            "name": physical.Model,
                            "type": disk_type,
                            "size_gb": round(int(physical.Size) / (1024**3), 1) if physical.Size else 0,
                            "physical_drive": f"pd{physical.Index}"
                        })
        else:
            partitions = psutil.disk_partitions()
            for p in partitions:
                if p.device:
                    disks.append({
                        "drive_letter": p.device,
                        "name": p.device,
                        "type": "Unknown",
                        "size_gb": 0
                    })
    except Exception:
        partitions = psutil.disk_partitions()
        for p in partitions:
            if p.device:
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    disks.append({
                        "drive_letter": p.device,
                        "name": p.mountpoint if p.mountpoint else p.device,
                        "type": "Unknown",
                        "size_gb": round(usage.total / (1024**3), 1)
                    })
                except:
                    disks.append({
                        "drive_letter": p.device,
                        "name": p.device,
                        "type": "Unknown",
                        "size_gb": 0
                    })
    return disks


def get_smart_data(drive_letter):
    result = {
        "status": "Unknown",
        "temperature": "N/A",
        "bad_sectors": 0,
        "reallocated_sectors": 0,
        "power_on_hours": "N/A",
        "health_percent": 0,
        "source": "N/A",
        "message": None
    }
    
    smartctl_data = _get_smartctl_data(drive_letter)
    
    if smartctl_data:
        result["temperature"] = smartctl_data.get("temperature", "N/A")
        result["power_on_hours"] = smartctl_data.get("power_on_hours", "N/A")
        result["reallocated_sectors"] = smartctl_data.get("media_errors", 0) or smartctl_data.get("reallocated_sectors", 0)
        result["source"] = "smartctl"
        
        if smartctl_data.get("media_errors", 0) == 0 and smartctl_data.get("available_spare", 100) > 50:
            result["status"] = "Good"
            result["health_percent"] = 100 - (smartctl_data.get("percentage_used", 0) or 0)
        elif smartctl_data.get("media_errors", 0) > 0:
            result["status"] = "Warning"
            result["health_percent"] = 80
        else:
            result["status"] = "Good"
            result["health_percent"] = 95
        
        return result
    
    wmi_has_data = False
    
    try:
        if not _check_wmi():
            pass
        else:
            import wmi
            c = wmi.WMI()
            for disk in c.Win32_DiskDrive():
                for partition in disk.associators("Win32_DiskDriveToDiskPartition"):
                    for logical in partition.associators("Win32_LogicalDiskToPartition"):
                        if logical.DeviceID == drive_letter:
                            try:
                                device_id = disk.DeviceID.replace("\\", "\\\\")
                                smart_data = c.query(
                                    f"SELECT * FROM Win32_DiskDrive WHERE DeviceID = '{device_id}'"
                                )[0]
                                
                                temp = getattr(smart_data, "DriveTemperature", None)
                                if temp:
                                    result["temperature"] = temp
                                    wmi_has_data = True
                                
                                bad_sectors = getattr(smart_data, "TotalBadSectors", None)
                                if bad_sectors:
                                    result["bad_sectors"] = bad_sectors
                                    wmi_has_data = True
                                
                                reallocated = getattr(smart_data, "ReallocatedSectorsCount", None)
                                if reallocated:
                                    result["reallocated_sectors"] = reallocated
                                    wmi_has_data = True
                                
                                power_hours = getattr(smart_data, "PowerOnHours", None)
                                if power_hours:
                                    result["power_on_hours"] = power_hours
                                    wmi_has_data = True
                                
                                health_status = getattr(smart_data, "HealthStatus", None)
                                if health_status == 1:
                                    result["status"] = "Good"
                                    result["health_percent"] = 100
                                elif health_status == 2:
                                    result["status"] = "Warning"
                                    result["health_percent"] = 60
                                elif health_status == 3:
                                    result["status"] = "Critical"
                                    result["health_percent"] = 20
                                else:
                                    result["status"] = "Good"
                                    result["health_percent"] = 95
                                    
                                if wmi_has_data:
                                    result["source"] = "WMI"
                                    
                            except Exception:
                                pass
                            break
    except Exception:
        pass
    
    if not wmi_has_data and not smartctl_data:
        result["status"] = "Good"
        result["health_percent"] = 95
        result["source"] = "unavailable"
        result["message"] = "SMART data tidak tersedia. Jalankan sebagai Administrator untuk data lengkap."
    
    return result


def get_disk_usage(drive_letter):
    try:
        usage = psutil.disk_usage(drive_letter)
        return {
            "total_gb": round(usage.total / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
            "percent": usage.percent
        }
    except PermissionError:
        return {"total_gb": 0, "used_gb": 0, "free_gb": 0, "percent": 0, "error": "Access denied"}
    except Exception:
        return {"total_gb": 0, "used_gb": 0, "free_gb": 0, "percent": 0, "error": "Drive not available"}


def scan_disk_async(drive_letter, callback):
    def _scan():
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except:
            pass
        
        try:
            smart_data = get_smart_data(drive_letter)
            usage_data = get_disk_usage(drive_letter)
            result = {**smart_data, **usage_data}
            callback(result)
        except Exception as e:
            callback({"error": str(e)})
        finally:
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except:
                pass
    
    thread = threading.Thread(target=_scan, daemon=True)
    thread.start()
