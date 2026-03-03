import json
import os
import sqlite3
import hashlib
from pathlib import Path

class DiskFingerprintSet:
    """
    A disk-backed set for tracking seen fingerprints with O(1) RAM usage.
    Uses SQLite for persistent storage of hashes.
    """
    def __init__(self, db_path="/tmp/fingerprints.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.cursor.execute("CREATE TABLE IF NOT EXISTS seen (hash TEXT PRIMARY KEY)")
        self.conn.commit()

    def add(self, fingerprint_str: str):
        # Create a unique hash for the fingerprint to save space
        fp_hash = hashlib.sha256(fingerprint_str.encode()).hexdigest()
        try:
            self.cursor.execute("INSERT INTO seen VALUES (?)", (fp_hash,))
            self.conn.commit()
            return True # New
        except sqlite3.IntegrityError:
            return False # Already exists

    def close(self):
        self.conn.close()
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except:
                pass

def calculate_savings(purified_count, total_count):
    """
    Calculates potential ROI of purification.
    Example: $0.10 per GB on CloudWatch.
    """
    reduction = 1 - (purified_count / total_count) if total_count > 0 else 0
    # Assuming avg size 1KB per log entry
    gb_saved = (total_count - purified_count) * 1024 / (1024**3)
    dollars_saved = gb_saved * 0.10 
    return {
        "gb_saved": round(gb_saved, 6),
        "dollars_saved": round(dollars_saved, 4),
        "reduction_pct": round(reduction * 100, 2)
    }

def purify_haios_audit(input_path, output_path, use_disk=True):
    """
    Purifies haios_audit.jsonl with optional disk-backed optimization.
    """
    if not os.path.exists(input_path):
        print(f"File not found: {input_path}")
        return

    seen = DiskFingerprintSet() if use_disk else set()
    total_count = 0
    purified_entries = []
    
    with open(input_path, 'r') as f:
        for line in f:
            total_count += 1
            entry = json.loads(line)
            semantic_part = {
                "event_type": entry.get("event_type"),
                "action_type": entry.get("action_type"),
                "actor_id": entry.get("actor_id"),
                "action_payload": entry.get("action_payload"),
                "pillars_scores": entry.get("pillars_scores"),
                "execution_status": entry.get("execution_status")
            }
            semantic_str = json.dumps(semantic_part, sort_keys=True)
            
            if use_disk:
                if seen.add(semantic_str):
                    purified_entries.append(entry)
            else:
                if semantic_str not in seen:
                    seen.add(semantic_str)
                    purified_entries.append(entry)

    with open(output_path, 'w') as f:
        for entry in purified_entries:
            f.write(json.dumps(entry) + '\n')
            
    if use_disk: seen.close()
    
    savings = calculate_savings(len(purified_entries), total_count)
    print(f"Purified haios_audit: {len(purified_entries)} unique events. Reduction: {savings['reduction_pct']}%")
    return savings

def purify_generic_json_list(input_path, output_path, semantic_keys, use_disk=True):
    """
    Purifies a JSON list with optional disk-backed optimization.
    """
    if not os.path.exists(input_path):
        print(f"File not found: {input_path}")
        return

    with open(input_path, 'r') as f:
        data = json.load(f)
        
    seen = DiskFingerprintSet() if use_disk else set()
    purified_data = []
    
    for item in data:
        semantic_part = {k: item.get(k) for k in semantic_keys if k in item}
        semantic_str = json.dumps(semantic_part, sort_keys=True)
        
        if use_disk:
            if seen.add(semantic_str):
                purified_data.append(item)
        else:
            if semantic_str not in seen:
                seen.add(semantic_str)
                purified_data.append(item)
            
    with open(output_path, 'w') as f:
        json.dump(purified_data, f, indent=2)
        
    if use_disk: seen.close()
    
    savings = calculate_savings(len(purified_data), len(data))
    print(f"Purified {os.path.basename(input_path)}: {len(purified_data)} unique entries. Reduction: {savings['reduction_pct']}%")
    return savings

if __name__ == "__main__":
    # Standard Operational Sweep
    purify_haios_audit(
        "/Users/andy/my_too_test/DAIOF-Framework/haios_audit.jsonl",
        "/Users/andy/my_too_test/DAIOF-Framework/haios_audit_purified.jsonl",
        use_disk=True
    )
    
    purify_generic_json_list(
        "/Users/andy/my_too_test/daiof_issues.json",
        "/Users/andy/my_too_test/daiof_issues_purified.json",
        ["title"],
        use_disk=True
    )
    
    purify_generic_json_list(
        "/Users/andy/balancehub/symphony_backup.json",
        "/Users/andy/balancehub/symphony_backup_purified_final.json",
        ["question"],
        use_disk=True
    )
