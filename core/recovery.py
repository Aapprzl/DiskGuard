import os
import threading
import time


class DataRecovery:
    CHUNK_SIZE = 1024 * 1024
    FILE_TIMEOUT = 30
    CHUNK_TIMEOUT = 5
    
    def __init__(self, source_drive, output_folder, callback=None):
        self.source_drive = source_drive.rstrip("\\").rstrip("/") + "\\"
        self.output_folder = output_folder
        self.callback = callback or (lambda *args: None)
        
        self._scan_thread = None
        self._rescue_thread = None
        self._cancel_event = threading.Event()
        
        self.scanned_files = []
        self.total_found = 0
        self.rescued_ok = 0
        self.rescued_partial = 0
        self.failed = 0
        self.failed_list = []
        
        self._progress = 0
        self._current_file = ""
        self._status = "idle"
    
    def scan_files(self, extensions=None):
        self.scanned_files = []
        self.total_found = 0
        self._status = "scanning"
        self._progress = 0
        self._cancel_event.clear()
        
        self._scan_thread = threading.Thread(target=self._scan_worker, args=(extensions,), daemon=True)
        self._scan_thread.start()
    
    def _scan_worker(self, extensions):
        try:
            self.callback(0, "", "Scanning drive...", "scanning")
            
            for root, dirs, files in os.walk(self.source_drive):
                if self._cancel_event.is_set():
                    break
                
                for filename in files:
                    if self._cancel_event.is_set():
                        break
                    
                    try:
                        filepath = os.path.join(root, filename)
                        _, ext = os.path.splitext(filename)
                        ext = ext.lower()
                        
                        if extensions and extensions != [None]:
                            if ext not in extensions:
                                continue
                        
                        try:
                            size = os.path.getsize(filepath)
                            readable = True
                            error = None
                        except (OSError, PermissionError) as e:
                            size = 0
                            readable = False
                            error = str(e)
                        
                        file_info = {
                            "path": filepath,
                            "name": filename,
                            "size": size,
                            "readable": readable,
                            "error": error
                        }
                        
                        self.scanned_files.append(file_info)
                        self.total_found += 1
                        
                        if self.total_found % 100 == 0:
                            self.callback(0, "", f"Found {self.total_found} files...", "scanning")
                        
                    except Exception:
                        continue
            
            self._status = "scan_complete"
            self.callback(100, "", f"Scan complete: {self.total_found} files found", "scan_complete")
            
        except Exception as e:
            self._status = "error"
            self.callback(0, "", f"Error: {str(e)}", "error")
    
    def rescue_files(self, file_list, skip_errors=True):
        print(f"[RESCUE] Starting rescue of {len(file_list) if file_list else 0} files to {self.output_folder}")
        print(f"[RESCUE] FILE_TIMEOUT={self.FILE_TIMEOUT}s, CHUNK_TIMEOUT={self.CHUNK_TIMEOUT}s")
        
        self._cancel_event.clear()
        self._status = "rescuing"
        self._progress = 0
        self.rescued_ok = 0
        self.rescued_partial = 0
        self.failed = 0
        self.failed_list = []
        
        self._rescue_thread = threading.Thread(
            target=self._rescue_worker, args=(file_list, skip_errors), daemon=True
        )
        self._rescue_thread.start()
    
    def _rescue_worker(self, file_list, skip_errors):
        total_files = len(file_list)
        processed = 0
        
        try:
            os.makedirs(self.output_folder, exist_ok=True)
        except Exception as e:
            self.callback(0, "", f"Cannot create output folder: {e}", "error")
            return
        
        for i, file_info in enumerate(file_list):
            if self._cancel_event.is_set():
                break
            
            src_path = file_info["path"]
            filename = file_info["name"]
            
            self._current_file = filename
            progress = (i / total_files) * 100
            self.callback(progress, filename, f"Processing {i+1}/{total_files}", "rescuing")
            
            try:
                result = self._rescue_single_file(src_path, filename, skip_errors)
            except Exception as e:
                print(f"Error processing {filename}: {e}")
                result = "failed"
                self.failed_list.append({"file": filename, "error": str(e)})
            
            if result == "ok":
                self.rescued_ok += 1
                self.callback(0, filename, f"[OK] {filename}", "file_ok")
            elif result == "partial":
                self.rescued_partial += 1
                error_info = self.failed_list[-1]["error"] if self.failed_list else "bad sector detected"
                self.callback(0, filename, f"[PARTIAL] {filename} — {error_info}", "file_partial")
            elif result == "failed":
                self.failed += 1
                error_info = self.failed_list[-1]["error"] if self.failed_list else "unknown error"
                self.callback(0, filename, f"[FAILED] {filename} — {error_info}", "file_failed")
            else:
                self.failed += 1
                self.callback(0, filename, f"[FAILED] {filename} — unknown result", "file_failed")
            
            processed += 1
            final_progress = (processed / total_files) * 100
            self.callback(final_progress, filename, f"Processed {processed}/{total_files}", "rescuing")
            
            time.sleep(0.01)
        
        self._status = "rescue_complete"
        self.callback(100, "", f"Complete: {self.rescued_ok} ok, {self.rescued_partial} partial, {self.failed} failed", "complete")
    
    def _rescue_single_file(self, src_path, filename, skip_errors):
        dst_path = os.path.join(self.output_folder, filename)
        if os.path.exists(dst_path):
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(dst_path):
                dst_path = os.path.join(self.output_folder, f"{base}_{counter}{ext}")
                counter += 1

        result_container = {"result": "failed", "error": None}

        def do_rescue():
            chunks_with_error = 0
            try:
                src_size = os.path.getsize(src_path)
                with open(src_path, 'rb') as fsrc, open(dst_path, 'wb') as fdst:
                    while True:
                        if self._cancel_event.is_set():
                            result_container["result"] = "failed"
                            return
                        try:
                            chunk = fsrc.read(self.CHUNK_SIZE)
                        except Exception:
                            chunk = b'\x00' * self.CHUNK_SIZE
                            chunks_with_error += 1
                        if not chunk:
                            break
                        fdst.write(chunk)
                if chunks_with_error > 0:
                    result_container["result"] = "partial"
                    self.failed_list.append({"file": filename, "error": f"{chunks_with_error} chunks unreadable"})
                else:
                    result_container["result"] = "ok"
            except Exception as e:
                result_container["result"] = "failed"
                result_container["error"] = str(e)
                self.failed_list.append({"file": filename, "error": str(e)})

        t = threading.Thread(target=do_rescue, daemon=True)
        t.start()
        t.join(timeout=self.FILE_TIMEOUT)

        if t.is_alive():
            print(f"FILE TIMEOUT for {filename} — skipping")
            self.failed_list.append({"file": filename, "error": "file timeout — bad sector"})
            result_container["result"] = "partial"
            if not os.path.exists(dst_path):
                open(dst_path, 'wb').close()

        return result_container["result"]
    
    def cancel(self):
        self._cancel_event.set()
        self._status = "cancelled"
        self.callback(0, "", "Cancelled", "cancelled")
    
    def get_rescue_report(self):
        return {
            "total_found": self.total_found,
            "rescued_ok": self.rescued_ok,
            "rescued_partial": self.rescued_partial,
            "failed": self.failed,
            "failed_list": self.failed_list,
            "output_folder": self.output_folder
        }
    
    def wait_for_scan(self):
        if self._scan_thread:
            self._scan_thread.join()
    
    def wait_for_rescue(self):
        if self._rescue_thread:
            self._rescue_thread.join()
