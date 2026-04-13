from langchain.tools import tool
import logging

try:
    from transformers import pipeline
    # Initialize a lightweight transformer model trained for detecting Fake News properties via Text Classification
    # To avoid VRAM exhaustion on local devices, we use a specialized smaller RoBERTa or BERT derivative 
    # and lazily load it.
    classifier = pipeline("text-classification", model="mrm8488/bert-tiny-finetuned-fake-news-detection")
except ImportError:
    classifier = None
    logging.warning("NLP Transformers unavailable - pip install transformers torch missing.")
except Exception as e:
    classifier = None
    logging.warning(f"Could not load Fake News NLP model: {e}")

@tool("Clickbait and Fake News Detector")
def fake_news_detector_tool(text: str) -> str:
    """
    Analyzes content for sensationalism, emotional manipulation, and propaganda vectors natively using NLP text classification.
    Returns the probability of the content being 'Fake' or 'Misleading'.
    """
    if not classifier:
        return "NLP Transformer not available on host machine. Assumed probability unknown."
        
    try:
        # Heavily truncate text to fit common 512 token limits to avoid tensor rank crashing
        truncated_text = text[:1500] 
        results = classifier(truncated_text)
        
        predictions = []
        for res in results:
            # Typical pipeline dictionaries: {'label': 'FAKE', 'score': 0.99}
            label = res.get('label', 'UNKNOWN')
            score = res.get('score', 0.0)
            predictions.append(f"Classified Label: {label} | NLP Confidence: {score:.2f}")
            
        return " \n".join(predictions)
    except Exception as e:
        return f"Classification tensor error: {e}"
