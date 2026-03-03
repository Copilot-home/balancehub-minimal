import os
import json
import subprocess
import ast
from datetime import datetime
from pathlib import Path

class DriftDetector:
    """
    APΩ-Portal Drift Detector (v3.0) - MESH GUARDIAN
    Enforces 3-Layer Invariants & Anti-Lateral Drift Protocols.
    """
    
    MAX_REPO_SIZE_MB = 100
    MAX_FUNC_LIMIT = 50
    PULSE_THRESHOLD_HOURS = 24
    
    # Precise 20-App Taxonomy
    TAXONOMY = {
        "L1": ["autonomous_operator", "Notion", "Linear", "Gmail", "Telegram"],
        "L2": ["DAIOF-Framework", "balancehub", "Alpha", "andy", "hyperai_phoenix", "trust_of_copilot"],
        "L3": ["GDrive", "iCloud", "Supabase", "Firebase"]
    }
    
    def __init__(self, workspace="/Users/andy/balancehub"):
        self.workspace = workspace
        self.report = {
            "version": "3.0-MESH",
            "timestamp": datetime.now().isoformat(),
            "mesh_status": "LOCKED",
            "layers": {
                "L1_CONTROL": {"health": 1.0, "violations": []},
                "L2_PRODUCTION": {"health": 1.0, "violations": []},
                "L3_ARCHIVE": {"health": 1.0, "violations": []}
            },
            "overall_score": 100
        }

    def _get_func_count(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
                return len([node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))])
        except Exception:
            return 0

    def audit_l1_purity(self, path):
        """L1 must NOT have build artifacts, binaries, or excessive logic"""
        violations = []
        forbidden_exts = [".exe", ".bin", ".out", ".app", ".dmg"]
        forbidden_dirs = ["node_modules", "dist", "build", "target"]
        
        for root, dirs, files in os.walk(path):
            # Skip virtual environments
            if "venv" in root or ".venv" in root:
                continue
                
            # Check for forbidden directories
            for d in dirs:
                if d in forbidden_dirs:
                    violations.append(f"LATERAL DRIFT: L1 node contains production artifact directory '{d}'")
            
            # Check for binary artifacts
            for f in files:
                if any(f.endswith(ext) for ext in forbidden_exts):
                    violations.append(f"LATERAL DRIFT: L1 node contains forbidden binary '{f}'")
                    
        return violations

    def check_pulse(self):
        """Verifies if the system 'heartbeat' (logs) updated in last 24h"""
        pulse_file = "/Users/andy/my_too_test/logs/orchestrator.log"
        if not os.path.exists(pulse_file):
            return "PULSE FAILURE: No heartbeat log found."
        
        mtime = os.path.getmtime(pulse_file)
        hours_since_pulse = (datetime.now().timestamp() - mtime) / 3600
        if hours_since_pulse > self.PULSE_THRESHOLD_HOURS:
            return f"PULSE WEAK: Last heartbeat was {hours_since_pulse:.1f}h ago (Threshold: {self.PULSE_THRESHOLD_HOURS}h)."
        return None

    def run_mesh_audit(self):
        print(f"--- INITIALIZING MESH AUDIT v3.1 [{self.report['timestamp']}] ---")
        
        # 1. Production Layer Audit (L2)
        l2_issues = []
        # Size limit
        size_bytes = sum(f.stat().st_size for f in Path(self.workspace).rglob('*') if f.is_file() and ".git" not in str(f) and "venv" not in str(f) and ".venv" not in str(f))
        size_mb = size_bytes / (1024 * 1024)
        if size_mb > self.MAX_REPO_SIZE_MB:
            l2_issues.append(f"SIZE DRIFT: {size_mb:.1f}MB > {self.MAX_REPO_SIZE_MB}MB")
        
        # Function limit scan
        for root, _, files in os.walk(os.path.join(self.workspace, "app")):
            for f in files:
                if f.endswith(".py"):
                    count = self._get_func_count(os.path.join(root, f))
                    if count > self.MAX_FUNC_LIMIT:
                        l2_issues.append(f"LOGIC DRIFT: {f} has {count} functions (Limit: {self.MAX_FUNC_LIMIT})")
        
        self.report["layers"]["L2_PRODUCTION"]["violations"] = l2_issues
        self.report["layers"]["L2_PRODUCTION"]["health"] = max(0.0, 1.0 - (len(l2_issues) * 0.1))

        # 2. Control Layer Audit (L1) - Purity Check
        l1_issues = self.audit_l1_purity("/Users/andy/my_too_test/autonomous_operator")
        pulse_err = self.check_pulse()
        if pulse_err:
            l1_issues.append(pulse_err)
            
        self.report["layers"]["L1_CONTROL"]["violations"] = l1_issues
        self.report["layers"]["L1_CONTROL"]["health"] = max(0.0, 1.0 - (len(l1_issues) * 0.2))

        # 3. Archive Layer Audit (L3)
        l3_issues = []
        if not os.path.exists("/Users/andy/my_too_test/logs"):
            l3_issues.append("COLD STORAGE FAILURE: Logs directory missing.")
        
        self.report["layers"]["L3_ARCHIVE"]["violations"] = l3_issues
        self.report["layers"]["L3_ARCHIVE"]["health"] = 1.0 if not l3_issues else 0.0

        # Score calculation
        avg_health = sum(v["health"] for v in self.report["layers"].values()) / 3
        self.report["overall_score"] = int(avg_health * 100)
        self.report["mesh_status"] = "HEALTHY" if self.report["overall_score"] > 90 else "DRIFTING"

        return self.report

if __name__ == "__main__":
    detector = DriftDetector()
    results = detector.run_mesh_audit()
    print(json.dumps(results, indent=2))
    
    # In future: Send to Notion via Control Plane service
