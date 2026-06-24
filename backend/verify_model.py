import os
import joblib

MODEL_PATH = os.path.join(os.path.dirname(__file__), "spam_detector_model.joblib")

def test_saved_model():
    if not os.path.exists(MODEL_PATH):
        print("ERROR: Model file not found.")
        return
        
    print(f"Loading model from {MODEL_PATH}...")
    pipeline = joblib.load(MODEL_PATH)
    vectorizer = pipeline['vectorizer']
    classifier = pipeline['classifier']
    
    test_messages = [
        "Hey, are we still meeting for lunch today?",
        "URGENT: Your mobile number has won a £1,500 cash prize. Call 09061701461 now to claim!",
        "Can you buy some milk on your way home?",
        "CLAIM NOW: Free spins on online slots! Click http://slots-las-vegas.com"
    ]
    
    print("\n--- Running Model Predictions ---")
    for msg in test_messages:
        vec = vectorizer.transform([msg])
        prediction = classifier.predict(vec)[0]
        probs = classifier.predict_proba(vec)[0]
        
        spam_idx = list(classifier.classes_).index('spam')
        spam_prob = probs[spam_idx]
        confidence = spam_prob if prediction == 'spam' else (1 - spam_prob)
        
        print(f"Message: '{msg}'")
        print(f"Prediction: {prediction.upper()} (Confidence: {confidence*100:.1f}%)")
        print("-" * 40)

if __name__ == "__main__":
    test_saved_model()
