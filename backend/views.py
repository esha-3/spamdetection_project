import os
import re
import json
import joblib
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Count
from .models import SpamRecord

MODEL_PATH = os.path.join(os.path.dirname(__file__), "spam_detector_model.joblib")
_cached_model = None

def get_model():
    """Lazily load and cache the model."""
    global _cached_model
    if _cached_model is None:
        if os.path.exists(MODEL_PATH):
            try:
                _cached_model = joblib.load(MODEL_PATH)
            except Exception as e:
                print(f"Error loading model: {e}")
        else:
            print("Model file not found. Running heuristic fallback mode.")
    return _cached_model


def get_heuristic_prediction(text):
    """
    Fallback rule-based prediction if model is not trained yet.
    """
    text_lower = text.lower()
    
    # Common spam triggers and regex patterns
    spam_triggers = {
        'free': 'promotions offering freebies',
        'win': 'lottery or contest winning claims',
        'winner': 'contest winning claims',
        'claim': 'urgent prize/reward claims',
        'prize': 'reward and cash sweepstakes',
        'urgent': 'artificial urgency triggers',
        'txt': 'premium rate text instructions',
        'cash': 'cash offers and credit options',
        'credit': 'loan or card offers',
        'loan': 'loan or debt financing deals',
        'reply': 'call-to-action responses',
        'stop': 'opt-out promotional structures',
        'call': 'requests to contact phone lines',
        'http': 'unverified external link references',
        'https': 'unverified external link references',
        'dhl': 'package delivery scams',
        'fedex': 'package delivery scams',
        'amazon': 'e-commerce account security alerts',
        'paypal': 'payment system alerts',
        'netflix': 'subscription renewal warnings'
    }
    
    matched_reasons = []
    matched_words = []
    
    for word, reason in spam_triggers.items():
        # Match word boundaries or link structures
        pattern = r'\b' + word + r'\b' if word not in ('http', 'https') else word
        if re.search(pattern, text_lower):
            matched_words.append(word)
            if reason not in matched_reasons:
                matched_reasons.append(reason)
                
    score = len(matched_words)
    
    if score >= 2:
        verdict = 'spam'
        confidence = min(65.0 + score * 8, 98.5)
        explanation = f"Detected high-risk spam indicators: {', '.join(matched_words)}. This message is flagged as spam due to {', '.join(matched_reasons[:3])}."
    elif score == 1:
        verdict = 'spam'
        confidence = 58.0
        explanation = f"Suspicious term '{matched_words[0]}' found. The content structure matches standard promotional or phishing templates."
    else:
        verdict = 'safe'
        confidence = 88.0
        explanation = "No typical spam triggers or suspicious links detected. The phrasing aligns with normal interpersonal communication."
        
    return verdict, confidence, explanation


def get_ml_prediction(text):
    """
    Runs prediction using the scikit-learn TF-IDF + Logistic Regression model.
    """
    pipeline = get_model()
    if not pipeline:
        return get_heuristic_prediction(text)
        
    vectorizer = pipeline['vectorizer']
    classifier = pipeline['classifier']
    
    # Transform and predict
    vec = vectorizer.transform([text])
    prediction = classifier.predict(vec)[0]
    
    # Calculate probabilities
    probs = classifier.predict_proba(vec)[0]
    classes = classifier.classes_
    
    spam_idx = list(classes).index('spam')
    spam_prob = probs[spam_idx]
    
    # Extract important features to construct an explanation
    feature_names = vectorizer.get_feature_names_out()
    coefs = classifier.coef_[0]
    feature_weights = dict(zip(feature_names, coefs))
    
    # Find words in text that contributed to spam
    text_words = re.findall(r'\b\w\w+\b', text.lower())
    flagged_terms = []
    for word in text_words:
        if word in feature_weights and feature_weights[word] > 0.15:
            flagged_terms.append((word, feature_weights[word]))
            
    # Sort terms by their model weight
    flagged_terms = sorted(list(set(flagged_terms)), key=lambda x: x[1], reverse=True)
    top_flagged = [t[0] for t in flagged_terms[:4]]
    
    if prediction == 'spam':
        verdict = 'spam'
        confidence = round(spam_prob * 100, 1)
        if top_flagged:
            explanation = f"Flagged by AI model based on high-risk keywords: {', '.join(top_flagged)}. The formatting matches patterns found in known spam broadcasts."
        else:
            explanation = "Classified as spam by the AI model. The overall combination of terms and structure matches promotional templates."
    else:
        verdict = 'safe'
        confidence = round((1 - spam_prob) * 100, 1)
        explanation = "The AI model is confident this message is safe. It shows no patterns associated with marketing campaigns or phishing schemes."
        
    return verdict, confidence, explanation


@csrf_exempt
@require_http_methods(["POST"])
def check_spam_api(request):
    try:
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        
        if not message:
            return JsonResponse({'error': 'Message cannot be empty.'}, status=400)
            
        # Perform prediction
        verdict, confidence, explanation = get_ml_prediction(message)
        
        # Save record to Database
        record = SpamRecord.objects.create(
            message_text=message,
            verdict=verdict,
            confidence=confidence,
            explanation=explanation
        )
        
        return JsonResponse({
            'id': record.id,
            'message_text': record.message_text,
            'verdict': record.verdict,
            'confidence': record.confidence,
            'explanation': record.explanation,
            'created_at': record.created_at.isoformat()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON request.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@require_http_methods(["GET"])
def get_history_api(request):
    try:
        # Get last 15 checks
        records = SpamRecord.objects.all()[:15]
        data = []
        for r in records:
            data.append({
                'id': r.id,
                'message_text': r.message_text,
                'verdict': r.verdict,
                'confidence': r.confidence,
                'explanation': r.explanation,
                'created_at': r.created_at.isoformat()
            })
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_history_item_api(request, pk):
    try:
        record = SpamRecord.objects.filter(pk=pk).first()
        if not record:
            return JsonResponse({'error': 'Record not found.'}, status=404)
            
        record.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_stats_api(request):
    try:
        total = SpamRecord.objects.count()
        if total == 0:
            return JsonResponse({
                'total_count': 0,
                'spam_count': 0,
                'safe_count': 0,
                'spam_rate': 0.0
            })
            
        spam_count = SpamRecord.objects.filter(verdict='spam').count()
        safe_count = SpamRecord.objects.filter(verdict='safe').count()
        spam_rate = round((spam_count / total) * 100, 1)
        
        return JsonResponse({
            'total_count': total,
            'spam_count': spam_count,
            'safe_count': safe_count,
            'spam_rate': spam_rate
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
