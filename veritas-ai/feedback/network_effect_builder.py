import sqlite3
import json
import logging
import os

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DB_PATH = os.path.join(DB_DIR, "feedback_loop.sqlite")
DATASET_PATH = os.path.join(DB_DIR, "proprietary_training_dataset.jsonl")

def extract_and_build_dataset():
    """
    Automated Data Flywheel System seamlessly extracting global human context.
    Transforms raw user overrides organically into strict fine-tuning dataset inputs safely natively.
    """
    try:
        # Gracefully handle uninitialized databases organically
        if not os.path.exists(DB_PATH):
            return {"status": "no_updates", "message": "Feedback tables natively empty."}
            
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM feedback_loop WHERE pipeline_status = 'PENDING_VALIDATION'")
        rows = cursor.fetchall()
        
        if not rows:
            logging.info("Network Effects Pipeline currently normalized natively. No new data.")
            conn.close()
            return {"status": "no_updates", "extracted": 0}
            
        dataset_entries = []
        parsed_ids = []
        
        for row in rows:
            entry = {
                "metadata_id": f"RLHF_VERITAS_{row['id']}",
                "origin_timestamp": row["timestamp"],
                "input_prompt": row["query"],
                "model_output_score": row["original_truth_score"],
                "human_preference_score": row["user_corrected_score"],
                "disagreement_label": row["user_flag"],
                "human_context": row["comments"]
            }
            dataset_entries.append(entry)
            parsed_ids.append(row["id"])
            
        # Append logic robustly directly compiling local Reinforcement Learning matrices (RLHF)
        with open(DATASET_PATH, 'a', encoding='utf-8') as f:
            for entry in dataset_entries:
                f.write(json.dumps(entry) + '\n')
                
        # Lock validated states safely preventing redundant ML data poisoning locally
        for record_id in parsed_ids:
            cursor.execute("UPDATE feedback_loop SET pipeline_status = 'INJECTED_INTO_ML' WHERE id = ?", (record_id,))
            
        conn.commit()
        conn.close()
        
        logging.info(f"Synthesized {len(parsed_ids)} proprietary intelligence parameters elegantly into Network Matrix.")
        return {
            "status": "success", 
            "dataset_updated": True, 
            "entries_parsed": len(parsed_ids),
            "output_target": DATASET_PATH
        }
        
    except Exception as e:
        logging.error(f"Network Effects extraction crash optimally bypassed: {e}")
        return {"status": "error", "message": str(e)}
