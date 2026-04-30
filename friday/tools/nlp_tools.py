from langchain.tools import tool
import logging

classifier = None
classifier_load_attempted = False


def _get_classifier():
    global classifier
    global classifier_load_attempted
    if classifier_load_attempted:
        return classifier
    classifier_load_attempted = True
    try:
        from transformers import pipeline

        classifier = pipeline(
            "text-classification",
            model="mrm8488/bert-tiny-finetuned-fake-news-detection",
        )
    except ImportError:
        logging.warning(
            "NLP Transformers unavailable - pip install transformers torch missing."
        )
        classifier = None
    except Exception as e:
        logging.warning(f"Could not load Fake News NLP model: {e}")
        classifier = None
    return classifier


@tool("Clickbait and Fake News Detector")
def fake_news_detector_tool(text: str) -> str:
    loaded_classifier = _get_classifier()
    if not loaded_classifier:
        return "NLP Transformer not available on host machine. Assumed probability unknown."
    try:
        truncated_text = text[:1500]
        results = loaded_classifier(truncated_text)
        predictions = []
        for res in results:
            label = res.get("label", "UNKNOWN")
            score = res.get("score", 0.0)
            predictions.append(
                f"Classified Label: {label} | NLP Confidence: {score:.2f}"
            )
        return " \n".join(predictions)
    except Exception as e:
        return f"Classification tensor error: {e}"
