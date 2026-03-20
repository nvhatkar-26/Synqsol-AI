import json
import random
import os

class QuestionEngine:
    def __init__(self, bank_path="database/question_bank.json", history_path="database/user_history.json"):
        self.bank_path = bank_path
        self.history_path = history_path
        # Ensure the history file exists
        if not os.path.exists(self.history_path):
            with open(self.history_path, 'w') as f:
                json.dump([], f)

    def _load_json(self, path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def get_questions(self, user_name, test_type="basic"):
        """
        Retrieves 20 or 40 questions balanced across OCEAN dimensions.
        Ensures no repeats for the specific user_name.
        """
        num_total = 20 if test_type == "basic" else 40
        num_per_dim = num_total // 5
        
        all_questions = self._load_json(self.bank_path)
        history = self._load_json(self.history_path)
        
        # Identify questions already seen by this user
        seen_ids = {h['q_id'] for h in history if h['user_id'] == user_name}
        
        dimensions = ["Openness", "Conscientiousness", "Extraversion", "Agreeableness", "Neuroticism"]
        selected_questions = []

        for dim in dimensions:
            # Filter available questions for this dimension that haven't been seen
            pool = [q for q in all_questions if q['dimension'] == dim and q['id'] not in seen_ids]
            
            # Fallback: If we run out of new questions, allow repeats for this dimension
            if len(pool) < num_per_dim:
                pool = [q for q in all_questions if q['dimension'] == dim]
            
            # Randomly sample the required number for this dimension
            selected_questions.extend(random.sample(pool, num_per_dim))

        # Shuffle the final list so dimensions are mixed for the user
        random.shuffle(selected_questions)
        return selected_questions

    def save_attempt(self, user_name, q_id, score):
        """
        Logs the answer to the history file to prevent future repeats.
        """
        history = self._load_json(self.history_path)
        history.append({
            "user_id": user_name,
            "q_id": q_id,
            "score": score,
            "timestamp": os.times().elapsed # Simple timestamp
        })
        with open(self.history_path, 'w') as f:
            json.dump(history, f, indent=2)

    def get_user_previous_scores(self, user_name):
        """
        Used for the 'Question Augmentor' flow to collect past data.
        """
        history = self._load_json(self.history_path)
        return [h for h in history if h['user_id'] == user_name]